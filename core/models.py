from django.core.cache import cache
from django.core.validators import RegexValidator
from django.db import models

hex_color = RegexValidator(r"^#[0-9a-fA-F]{6}$", "Use a hex colour such as #0f766e.")


class SiteSettings(models.Model):
    """Singleton holding every customisable piece of the site (branding, theme, content, chatbot)."""

    FONT_CHOICES = [
        ("Poppins", "Poppins"),
        ("Inter", "Inter"),
        ("Montserrat", "Montserrat"),
        ("Cairo", "Cairo (Arabic friendly)"),
        ("Playfair Display", "Playfair Display"),
    ]
    CACHE_KEY = "core.site_settings"

    # Branding
    site_name = models.CharField(max_length=80, default="GoTrip")
    tagline = models.CharField(max_length=160, default="Tours & travel, crafted by local experts")
    logo = models.ImageField(upload_to="branding/", blank=True)
    favicon = models.ImageField(upload_to="branding/", blank=True)

    # Theme
    primary_color = models.CharField(max_length=7, default="#0f766e", validators=[hex_color])
    secondary_color = models.CharField(max_length=7, default="#f59e0b", validators=[hex_color])
    dark_color = models.CharField(max_length=7, default="#0f172a", validators=[hex_color])
    font_family = models.CharField(max_length=40, choices=FONT_CHOICES, default="Poppins")
    border_radius = models.PositiveSmallIntegerField(default=14, help_text="Corner roundness in px (0-32).")

    # Home page content
    hero_title = models.CharField(max_length=160, default="Discover the world with people who know it")
    hero_subtitle = models.CharField(
        max_length=300,
        default="Hand-picked tours, certified local guides and flexible booking - all in one place.",
    )
    hero_image = models.ImageField(upload_to="branding/", blank=True)
    hero_image_url = models.URLField(
        blank=True, default="https://picsum.photos/seed/gotrip-hero/1920/1080"
    )
    about_title = models.CharField(max_length=160, default="Travel that feels personal")
    about_text = models.TextField(
        default=(
            "We design small-group and private tours led by certified local guides. "
            "Every itinerary is tested on the ground, priced transparently and backed "
            "by 24/7 support so you can focus on the journey."
        )
    )
    show_stats = models.BooleanField(default=True)
    show_testimonials = models.BooleanField(default=True)
    show_blog = models.BooleanField(default=True)

    # Contact & social
    email = models.EmailField(default="hello@gotrip.test")
    phone = models.CharField(max_length=40, default="+20 100 000 0000")
    address = models.CharField(max_length=200, default="12 Nile Corniche, Cairo, Egypt")
    whatsapp = models.CharField(max_length=40, blank=True)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    footer_text = models.CharField(max_length=255, default="Licensed tour operator. Travel safely, travel well.")

    # Commerce
    currency_symbol = models.CharField(max_length=5, default="$")
    booking_enabled = models.BooleanField(default=True)
    cancellation_policy = models.TextField(
        default="Free cancellation up to 7 days before departure. 50% refund within 7 days. No refund within 48 hours."
    )

    # Chatbot
    chatbot_enabled = models.BooleanField(default=True)
    chatbot_name = models.CharField(max_length=40, default="Trip Assistant")
    chatbot_welcome = models.CharField(
        max_length=255, default="Hi! I can help you find a tour, check prices or answer booking questions."
    )
    chatbot_instructions = models.TextField(
        blank=True,
        help_text="Extra instructions appended to the assistant's system prompt (tone, promotions, rules...).",
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = verbose_name_plural = "Site settings"

    def __str__(self):
        return "Site settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete(self.CACHE_KEY)

    def delete(self, *args, **kwargs):  # the singleton can't be deleted
        pass

    @classmethod
    def load(cls):
        obj = cache.get(cls.CACHE_KEY)
        if obj is None:
            obj, _ = cls.objects.get_or_create(pk=1)
            cache.set(cls.CACHE_KEY, obj, 300)
        return obj

    @property
    def hero_background(self):
        return self.hero_image.url if self.hero_image else self.hero_image_url


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(
        max_length=30, blank=True, validators=[RegexValidator(r"^[0-9+()\-\s]*$", "Invalid phone number.")]
    )
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} - {self.name}"


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
