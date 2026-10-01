"""Guide dashboard. A guide only sees bookings assigned to them (``Booking.guide``); every query is
scoped to ``request.user`` so other guides' data returns 404."""
import datetime
from datetime import timedelta

from django.contrib import messages
from django.db.models import Avg, Count, Q, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.forms import GuideProfileForm, UserForm
from accounts.permissions import guide_required
from dashboard import analytics
from messaging.services import threads_for
from tours import services
from tours.forms import DeclineForm, GuideNotesForm, UnavailabilityForm
from tours.models import Booking, GuideUnavailability, Review, Tour

STATUS_COLORS = {"pending": "#f59e0b", "confirmed": "#0f766e", "completed": "#16a34a", "cancelled": "#dc2626"}
R = Booking.GuideResponse


def my_bookings(user):
    return Booking.objects.filter(guide=user).select_related("tour", "tour__destination", "user")


def pending_requests(user):
    return (
        my_bookings(user)
        .filter(guide_status=R.PENDING, travel_date__gte=timezone.localdate())
        .exclude(status=Booking.Status.CANCELLED)
        .order_by("travel_date")
    )


@guide_required
def home(request):
    today = timezone.localdate()
    bookings = my_bookings(request.user)
    accepted = bookings.filter(guide_status=R.ACCEPTED).exclude(status=Booking.Status.CANCELLED)
    upcoming = accepted.filter(travel_date__gte=today).order_by("travel_date")
    reviews = Review.objects.filter(tour__guide=request.user, is_approved=True)
    requests = pending_requests(request.user)
    context = {
        "kpis": {
            "requests": requests.count(),
            "upcoming": upcoming.count(),
            "travelers_upcoming": upcoming.aggregate(n=Sum("travelers"))["n"] or 0,
            "completed": bookings.filter(status=Booking.Status.COMPLETED).count(),
            "rating": round(reviews.aggregate(v=Avg("rating"))["v"] or 0, 1),
            "reviews": reviews.count(),
            "tours": request.user.guided_tours.filter(is_active=True).count(),
        },
        "requests": requests[:5],
        "next_trip": upcoming.first(),
        "upcoming": upcoming[:6],
        "this_week": upcoming.filter(travel_date__lte=today + timedelta(days=7)),
        "monthly": analytics.monthly_series(accepted, 6),
        "latest_reviews": reviews.select_related("user", "tour")[:4],
        "time_off": GuideUnavailability.objects.filter(guide=request.user, end_date__gte=today)[:3],
    }
    return render(request, "guide/home.html", context)


@guide_required
def tour_list(request):
    today = timezone.localdate()
    mine = Q(bookings__guide=request.user) & ~Q(bookings__status="cancelled")
    tours = (
        Tour.objects.filter(Q(guide=request.user) | Q(bookings__guide=request.user))
        .distinct()
        .select_related("destination")
        .with_rating()
        .annotate(
            n_upcoming=Count("bookings", filter=mine & Q(bookings__travel_date__gte=today), distinct=True),
            n_travelers=Sum("bookings__travelers", filter=mine),
        )
    )
    return render(request, "guide/tours.html", {"tours": tours})


def _my_tour(request, slug):
    tour = Tour.objects.select_related("destination").filter(slug=slug).first()
    if not tour or not (tour.guide_id == request.user.pk or tour.bookings.filter(guide=request.user).exists()):
        raise Http404
    return tour


