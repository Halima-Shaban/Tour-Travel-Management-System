import logging

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from tours import services
from tours.models import Booking

from . import gateway

logger = logging.getLogger(__name__)


def _can_pay(request, booking):
    return booking.user_id == request.user.pk if booking.user_id else request.session.get("last_booking") == booking.reference


def _return_url(request, booking):
    if booking.user_id:
        return reverse("accounts:booking_detail", args=[booking.reference])
    return reverse("tours:booking_success", args=[booking.reference])


@require_POST
def checkout(request, reference):
    booking = get_object_or_404(Booking.objects.select_related("tour"), reference=reference)
    back = _return_url(request, booking)
    if not _can_pay(request, booking):
        return redirect("tours:list")
    if not gateway.is_enabled() or not booking.can_pay:
        messages.info(request, "This booking can't be paid online right now.")
        return redirect(back)
    success = request.build_absolute_uri(reverse("payments:success", args=[booking.reference])) + "?session_id={CHECKOUT_SESSION_ID}"
    try:
        session_id, url = gateway.create_checkout_session(booking, success, request.build_absolute_uri(back))
    except gateway.PaymentError:
        logger.exception("Stripe checkout failed for %s", booking.reference)
        messages.error(request, "We couldn't start the payment. Please try again in a moment.")
        return redirect(back)
    booking.stripe_session_id = session_id
    booking.save(update_fields=["stripe_session_id", "updated_at"])
    return redirect(url)


def success(request, reference):
    """Stripe redirects here; confirm the session server-side (the webhook does the same, idempotently)."""
    booking = get_object_or_404(Booking, reference=reference)
    session_id = request.GET.get("session_id", "")
    if session_id and session_id == booking.stripe_session_id and gateway.is_enabled():
        try:
            session = gateway.retrieve_session(session_id)
            if session["paid"] and session["reference"] == booking.reference:
                services.mark_paid(booking, session["amount"], session["payment_intent"])
                messages.success(request, "Payment received - thank you!")
        except gateway.PaymentError:
            logger.exception("Could not verify Stripe session %s", session_id)
            messages.info(request, "Payment is being processed - we'll confirm shortly.")
    return redirect(_return_url(request, booking))


@csrf_exempt
@require_POST
def webhook(request):
    try:
        event = gateway.parse_webhook(request.body, request.META.get("HTTP_STRIPE_SIGNATURE", ""))
    except gateway.PaymentError as exc:
        logger.warning("Rejected Stripe webhook: %s", exc)
        return HttpResponse(status=400)

    obj = event.get("data", {}).get("object", {})
    kind = event.get("type")
    if kind in ("checkout.session.completed", "checkout.session.async_payment_succeeded") and obj.get("payment_status") == "paid":
        booking = Booking.objects.filter(reference=obj.get("client_reference_id")).first()
        if booking:
            services.mark_paid(booking, gateway.from_minor_units(obj.get("amount_total") or 0), obj.get("payment_intent") or "")
    elif kind == "charge.refunded":
        booking = Booking.objects.filter(stripe_payment_intent=obj.get("payment_intent") or "-").first()
        if booking:
            services.mark_refunded(booking)
    return HttpResponse(status=200)
