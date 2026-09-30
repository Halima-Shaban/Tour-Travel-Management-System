"""Guide dashboard: a guide only ever sees tours assigned to them and the bookings on those tours."""
import datetime
from datetime import timedelta

from django.contrib import messages
from django.db.models import Avg, Count, Q, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.forms import GuideProfileForm, UserForm
from accounts.permissions import guide_required
from dashboard import analytics
from tours.forms import GuideBookingForm
from tours.models import Booking, Review, Tour

STATUS_COLORS = {"pending": "#f59e0b", "confirmed": "#0f766e", "completed": "#16a34a", "cancelled": "#dc2626"}


def my_bookings(user):
    return Booking.objects.filter(tour__guide=user).select_related("tour", "tour__destination")


@guide_required
def home(request):
    today = timezone.localdate()
    bookings = my_bookings(request.user)
    active = bookings.exclude(status=Booking.Status.CANCELLED)
    upcoming = active.filter(travel_date__gte=today).order_by("travel_date")
    reviews = Review.objects.filter(tour__guide=request.user, is_approved=True)
    context = {
        "kpis": {
            "tours": request.user.guided_tours.filter(is_active=True).count(),
            "upcoming": upcoming.count(),
            "travelers_upcoming": upcoming.aggregate(n=Sum("travelers"))["n"] or 0,
            "completed": bookings.filter(status=Booking.Status.COMPLETED).count(),
            "pending": bookings.filter(status=Booking.Status.PENDING).count(),
            "rating": round(reviews.aggregate(v=Avg("rating"))["v"] or 0, 1),
            "reviews": reviews.count(),
        },
        "next_trip": upcoming.filter(status=Booking.Status.CONFIRMED).first() or upcoming.first(),
        "upcoming": upcoming[:6],
        "this_week": upcoming.filter(travel_date__lte=today + timedelta(days=7)),
        "monthly": analytics.monthly_series(bookings, 6),
        "status": analytics.status_breakdown(bookings),
        "latest_reviews": reviews.select_related("user", "tour")[:4],
    }
    return render(request, "guide/home.html", context)


@guide_required
def tour_list(request):
    tours = (
        request.user.guided_tours.select_related("destination")
        .with_rating()
        .annotate(
            n_upcoming=Count("bookings", filter=Q(bookings__travel_date__gte=timezone.localdate()) & ~Q(bookings__status="cancelled")),
            n_travelers=Sum("bookings__travelers", filter=~Q(bookings__status="cancelled")),
        )
    )
    return render(request, "guide/tours.html", {"tours": tours})


@guide_required
def tour_detail(request, slug):
    tour = get_object_or_404(Tour.objects.select_related("destination"), slug=slug, guide=request.user)
    today = timezone.localdate()
    departures = (
        tour.bookings.exclude(status=Booking.Status.CANCELLED)
        .filter(travel_date__gte=today)
        .values("travel_date")
        .annotate(groups=Count("id"), travelers=Sum("travelers"))
        .order_by("travel_date")
    )
    for dep in departures:
        dep["seats_left"] = max(tour.max_group_size - dep["travelers"], 0)
    return render(
        request,
        "guide/tour_detail.html",
        {"tour": tour, "departures": departures, "reviews": tour.reviews.filter(is_approved=True).select_related("user")[:10]},
    )


@guide_required
def manifest(request, slug, date):
    """Passenger manifest for one departure - printable."""
    tour = get_object_or_404(Tour, slug=slug, guide=request.user)
    try:
        date = datetime.date.fromisoformat(date)
    except ValueError:
        raise Http404("Invalid date")
    bookings = tour.bookings.filter(travel_date=date).exclude(status=Booking.Status.CANCELLED).order_by("full_name")
    total = bookings.aggregate(n=Sum("travelers"))["n"] or 0
    return render(request, "guide/manifest.html", {"tour": tour, "bookings": bookings, "date": date, "total": total})


@guide_required
def booking_list(request):
    bookings = my_bookings(request.user)
    when = request.GET.get("when", "upcoming")
    today = timezone.localdate()
    if when == "upcoming":
        bookings = bookings.filter(travel_date__gte=today).order_by("travel_date")
    elif when == "past":
        bookings = bookings.filter(travel_date__lt=today).order_by("-travel_date")
    if status := request.GET.get("status"):
        bookings = bookings.filter(status=status)
    return render(
        request, "guide/bookings.html", {"bookings": bookings, "when": when, "statuses": Booking.Status.choices}
    )


@guide_required
def booking_detail(request, pk):
    booking = get_object_or_404(my_bookings(request.user), pk=pk)
    form = GuideBookingForm(request.POST or None, instance=booking)
    if booking.status == Booking.Status.CANCELLED:
        form = None
    elif request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Booking {booking.reference} updated.")
        return redirect("guide:bookings")
    return render(request, "guide/booking_detail.html", {"booking": booking, "form": form})


@guide_required
def calendar(request):
    return render(request, "guide/calendar.html")


@guide_required
def calendar_events(request):
    """JSON feed for FullCalendar: one event per booking, spanning the tour duration."""
    events = []
    for b in my_bookings(request.user).exclude(status=Booking.Status.CANCELLED):
        events.append(
            {
                "title": f"{b.tour.title} · {b.travelers} pax",
                "start": b.travel_date.isoformat(),
                "end": (b.end_date + timedelta(days=1)).isoformat(),
                "url": f"/guide/bookings/{b.pk}/",
                "color": STATUS_COLORS.get(b.status),
            }
        )
    return JsonResponse(events, safe=False)


@guide_required
def reviews(request):
    reviews = Review.objects.filter(tour__guide=request.user, is_approved=True).select_related("user", "tour")
    summary = reviews.aggregate(avg=Avg("rating"), n=Count("id"))
    distribution = {i: reviews.filter(rating=i).count() for i in range(5, 0, -1)}
    return render(request, "guide/reviews.html", {"reviews": reviews, "summary": summary, "distribution": distribution})


@guide_required
def profile(request):
    user_form = UserForm(request.POST or None, instance=request.user)
    profile_form = GuideProfileForm(request.POST or None, request.FILES or None, instance=request.user.profile)
    if request.method == "POST" and user_form.is_valid() and profile_form.is_valid():
        user_form.save()
        profile_form.save()
        messages.success(request, "Profile updated.")
        return redirect("guide:profile")
    return render(request, "guide/profile.html", {"user_form": user_form, "profile_form": profile_form})
