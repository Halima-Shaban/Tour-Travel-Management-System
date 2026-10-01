from urllib.parse import urlencode

from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def query(context, **kwargs):
    """Rebuild the current query string with some keys replaced (used by pagination/sorting)."""
    params = context["request"].GET.copy()
    for key, value in kwargs.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    return "?" + urlencode(params, doseq=True) if params else "?"


@register.filter
def money(value, symbol="$"):
    try:
        return f"{symbol}{float(value):,.0f}"
    except (TypeError, ValueError):
        return value


@register.filter
def stars(value):
    """Return a list of 5 icon names for a rating value (full/half/empty)."""
    value = float(value or 0)
    icons = []
    for i in range(1, 6):
        if value >= i:
            icons.append("bi-star-fill")
        elif value >= i - 0.5:
            icons.append("bi-star-half")
        else:
            icons.append("bi-star")
    return icons


STATUS_COLORS = {
    "pending": "warning",
    "confirmed": "primary",
    "completed": "success",
    "cancelled": "danger",
    "paid": "success",
    "unpaid": "secondary",
    "refunded": "info",
}


@register.filter
def status_color(value):
    return STATUS_COLORS.get(str(value).lower(), "secondary")


@register.filter
def initials(user):
    name = user.get_full_name() or user.username
    return "".join(part[0] for part in name.split()[:2]).upper()


@register.simple_tag
def admin_counts():
    """Badge counters for the admin sidebar."""
    from core.models import ContactMessage
    from tours.models import Booking

    return {
        "pending": Booking.objects.filter(status=Booking.Status.PENDING).count(),
        "unread": ContactMessage.objects.filter(is_read=False).count(),
    }


@register.simple_tag(takes_context=True)
def active(context, *prefixes, exact=False):
    """'active' when the current path matches one of the url names given (by prefix, or exactly)."""
    from django.urls import reverse

    path = context["request"].path
    for name in prefixes:
        url = reverse(name)
        if (exact and path == url) or (not exact and path.startswith(url)):
            return "active"
    return ""


@register.simple_tag(takes_context=True)
def guide_counts(context):
    """Badge counters for the guide sidebar."""
    from django.utils import timezone

    from messaging.services import unread_total
    from tours.models import Booking

    user = context["request"].user
    requests = (
        Booking.objects.filter(guide=user, guide_status="pending", travel_date__gte=timezone.localdate())
        .exclude(status="cancelled")
        .count()
    )
    return {"requests": requests, "unread": unread_total(user)}
