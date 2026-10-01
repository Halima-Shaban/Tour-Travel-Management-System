"""Booking workflow - the single place where the website, the admin dashboard and the guide
dashboard change a booking. Every transition notifies the people involved."""
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from accounts.permissions import is_admin
from notifications.models import Notification
from notifications.services import admins, notify

from .models import Booking

K = Notification.Kind


def booking_url_for(user, booking):
    """Where a given user should land to see this booking."""
    if user is not None and is_admin(user):
        return reverse("dashboard:booking_edit", args=[booking.pk])
    if user is not None and booking.guide_id == user.pk:
        return reverse("guide:booking_detail", args=[booking.pk])
    return reverse("accounts:booking_detail", args=[booking.reference])


def _notify_each(users, title, body, booking, kind, email=False, exclude=None):
    for user in users:
        if user is None or (exclude is not None and user.pk == exclude.pk):
            continue
        notify([user], title, body, booking_url_for(user, booking), kind=kind, email=email)


def guide_conflicts(booking):
    """Other accepted trips of the same guide that overlap this booking's dates."""
    if not booking.guide_id:
        return Booking.objects.none()
    candidates = (
        Booking.objects.filter(guide=booking.guide, guide_status=Booking.GuideResponse.ACCEPTED)
        .exclude(pk=booking.pk)
        .exclude(status=Booking.Status.CANCELLED)
        .exclude(tour=booking.tour, travel_date=booking.travel_date)  # same departure is not a conflict
        .filter(travel_date__lte=booking.end_date)
        .select_related("tour")
    )
    return [b for b in candidates if b.end_date >= booking.travel_date]


# --------------------------------------------------------------------------- lifecycle
def on_booking_created(booking):
    title = f"New booking {booking.reference}"
    body = f"{booking.full_name} · {booking.tour.title} · {booking.travel_date:%d %b %Y} · {booking.travelers} pax"
    _notify_each(admins(), title, body, booking, K.BOOKING)
    if booking.guide:
        _notify_each([booking.guide], "New trip request - please accept or decline", body, booking, K.GUIDE, email=True)
    if booking.user:
        _notify_each([booking.user], f"Booking {booking.reference} received",
                     "We'll let you know as soon as your guide confirms.", booking, K.BOOKING)


@transaction.atomic
def guide_accept(booking, guide):
    if booking.guide_id != guide.pk or not booking.can_guide_respond:
        return False
    booking.guide_status = Booking.GuideResponse.ACCEPTED
    booking.guide_responded_at = timezone.now()
    booking.guide_decline_reason = ""
    if booking.status == Booking.Status.PENDING:
        booking.status = Booking.Status.CONFIRMED
    booking.save()
    name = guide.get_full_name() or guide.username
    _notify_each([booking.user], f"Your trip is confirmed! ({booking.reference})",
                 f"{name} will be your guide for {booking.tour.title} on {booking.travel_date:%d %b %Y}.",
                 booking, K.GUIDE, email=True)
    _notify_each(admins(), f"{name} accepted {booking.reference}", booking.tour.title, booking, K.GUIDE)
    return True


@transaction.atomic
def guide_decline(booking, guide, reason=""):
    if booking.guide_id != guide.pk or not booking.can_guide_respond:
        return False
    booking.guide_status = Booking.GuideResponse.DECLINED
    booking.guide_responded_at = timezone.now()
    booking.guide_decline_reason = reason[:255]
    booking.save()
    name = guide.get_full_name() or guide.username
    _notify_each(admins(), f"{name} declined {booking.reference} - reassign a guide",
                 reason or "No reason given.", booking, K.GUIDE, email=True)
    return True


@transaction.atomic
def assign_guide(booking, guide, by=None):
    """Admin (re)assigns a guide to one booking; the new guide must accept it."""
    previous = booking.guide
    booking.guide = guide
    booking.guide_status = Booking.GuideResponse.PENDING
    booking.guide_responded_at = None
    booking.guide_decline_reason = ""
    booking.save()
    body = f"{booking.tour.title} · {booking.travel_date:%d %b %Y} · {booking.travelers} pax"
    if guide:
        _notify_each([guide], "You've been assigned a trip - please accept or decline", body, booking, K.GUIDE, email=True)
    if previous and previous != guide:
        _notify_each([previous], f"{booking.reference} was reassigned to another guide", body, booking, K.GUIDE)


@transaction.atomic
def cancel_booking(booking, by):
    if booking.status == Booking.Status.CANCELLED:
        return False
    booking.status = Booking.Status.CANCELLED
    booking.save()
    who = "the customer" if by == booking.user else "the office"
    body = f"{booking.tour.title} on {booking.travel_date:%d %b %Y} was cancelled by {who}."
    _notify_each([booking.guide, booking.user, *admins()], f"Booking {booking.reference} cancelled", body,
                 booking, K.BOOKING, exclude=by)
    return True


@transaction.atomic
def mark_paid(booking, amount=None, payment_intent=""):
    """Idempotent: called by the Stripe webhook, the success redirect, or an admin marking cash payment."""
    booking = Booking.objects.select_for_update().get(pk=booking.pk)
    if booking.payment_status == Booking.Payment.PAID:
        return False
    booking.payment_status = Booking.Payment.PAID
    booking.amount_paid = amount if amount is not None else booking.total_price
    booking.paid_at = timezone.now()
    if payment_intent:
        booking.stripe_payment_intent = payment_intent
    booking.save()
    body = f"{booking.full_name} paid {booking.amount_paid} for {booking.tour.title}."
    _notify_each([*admins(), booking.guide], f"Payment received · {booking.reference}", body, booking, K.PAYMENT)
    _notify_each([booking.user], f"Payment confirmed · {booking.reference}",
                 "Thank you! Your payment was received.", booking, K.PAYMENT, email=True)
    return True


@transaction.atomic
def mark_refunded(booking):
    if booking.payment_status == Booking.Payment.REFUNDED:
        return False
    booking.payment_status = Booking.Payment.REFUNDED
    booking.save()
    _notify_each([booking.user], f"Refund issued · {booking.reference}",
                 "Your refund is on its way - it may take 5-10 days to appear.", booking, K.PAYMENT, email=True)
    return True
