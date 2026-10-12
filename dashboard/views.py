import csv
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q, Sum
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, TemplateView, UpdateView

from accounts.models import Profile
from accounts.permissions import AdminRequiredMixin, admin_required
from blog.forms import PostForm
from blog.models import Post
from chatbot.models import Conversation
from core.forms import SiteSettingsForm
from core.models import ContactMessage, NewsletterSubscriber, SiteSettings
from messaging.services import threads_for
from payments import gateway
from tours import services
from tours.forms import AssignGuideForm, BookingAdminForm, DestinationForm, TourForm
from tours.models import Booking, Destination, Review, Tour

from . import analytics
from .forms import GuideCreateForm, UserRoleForm


def paginate(request, queryset, per_page=15):
    return Paginator(queryset, per_page).get_page(request.GET.get("page"))


# --------------------------------------------------------------------------- overview
class HomeView(AdminRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        today = timezone.localdate()
        month_start = today.replace(day=1)
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)
        active = Booking.objects.exclude(status=Booking.Status.CANCELLED)

        def revenue(qs):
            return float(qs.aggregate(v=Sum("total_price"))["v"] or 0)

        this_month = active.filter(created_at__date__gte=month_start)
        last_month = active.filter(created_at__date__gte=prev_month_start, created_at__date__lt=month_start)
        kpis = {
            "revenue": revenue(active.filter(payment_status=Booking.Payment.PAID)),
            "revenue_month": revenue(this_month),
            "revenue_growth": analytics.growth(revenue(this_month), revenue(last_month)),
            "bookings": active.count(),
            "bookings_month": this_month.count(),
            "bookings_growth": analytics.growth(this_month.count(), last_month.count()),
            "pending": Booking.objects.filter(status=Booking.Status.PENDING).count(),
            "customers": Profile.objects.filter(role=Profile.Role.CUSTOMER).count(),
            "guides": Profile.objects.filter(role=Profile.Role.GUIDE).count(),
            "tours": Tour.objects.active().count(),
            "rating": round(Review.objects.filter(is_approved=True).aggregate(v=Avg("rating"))["v"] or 0, 1),
            "unread": ContactMessage.objects.filter(is_read=False).count(),
        }
        top_tours = (
            Tour.objects.annotate(
                n=Count("bookings", filter=~Q(bookings__status=Booking.Status.CANCELLED)),
                revenue=Sum("bookings__total_price", filter=~Q(bookings__status=Booking.Status.CANCELLED)),
            )
            .filter(n__gt=0)
            .order_by("-revenue")[:5]
        )
        destinations = (
            Destination.objects.annotate(
                n=Count("tours__bookings", filter=~Q(tours__bookings__status=Booking.Status.CANCELLED))
            )
            .filter(n__gt=0)
            .order_by("-n")[:6]
        )
        return super().get_context_data(
            kpis=kpis,
            monthly=analytics.monthly_series(Booking.objects.all()),
            status=analytics.status_breakdown(Booking.objects.all()),
            top_tours=top_tours,
            destination_chart={"labels": [d.name for d in destinations], "values": [d.n for d in destinations]},
            recent_bookings=Booking.objects.select_related("tour")[:8],
            upcoming=active.filter(travel_date__gte=today, travel_date__lte=today + timedelta(days=14))
            .select_related("tour", "guide")
            .order_by("travel_date")[:8],
            unassigned=Tour.objects.active().filter(guide__isnull=True).count(),
            needs_guide=needs_guide_qs().count(),
            **kwargs,
        )


def needs_guide_qs():
    return Booking.objects.exclude(status=Booking.Status.CANCELLED).filter(
        travel_date__gte=timezone.localdate()
    ).filter(Q(guide__isnull=True) | Q(guide_status=Booking.GuideResponse.DECLINED))


# --------------------------------------------------------------------------- generic CRUD helpers
class CrudMixin(AdminRequiredMixin, SuccessMessageMixin):
    template_name = "dashboard/form.html"
    list_url = None
    title = ""

    def get_success_url(self):
        return reverse(self.list_url)

    def get_context_data(self, **kwargs):
        kwargs.setdefault("title", self.title or (f"Edit {self.object}" if getattr(self, "object", None) else "Create"))
        kwargs.setdefault("back_url", reverse(self.list_url))
        return super().get_context_data(**kwargs)


class CrudDeleteView(AdminRequiredMixin, DeleteView):
    template_name = "dashboard/confirm_delete.html"
    list_url = None

    def get_success_url(self):
        return reverse(self.list_url)

    def get_context_data(self, **kwargs):
        return super().get_context_data(back_url=reverse(self.list_url), **kwargs)

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, f"“{self.object}” is in use (e.g. it has bookings) and can't be deleted. Deactivate it instead.")
            return redirect(self.get_success_url())
        messages.success(self.request, f"“{self.object}” deleted.")
        return response


