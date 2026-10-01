from django.conf import settings
from django.db import models
from django.utils import timezone


class Thread(models.Model):
    """One conversation per booking between the customer, the assigned guide and the office."""

    booking = models.OneToOneField("tours.Booking", on_delete=models.CASCADE, related_name="thread")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Thread for {self.booking.reference}"

    def participants(self):
        """Users who take part directly (admins can always join)."""
        return [u for u in (self.booking.user, self.booking.guide) if u is not None]

    def unread_for(self, user):
        state = self.read_states.filter(user=user).first()
        messages = self.messages.exclude(sender=user)
        if state:
            messages = messages.filter(created_at__gt=state.last_read_at)
        return messages.count()

    def mark_read(self, user):
        ReadState.objects.update_or_create(thread=self, user=user, defaults={"last_read_at": timezone.now()})


class Message(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.sender}: {self.body[:40]}"


class ReadState(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="read_states")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    last_read_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["thread", "user"], name="one_read_state_per_user")]
