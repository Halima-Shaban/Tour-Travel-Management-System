import secrets
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class SluggedModel(models.Model):
    slug = models.SlugField(max_length=180, unique=True, blank=True)

    class Meta:
        abstract = True

    def slug_source(self):
        raise NotImplementedError

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.slug_source())[:170] or "item"
            slug, n = base, 2
            while type(self).objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)


class ImageMixin(models.Model):
    image = models.ImageField(upload_to="tours/", blank=True)
    image_url = models.URLField(blank=True, help_text="Used when no image is uploaded.")

    class Meta:
        abstract = True

    @property
    def cover(self):
        if self.image:
            return self.image.url
        return self.image_url or f"https://picsum.photos/seed/{self.slug or 'gotrip'}/900/600"


class Destination(SluggedModel, ImageMixin):
    name = models.CharField(max_length=120)
    country = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}, {self.country}"

    def slug_source(self):
        return self.name

    def get_absolute_url(self):
        return reverse("tours:destination", args=[self.slug])


class TourQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def with_rating(self):
        return self.annotate(avg_rating=Avg("reviews__rating", filter=models.Q(reviews__is_approved=True)))


class Tour(SluggedModel, ImageMixin):
    class Category(models.TextChoices):
        ADVENTURE = "adventure", "Adventure"
        CULTURAL = "cultural", "Cultural"
        BEACH = "beach", "Beach & islands"
        DESERT = "desert", "Desert & safari"
        CITY = "city", "City break"
        CRUISE = "cruise", "Cruise"
        NATURE = "nature", "Nature & wildlife"

    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MODERATE = "moderate", "Moderate"
        CHALLENGING = "challenging", "Challenging"

    title = models.CharField(max_length=160)
    destination = models.ForeignKey(Destination, on_delete=models.PROTECT, related_name="tours")
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.CULTURAL)
    difficulty = models.CharField(max_length=20, choices=Difficulty.choices, default=Difficulty.EASY)
    summary = models.CharField(max_length=255)
    description = models.TextField()
    highlights = models.TextField(blank=True, help_text="One highlight per line.")
    itinerary = models.TextField(blank=True, help_text="One day per line, e.g. 'Day 1: Arrival in Cairo'.")
    included = models.TextField(blank=True, help_text="One item per line.")
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    sale_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    duration_days = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    max_group_size = models.PositiveSmallIntegerField(default=12, validators=[MinValueValidator(1)])
    guide = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guided_tours",
        limit_choices_to={"profile__role": "guide"},
    )
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TourQuerySet.as_manager()

    class Meta:
        ordering = ["-is_featured", "-created_at"]

    def __str__(self):
        return self.title

    def slug_source(self):
        return self.title

    def get_absolute_url(self):
        return reverse("tours:detail", args=[self.slug])

    @property
    def current_price(self):
        return self.sale_price if self.sale_price and self.sale_price < self.price else self.price

    @property
    def discount_percent(self):
        if self.current_price < self.price:
            return int(round((1 - self.current_price / self.price) * 100))
        return 0

    @staticmethod
    def _lines(text):
        return [line.strip() for line in text.splitlines() if line.strip()]

    @property
    def highlight_list(self):
        return self._lines(self.highlights)

    @property
    def itinerary_list(self):
        return self._lines(self.itinerary)

    @property
    def included_list(self):
        return self._lines(self.included)

    @property
    def rating(self):
        value = getattr(self, "avg_rating", None)
        if value is None:
            value = self.reviews.filter(is_approved=True).aggregate(v=Avg("rating"))["v"]
        return round(value or 0, 1)

    def seats_left(self, travel_date):
        booked = (
            self.bookings.filter(travel_date=travel_date)
            .exclude(status=Booking.Status.CANCELLED)
            .aggregate(total=models.Sum("travelers"))["total"]
            or 0
        )
        return max(self.max_group_size - booked, 0)