# --------------------------------------------------------------------------- tours
@admin_required
def tour_list(request):
    tours = Tour.objects.select_related("destination", "guide").with_rating().annotate(
        n_bookings=Count("bookings", distinct=True)
    ).order_by("-created_at")
    if q := request.GET.get("q"):
        tours = tours.filter(Q(title__icontains=q) | Q(destination__name__icontains=q))
    if status := request.GET.get("status"):
        tours = tours.filter(is_active=status == "active")
    if category := request.GET.get("category"):
        tours = tours.filter(category=category)
    return render(request, "dashboard/tours.html", {"page": paginate(request, tours), "categories": Tour.Category.choices})


class TourCreate(CrudMixin, CreateView):
    model, form_class, list_url, title = Tour, TourForm, "dashboard:tours", "New tour"
    success_message = "Tour “%(title)s” created."


class TourUpdate(CrudMixin, UpdateView):
    model, form_class, list_url = Tour, TourForm, "dashboard:tours"
    success_message = "Tour “%(title)s” updated."


class TourDelete(CrudDeleteView):
    model, list_url = Tour, "dashboard:tours"


@admin_required
def tour_toggle(request, pk):
    tour = get_object_or_404(Tour, pk=pk)
    if request.method == "POST":
        field = request.POST.get("field")
        if field in ("is_active", "is_featured"):
            setattr(tour, field, not getattr(tour, field))
            tour.save(update_fields=[field, "updated_at"])
    return redirect(request.META.get("HTTP_REFERER") or "dashboard:tours")


# --------------------------------------------------------------------------- destinations
@admin_required
def destination_list(request):
    destinations = Destination.objects.annotate(n_tours=Count("tours", distinct=True))
    return render(request, "dashboard/destinations.html", {"destinations": destinations})


class DestinationCreate(CrudMixin, CreateView):
    model, form_class, list_url, title = Destination, DestinationForm, "dashboard:destinations", "New destination"
    success_message = "Destination “%(name)s” created."


class DestinationUpdate(CrudMixin, UpdateView):
    model, form_class, list_url = Destination, DestinationForm, "dashboard:destinations"
    success_message = "Destination “%(name)s” updated."


class DestinationDelete(CrudDeleteView):
    model, list_url = Destination, "dashboard:destinations"


# --------------------------------------------------------------------------- bookings
def _filtered_bookings(request):
    bookings = Booking.objects.select_related("tour", "guide", "user")
    if q := request.GET.get("q"):
        bookings = bookings.filter(
            Q(reference__icontains=q) | Q(full_name__icontains=q) | Q(email__icontains=q) | Q(tour__title__icontains=q)
        )
    if status := request.GET.get("status"):
        bookings = bookings.filter(status=status)
    if payment := request.GET.get("payment"):
        bookings = bookings.filter(payment_status=payment)
    if request.GET.get("guide") == "needs":
        bookings = bookings.filter(pk__in=needs_guide_qs())
    elif request.GET.get("guide") in Booking.GuideResponse.values:
        bookings = bookings.filter(guide_status=request.GET["guide"])
    if when := request.GET.get("when"):
        today = timezone.localdate()
        bookings = bookings.filter(travel_date__gte=today) if when == "upcoming" else bookings.filter(travel_date__lt=today)
    return bookings


@admin_required
def booking_list(request):
    bookings = _filtered_bookings(request)
    counts = dict(Booking.objects.values_list("status").annotate(n=Count("id")))
    return render(
        request,
        "dashboard/bookings.html",
        {
            "page": paginate(request, bookings),
            "statuses": Booking.Status.choices,
            "payments": Booking.Payment.choices,
            "counts": counts,
            "total": sum(counts.values()),
            "needs_guide": needs_guide_qs().count(),
        },
    )


