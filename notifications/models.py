from django.conf import settings
from django.db import models


class Notification(models.Model):
    """In-app notification shown in the bell menu of the website and both dashboards."""

    class Kind(models.TextChoices):
        BOOKING = "booking", "Booking"
        GUIDE = "guide", "Guide"
        PAYMENT = "payment", "Payment"
        MESSAGE = "message", "Message"
        SYSTEM = "system", "System"

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.SYSTEM)
    title = models.CharField(max_length=160)
    body = models.CharField(max_length=300, blank=True)
    url = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read"])]

    def __str__(self):
        return f"{self.recipient}: {self.title}"

    @property
    def icon(self):
        return {
            "booking": "bi-calendar-check",
            "guide": "bi-person-badge",
            "payment": "bi-credit-card",
            "message": "bi-chat-dots",
        }.get(self.kind, "bi-bell")
