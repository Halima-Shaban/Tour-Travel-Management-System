"""Aggregations used by the admin and guide dashboards (kept out of the views for reuse/testing)."""
from datetime import date

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from tours.models import Booking


def last_n_months(n=12):
    today = timezone.localdate().replace(day=1)
    months = []
    y, m = today.year, today.month
    for _ in range(n):
        months.append(date(y, m, 1))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return months[::-1]


def monthly_series(bookings, n=12):
    """Bookings count, revenue and travelers per month for the last ``n`` months (by travel date)."""
    months = last_n_months(n)
    rows = (
        bookings.exclude(status=Booking.Status.CANCELLED)
        .filter(travel_date__gte=months[0])
        .annotate(month=TruncMonth("travel_date"))
        .values("month")
        .annotate(count=Count("id"), revenue=Sum("total_price"), travelers=Sum("travelers"))
    )
    by_month = {}
    for row in rows:
        month = row["month"]
        key = month.date() if hasattr(month, "date") else month
        by_month[key.replace(day=1)] = row
    return {
        "labels": [m.strftime("%b %y") for m in months],
        "bookings": [by_month.get(m, {}).get("count", 0) for m in months],
        "revenue": [float(by_month.get(m, {}).get("revenue") or 0) for m in months],
        "travelers": [by_month.get(m, {}).get("travelers") or 0 for m in months],
    }


def status_breakdown(bookings):
    counts = dict(bookings.values_list("status").annotate(n=Count("id")))
    return {
        "labels": [label for _, label in Booking.Status.choices],
        "values": [counts.get(value, 0) for value, _ in Booking.Status.choices],
    }


def growth(current, previous):
    if not previous:
        return None
    return round((current - previous) / previous * 100, 1)