@admin_required
def booking_export(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="bookings-{timezone.localdate()}.csv"'
    writer = csv.writer(response)
    writer.writerow(["Reference", "Tour", "Guide", "Customer", "Email", "Phone", "Travel date", "Travelers",
                     "Total", "Status", "Payment", "Created"])
    for b in _filtered_bookings(request):
        guide = b.guide.get_full_name() if b.guide else ""
        writer.writerow([b.reference, b.tour.title, guide, b.full_name, b.email, b.phone, b.travel_date, b.travelers,
                         b.total_price, b.get_status_display(), b.get_payment_status_display(), b.created_at.strftime("%Y-%m-%d")])
    return response


class BookingUpdate(CrudMixin, UpdateView):
    model, form_class, list_url = Booking, BookingAdminForm, "dashboard:bookings"
    template_name = "dashboard/booking_detail.html"
    success_message = "Booking %(reference)s updated."

    def get_success_message(self, cleaned_data):
        return self.success_message % {"reference": self.object.reference}

    def get_success_url(self):
        return reverse("dashboard:booking_edit", args=[self.object.pk])

    def form_valid(self, form):
        before = Booking.objects.get(pk=self.object.pk)
        new_status, new_payment = form.cleaned_data["status"], form.cleaned_data["payment_status"]
        # Transitions with side effects (notifications, Stripe) go through the workflow service.
        form.instance.status, form.instance.payment_status = before.status, before.payment_status
        response = super().form_valid(form)
        booking = self.object
        if new_status == Booking.Status.CANCELLED and before.status != new_status:
            services.cancel_booking(booking, by=self.request.user)
        elif new_status != before.status:
            Booking.objects.filter(pk=booking.pk).update(status=new_status)
        if new_payment == Booking.Payment.PAID and before.payment_status != new_payment:
            services.mark_paid(booking)
        elif new_payment == Booking.Payment.REFUNDED and before.payment_status != new_payment:
            services.mark_refunded(booking)
        elif new_payment != before.payment_status:
            Booking.objects.filter(pk=booking.pk).update(payment_status=new_payment)
        return response

    def get_context_data(self, **kwargs):
        booking = self.object
        return super().get_context_data(
            assign_form=AssignGuideForm(initial={"guide": booking.guide_id}),
            participants=booking.participants.all(),
            conflicts=services.guide_conflicts(booking),
            stripe_enabled=gateway.is_enabled(),
            **kwargs,
        )


@admin_required
def booking_action(request, pk):
    """Side-effect actions from the booking page: assign guide, Stripe refund."""
    booking = get_object_or_404(Booking, pk=pk)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "assign":
            form = AssignGuideForm(request.POST)
            if form.is_valid():
                guide = form.cleaned_data["guide"]
                services.assign_guide(booking, guide, by=request.user)
                messages.success(request, f"{guide.get_full_name()} assigned - waiting for their confirmation.")
        elif action == "refund" and booking.payment_status == Booking.Payment.PAID and booking.stripe_payment_intent:
            try:
                gateway.refund(booking.stripe_payment_intent)
            except gateway.PaymentError as exc:
                messages.error(request, f"Stripe refund failed: {exc}")
            else:
                services.mark_refunded(booking)
                messages.success(request, "Refund issued through Stripe.")
    return redirect("dashboard:booking_edit", pk=pk)


@admin_required
def booking_quick_status(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if request.method == "POST":
        status = request.POST.get("status")
        payment = request.POST.get("payment_status")
        if status == Booking.Status.CANCELLED:
            services.cancel_booking(booking, by=request.user)
        elif status in Booking.Status.values:
            booking.status = status
            booking.save(update_fields=["status", "updated_at"])
        if payment == Booking.Payment.PAID:
            services.mark_paid(booking)
        messages.success(request, f"Booking {booking.reference} updated.")
    return redirect(request.META.get("HTTP_REFERER") or "dashboard:bookings")


# --------------------------------------------------------------------------- guides & users
@admin_required
def guide_list(request):
    guides = (
        User.objects.filter(profile__role=Profile.Role.GUIDE)
        .select_related("profile")
        .annotate(
            n_tours=Count("guided_tours", distinct=True),
            n_bookings=Count("assigned_bookings", filter=~Q(assigned_bookings__status="cancelled"), distinct=True),
            n_pending=Count("assigned_bookings", filter=Q(assigned_bookings__guide_status="pending")
                            & ~Q(assigned_bookings__status="cancelled"), distinct=True),
            rating=Avg("guided_tours__reviews__rating"),
        )
        .order_by("first_name")
    )
    return render(request, "dashboard/guides.html", {"guides": guides})


class GuideCreate(CrudMixin, CreateView):
    form_class, list_url, title = GuideCreateForm, "dashboard:guides", "New guide account"
    success_message = "Guide account “%(username)s” created. Share the password with them securely."


@admin_required
def user_list(request):
    users = User.objects.select_related("profile").annotate(n_bookings=Count("bookings")).order_by("-date_joined")
    if q := request.GET.get("q"):
        users = users.filter(Q(username__icontains=q) | Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
    if role := request.GET.get("role"):
        users = users.filter(profile__role=role)
    return render(request, "dashboard/users.html", {"page": paginate(request, users), "roles": Profile.Role.choices})


@admin_required
def user_edit(request, pk):
    user = get_object_or_404(User.objects.select_related("profile"), pk=pk)
    form = UserRoleForm(request.POST or None, instance=user.profile)
    if request.method == "POST" and form.is_valid():
        if user == request.user and form.cleaned_data["role"] != Profile.Role.ADMIN:
            messages.error(request, "You can't remove your own admin role.")
        else:
            form.save()
            messages.success(request, f"{user.username} updated.")
            return redirect("dashboard:users")
    return render(
        request,
        "dashboard/form.html",
        {"form": form, "title": f"Edit user: {user.get_full_name() or user.username}", "back_url": reverse("dashboard:users"),
         "subtitle": f"{user.email} · joined {user.date_joined:%d %b %Y}"},
    )


# --------------------------------------------------------------------------- reviews
@admin_required
def review_list(request):
    reviews = Review.objects.select_related("tour", "user")
    if (state := request.GET.get("state")) in ("approved", "hidden"):
        reviews = reviews.filter(is_approved=state == "approved")
    return render(request, "dashboard/reviews.html", {"page": paginate(request, reviews)})


@admin_required
def review_action(request, pk):
    review = get_object_or_404(Review, pk=pk)
    if request.method == "POST":
        if request.POST.get("action") == "delete":
            review.delete()
            messages.success(request, "Review deleted.")
        else:
            review.is_approved = not review.is_approved
            review.save(update_fields=["is_approved"])
    return redirect(request.META.get("HTTP_REFERER") or "dashboard:reviews")


# --------------------------------------------------------------------------- inbox & newsletter
@admin_required
def message_list(request):
    msgs = ContactMessage.objects.all()
    if request.GET.get("unread"):
        msgs = msgs.filter(is_read=False)
    return render(request, "dashboard/messages.html", {"page": paginate(request, msgs)})


@admin_required
def message_detail(request, pk):
    msg = get_object_or_404(ContactMessage, pk=pk)
    if request.method == "POST":
        if request.POST.get("action") == "delete":
            msg.delete()
            messages.success(request, "Message deleted.")
            return redirect("dashboard:messages")
        msg.is_read = not msg.is_read
        msg.save(update_fields=["is_read"])
        return redirect("dashboard:messages")
    if not msg.is_read:
        msg.is_read = True
        msg.save(update_fields=["is_read"])
    return render(request, "dashboard/message_detail.html", {"msg": msg})


@admin_required
def subscriber_list(request):
    if request.GET.get("export"):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="subscribers.csv"'
        writer = csv.writer(response)
        writer.writerow(["Email", "Subscribed"])
        for s in NewsletterSubscriber.objects.all():
            writer.writerow([s.email, s.created_at.date()])
        return response
    return render(request, "dashboard/subscribers.html", {"page": paginate(request, NewsletterSubscriber.objects.all(), 25)})


# --------------------------------------------------------------------------- blog
@admin_required
def post_list(request):
    posts = Post.objects.select_related("author", "category").annotate(n_comments=Count("comments")).order_by("-created_at")
    return render(request, "dashboard/posts.html", {"page": paginate(request, posts)})


class PostCreate(CrudMixin, CreateView):
    model, form_class, list_url, title = Post, PostForm, "dashboard:posts", "New article"
    success_message = "Article published."

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class PostUpdate(CrudMixin, UpdateView):
    model, form_class, list_url = Post, PostForm, "dashboard:posts"
    success_message = "Article updated."


class PostDelete(CrudDeleteView):
    model, list_url = Post, "dashboard:posts"


# --------------------------------------------------------------------------- traveler <-> guide conversations
@admin_required
def conversation_list(request):
    return render(request, "dashboard/conversations.html", {"threads": threads_for(request.user)})


# --------------------------------------------------------------------------- chatbot logs
@admin_required
def chat_list(request):
    conversations = (
        Conversation.objects.select_related("user").annotate(n=Count("messages")).filter(n__gt=0).order_by("-updated_at")
    )
    return render(
        request,
        "dashboard/chats.html",
        {"page": paginate(request, conversations, 20), "groq_enabled": bool(settings.GROQ_API_KEY)},
    )


@admin_required
def chat_detail(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk)
    return render(request, "dashboard/chat_detail.html", {"conversation": conversation, "messages_list": conversation.messages.all()})


# --------------------------------------------------------------------------- customisation
class SettingsView(CrudMixin, UpdateView):
    form_class, template_name, list_url = SiteSettingsForm, "dashboard/settings.html", "dashboard:settings"
    success_message = "Settings saved - changes are live."

    def get_object(self, queryset=None):
        return SiteSettings.objects.get_or_create(pk=1)[0]

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            title="Customization", groq_enabled=bool(settings.GROQ_API_KEY), groq_model=settings.GROQ_MODEL, **kwargs
        )