@guide_required
def tour_detail(request, slug):
    tour = _my_tour(request, slug)
    departures = (
        tour.bookings.filter(guide=request.user, travel_date__gte=timezone.localdate())
        .exclude(status=Booking.Status.CANCELLED)
        .values("travel_date")
        .annotate(
            groups=Count("id"),
            travelers=Sum("travelers"),
            pending=Count("id", filter=Q(guide_status=R.PENDING)),
        )
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
    """Passenger manifest for one departure, with every named participant - printable."""
    tour = _my_tour(request, slug)
    try:
        date = datetime.date.fromisoformat(date)
    except ValueError:
        raise Http404("Invalid date")
    bookings = (
        tour.bookings.filter(travel_date=date, guide=request.user)
        .exclude(status=Booking.Status.CANCELLED)
        .prefetch_related("participants")
        .order_by("full_name")
    )
    total = bookings.aggregate(n=Sum("travelers"))["n"] or 0
    return render(request, "guide/manifest.html", {"tour": tour, "bookings": bookings, "date": date, "total": total})


@guide_required
def booking_list(request):
    today = timezone.localdate()
    bookings = my_bookings(request.user)
    tab = request.GET.get("tab", "requests")
    tabs = {
        "requests": pending_requests(request.user),
        "upcoming": bookings.filter(guide_status=R.ACCEPTED, travel_date__gte=today).exclude(status="cancelled").order_by("travel_date"),
        "past": bookings.filter(travel_date__lt=today).order_by("-travel_date"),
        "declined": bookings.filter(guide_status=R.DECLINED).order_by("-travel_date"),
        "all": bookings.order_by("-travel_date"),
    }
    if tab not in tabs:
        tab = "requests"
    counts = {key: qs.count() for key, qs in tabs.items() if key in ("requests", "upcoming")}
    return render(request, "guide/bookings.html", {"bookings": tabs[tab], "tab": tab, "counts": counts})


@guide_required
def booking_detail(request, pk):
    booking = get_object_or_404(my_bookings(request.user).prefetch_related("participants"), pk=pk)
    notes_form = GuideNotesForm(request.POST or None, instance=booking)
    if request.method == "POST" and "save_notes" in request.POST and notes_form.is_valid():
        notes_form.save()
        messages.success(request, "Notes saved.")
        return redirect("guide:booking_detail", pk=pk)
    return render(
        request,
        "guide/booking_detail.html",
        {
            "booking": booking,
            "notes_form": notes_form,
            "decline_form": DeclineForm(),
            "conflicts": services.guide_conflicts(booking),
            "time_off": GuideUnavailability.overlapping(request.user, booking.travel_date, booking.end_date),
        },
    )


@guide_required
@require_POST
def respond(request, pk):
    booking = get_object_or_404(my_bookings(request.user), pk=pk)
    action = request.POST.get("action")
    if action == "accept" and services.guide_accept(booking, request.user):
        messages.success(request, f"You accepted {booking.reference}. The traveler has been notified.")
    elif action == "decline":
        form = DeclineForm(request.POST)
        reason = form.cleaned_data["reason"] if form.is_valid() else ""
        if services.guide_decline(booking, request.user, reason):
            messages.info(request, f"You declined {booking.reference}. The office will reassign it.")
    elif action == "complete" and booking.guide_status == R.ACCEPTED and booking.status == Booking.Status.CONFIRMED \
            and booking.travel_date <= timezone.localdate():
        booking.status = Booking.Status.COMPLETED
        booking.save(update_fields=["status", "updated_at"])
        messages.success(request, "Trip marked as completed.")
    else:
        messages.error(request, "This booking can no longer be changed.")
    if request.POST.get("next") == "list":
        return redirect("guide:bookings")
    return redirect("guide:booking_detail", pk=pk)


@guide_required
def calendar(request):
    form = UnavailabilityForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        block = form.save(commit=False)
        block.guide = request.user
        block.save()
        clashes = my_bookings(request.user).filter(guide_status=R.ACCEPTED).exclude(status="cancelled") \
            .filter(travel_date__lte=block.end_date, travel_date__gte=block.start_date - timedelta(days=30))
        clashes = [b for b in clashes if b.overlaps(block.start_date, block.end_date)]
        if clashes:
            messages.warning(request, f"Time off saved, but you have {len(clashes)} accepted trip(s) in that period - contact the office.")
        else:
            messages.success(request, "Time off saved. New bookings won't be accepted on those dates.")
        return redirect("guide:calendar")
    blocks = GuideUnavailability.objects.filter(guide=request.user, end_date__gte=timezone.localdate())
    return render(request, "guide/calendar.html", {"form": form, "blocks": blocks})


@guide_required
@require_POST
def delete_time_off(request, pk):
    GuideUnavailability.objects.filter(guide=request.user, pk=pk).delete()
    messages.info(request, "Time off removed.")
    return redirect("guide:calendar")


@guide_required
def calendar_events(request):
    """FullCalendar feed: trips (spanning the tour duration) plus time off as background blocks."""
    events = []
    for b in my_bookings(request.user).exclude(status=Booking.Status.CANCELLED).exclude(guide_status=R.DECLINED):
        pending = b.guide_status == R.PENDING
        events.append(
            {
                "title": f"{'⏳ ' if pending else ''}{b.tour.title} · {b.travelers} pax",
                "start": b.travel_date.isoformat(),
                "end": (b.end_date + timedelta(days=1)).isoformat(),
                "url": f"/guide/bookings/{b.pk}/",
                "color": "#94a3b8" if pending else STATUS_COLORS.get(b.status),
            }
        )
    for block in GuideUnavailability.objects.filter(guide=request.user):
        events.append(
            {
                "title": block.reason or "Time off",
                "start": block.start_date.isoformat(),
                "end": (block.end_date + timedelta(days=1)).isoformat(),
                "display": "background",
                "color": "#ef4444",
            }
        )
    return JsonResponse(events, safe=False)


@guide_required
def inbox(request):
    return render(request, "guide/inbox.html", {"threads": threads_for(request.user)})


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
