from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.models import SiteSettings
from core.utils import notify_staff

from . import services
from .forms import BookingForm, ReviewForm, TourFilterForm
from .models import Booking, Destination, Review, Tour

SORT_MAP = {
    "price": "price",
    "-price": "-price",
    "duration": "duration_days",
    "-rating": "-avg_rating",
    "-created": "-created_at",
}


def filter_tours(params, queryset=None):
    """Apply the public search filters; shared by the listing page and the chatbot."""
    form = TourFilterForm(params or None)
    tours = (
        (queryset or Tour.objects.active())
        .select_related("destination", "guide")
        .with_rating()
        .order_by("-is_featured", "-created_at")
    )
    if form.is_valid():
        data = form.cleaned_data
        if data["q"]:
            q = data["q"]
            tours = tours.filter(
                Q(title__icontains=q) | Q(summary__icontains=q) | Q(destination__name__icontains=q)
                | Q(destination__country__icontains=q)
            )
        if data["destination"]:
            tours = tours.filter(destination=data["destination"])
        if data["category"]:
            tours = tours.filter(category=data["category"])
        if data["duration"]:
            low, high = map(int, data["duration"].split("-"))
            tours = tours.filter(duration_days__gte=low, duration_days__lte=high)
        if data["max_price"] is not None:
            tours = tours.filter(price__lte=data["max_price"])
        if data["sort"] in SORT_MAP:
            tours = tours.order_by(SORT_MAP[data["sort"]])
    return form, tours


def tour_list(request):
    form, tours = filter_tours(request.GET)
    page = Paginator(tours, 9).get_page(request.GET.get("page"))
    return render(request, "tours/list.html", {"form": form, "page": page, "total": tours.count()})


def tour_detail(request, slug):
    tour = get_object_or_404(Tour.objects.active().select_related("destination", "guide__profile"), slug=slug)
    site = SiteSettings.load()
    booking_form = BookingForm(tour=tour, initial=_booking_initial(request.user))

    if request.method == "POST" and "book" in request.POST:
        if not site.booking_enabled:
            messages.error(request, "Online booking is temporarily disabled. Please contact us.")
            return redirect(tour)
        booking_form = BookingForm(request.POST, tour=tour)
        if booking_form.is_valid():
            booking = booking_form.save(commit=False)
            booking.tour = tour
            if request.user.is_authenticated:
                booking.user = request.user
            booking.save()
            services.on_booking_created(booking)
            notify_staff(
                f"New booking {booking.reference}",
                f"{booking.full_name} booked {tour} for {booking.travel_date} ({booking.travelers} travelers).",
            )
            request.session["last_booking"] = booking.reference
            return redirect("tours:booking_success", reference=booking.reference)

    reviews = tour.reviews.filter(is_approved=True).select_related("user")
    user_review = None
    if request.user.is_authenticated:
        user_review = reviews.filter(user=request.user).first()
    related = Tour.objects.active().filter(destination=tour.destination).exclude(pk=tour.pk).with_rating()[:3]
    return render(
        request,
        "tours/detail.html",
        {
            "tour": tour,
            "booking_form": booking_form,
            "review_form": ReviewForm(),
            "reviews": reviews,
            "user_review": user_review,
            "related": related,
        },
    )


def _booking_initial(user):
    if not user.is_authenticated:
        return {}
    return {
        "full_name": user.get_full_name(),
        "email": user.email,
        "phone": getattr(getattr(user, "profile", None), "phone", ""),
    }


def booking_success(request, reference):
    booking = get_object_or_404(Booking.objects.select_related("tour"), reference=reference)
    # Only the booker (by session or account) may view the confirmation.
    if request.session.get("last_booking") != reference and booking.user != request.user:
        return redirect("tours:list")
    return render(request, "tours/booking_success.html", {"booking": booking})


@login_required
def add_review(request, slug):
    tour = get_object_or_404(Tour.objects.active(), slug=slug)
    if request.method == "POST":
        form = ReviewForm(request.POST)
        if Review.objects.filter(tour=tour, user=request.user).exists():
            messages.info(request, "You have already reviewed this tour.")
        elif form.is_valid():
            review = form.save(commit=False)
            review.tour, review.user = tour, request.user
            review.save()
            messages.success(request, "Thanks for sharing your experience!")
        else:
            messages.error(request, "Please choose a rating and write a short comment.")
    return redirect(reverse("tours:detail", args=[slug]) + "#reviews")


def destination_list(request):
    destinations = Destination.objects.annotate(tour_count=Count("tours", filter=Q(tours__is_active=True)))
    return render(request, "tours/destinations.html", {"destinations": destinations})


def destination_detail(request, slug):
    destination = get_object_or_404(Destination, slug=slug)
    tours = destination.tours.active().with_rating().select_related("destination")
    return render(request, "tours/destination_detail.html", {"destination": destination, "tours": tours})
