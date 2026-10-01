"""Thin wrapper around the Stripe SDK so the rest of the code (and the tests) never touch it directly."""
from decimal import ROUND_HALF_UP, Decimal

import stripe
from django.conf import settings

ZERO_DECIMAL = {"bif", "clp", "djf", "gnf", "jpy", "kmf", "krw", "mga", "pyg", "rwf", "ugx", "vnd", "vuv", "xaf", "xof", "xpf"}


class PaymentError(Exception):
    pass


def is_enabled():
    return bool(settings.STRIPE_SECRET_KEY)


def _client():
    if not is_enabled():
        raise PaymentError("Stripe is not configured.")
    return stripe.StripeClient(settings.STRIPE_SECRET_KEY)


def to_minor_units(amount):
    currency = settings.STRIPE_CURRENCY.lower()
    if currency in ZERO_DECIMAL:
        return int(Decimal(amount).quantize(Decimal("1"), ROUND_HALF_UP))
    return int((Decimal(amount) * 100).quantize(Decimal("1"), ROUND_HALF_UP))


def from_minor_units(value):
    currency = settings.STRIPE_CURRENCY.lower()
    return Decimal(value) if currency in ZERO_DECIMAL else Decimal(value) / 100


def create_checkout_session(booking, success_url, cancel_url):
    """Hosted Stripe Checkout for one booking. Returns (session_id, url)."""
    try:
        session = _client().v1.checkout.sessions.create(
            params={
                "mode": "payment",
                "client_reference_id": booking.reference,
                "customer_email": booking.email,
                "metadata": {"booking_reference": booking.reference},
                "payment_intent_data": {"metadata": {"booking_reference": booking.reference}},
                "line_items": [
                    {
                        "quantity": booking.travelers,
                        "price_data": {
                            "currency": settings.STRIPE_CURRENCY.lower(),
                            "unit_amount": to_minor_units(booking.unit_price),
                            "product_data": {
                                "name": booking.tour.title,
                                "description": f"{booking.reference} · {booking.travel_date:%d %b %Y}",
                            },
                        },
                    }
                ],
                "success_url": success_url,
                "cancel_url": cancel_url,
            }
        )
    except stripe.StripeError as exc:
        raise PaymentError(str(exc)) from exc
    return session.id, session.url


def retrieve_session(session_id):
    try:
        session = _client().v1.checkout.sessions.retrieve(session_id)
    except stripe.StripeError as exc:
        raise PaymentError(str(exc)) from exc
    return {
        "id": session.id,
        "paid": session.payment_status == "paid",
        "reference": session.client_reference_id,
        "amount": from_minor_units(session.amount_total or 0),
        "payment_intent": session.payment_intent or "",
    }


def parse_webhook(payload, signature):
    """Verify the Stripe signature and return the event as a plain dict."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise PaymentError("STRIPE_WEBHOOK_SECRET is not configured.")
    try:
        event = stripe.Webhook.construct_event(payload, signature, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise PaymentError(str(exc)) from exc
    return event.to_dict() if hasattr(event, "to_dict") else dict(event)


def refund(payment_intent):
    try:
        _client().v1.refunds.create(params={"payment_intent": payment_intent})
    except stripe.StripeError as exc:
        raise PaymentError(str(exc)) from exc