def generate_reference():
    return "GT-" + secrets.token_hex(3).upper()


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class Payment(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PAID = "paid", "Paid"
        REFUNDED = "refunded", "Refunded"

    class GuideResponse(models.TextChoices):
        PENDING = "pending", "Awaiting guide"
        ACCEPTED = "accepted", "Accepted by guide"
        DECLINED = "declined", "Declined by guide"

    reference = models.CharField(max_length=12, unique=True, default=generate_reference, editable=False)
    tour = models.ForeignKey(Tour, on_delete=models.PROTECT, related_name="bookings")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings"
    )
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    travel_date = models.DateField()
    travelers = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(50)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_status = models.CharField(max_length=20, choices=Payment.choices, default=Payment.UNPAID)
    special_requests = models.TextField(blank=True)
    guide_notes = models.TextField(blank=True, help_text="Private notes from the assigned guide.")
    # Guide assignment (defaults to the tour's guide; admins can reassign per booking)
    guide = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_bookings",
        limit_choices_to={"profile__role": "guide"},
    )
    guide_status = models.CharField(max_length=10, choices=GuideResponse.choices, default=GuideResponse.PENDING)
    guide_responded_at = models.DateTimeField(null=True, blank=True)
    guide_decline_reason = models.CharField(max_length=255, blank=True)
    # Online payment (Stripe)
    stripe_session_id = models.CharField(max_length=255, blank=True)
    stripe_payment_intent = models.CharField(max_length=255, blank=True)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["travel_date", "status"])]

    def __str__(self):
        return f"{self.reference} - {self.tour}"

    def save(self, *args, **kwargs):
        if not self.unit_price:
            self.unit_price = self.tour.current_price
        if self._state.adding and self.guide_id is None:
            self.guide = self.tour.guide
        self.total_price = self.unit_price * self.travelers
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("accounts:booking_detail", args=[self.reference])

    @property
    def is_upcoming(self):
        return self.travel_date >= timezone.localdate()

    @property
    def has_started(self):
        return self.travel_date <= timezone.localdate()

    @property
    def needs_guide(self):
        return self.status != self.Status.CANCELLED and (
            self.guide_id is None or self.guide_status == self.GuideResponse.DECLINED
        )

    @property
    def can_pay(self):
        return self.payment_status == self.Payment.UNPAID and self.status in (
            self.Status.PENDING, self.Status.CONFIRMED
        )

    @property
    def can_guide_respond(self):
        return (
            self.guide_status == self.GuideResponse.PENDING
            and self.status in (self.Status.PENDING, self.Status.CONFIRMED)
            and self.is_upcoming
        )

    def overlaps(self, start, end):
        return self.travel_date <= end and self.end_date >= start

    @property
    def end_date(self):
        return self.travel_date + timedelta(days=self.tour.duration_days - 1)

    @property
    def can_cancel(self):
        return self.status in (self.Status.PENDING, self.Status.CONFIRMED) and self.travel_date > timezone.localdate()


class Review(models.Model):
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["tour", "user"], name="one_review_per_user_per_tour")]

    def __str__(self):
        return f"{self.rating}* {self.tour} by {self.user}"


class Participant(models.Model):
    """A named traveler on a booking (the lead traveler fills these in; guides see them in manifests)."""

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="participants")
    full_name = models.CharField(max_length=120)
    age = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MaxValueValidator(120)])
    nationality = models.CharField(max_length=60, blank=True)
    notes = models.CharField(max_length=255, blank=True, help_text="Dietary needs, mobility, allergies...")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.full_name


class GuideUnavailability(models.Model):
    """Time off blocked by a guide; bookings can't be made on these dates for the guide's tours."""

    guide = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="unavailability")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_date"]
        verbose_name_plural = "guide unavailability"

    def __str__(self):
        return f"{self.guide} off {self.start_date} - {self.end_date}"

    @classmethod
    def overlapping(cls, guide, start, end):
        return cls.objects.filter(guide=guide, start_date__lte=end, end_date__gte=start)
