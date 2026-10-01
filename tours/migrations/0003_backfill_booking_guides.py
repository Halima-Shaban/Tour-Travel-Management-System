from django.db import migrations


def backfill(apps, schema_editor):
    """Existing bookings inherit their tour's guide; confirmed/completed ones count as accepted."""
    Booking = apps.get_model("tours", "Booking")
    for booking in Booking.objects.filter(guide__isnull=True).select_related("tour"):
        booking.guide_id = booking.tour.guide_id
        if booking.status in ("confirmed", "completed"):
            booking.guide_status = "accepted"
        if booking.payment_status == "paid" and not booking.amount_paid:
            booking.amount_paid = booking.total_price
        booking.save(update_fields=["guide", "guide_status", "amount_paid"])


class Migration(migrations.Migration):
    dependencies = [("tours", "0002_guide_assignment_payments_participants")]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
