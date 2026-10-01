from django.utils import timezone

from accounts.permissions import is_admin
from notifications.models import Notification
from notifications.services import notify
from tours.services import booking_url_for

from .models import Message, Thread


def can_access(user, booking):
    return user.is_authenticated and (is_admin(user) or user.pk in (booking.user_id, booking.guide_id))


def thread_for(booking):
    return Thread.objects.get_or_create(booking=booking)[0]


def threads_for(user):
    """Threads a user takes part in, newest activity first, annotated with unread counts."""
    qs = Thread.objects.select_related("booking", "booking__tour", "booking__user", "booking__guide")
    if not is_admin(user):
        from django.db.models import Q

        qs = qs.filter(Q(booking__user=user) | Q(booking__guide=user))
    threads = list(qs.filter(messages__isnull=False).distinct())
    for t in threads:
        t.unread = t.unread_for(user)
        t.last = t.messages.last()
    return threads


def unread_total(user):
    return sum(t.unread for t in threads_for(user))


def post_message(thread, sender, body):
    message = Message.objects.create(thread=thread, sender=sender, body=body.strip()[:2000])
    Thread.objects.filter(pk=thread.pk).update(updated_at=timezone.now())
    thread.mark_read(sender)
    booking = thread.booking
    name = sender.get_full_name() or sender.username
    for user in thread.participants():
        if user.pk != sender.pk:
            notify([user], f"New message from {name}", body[:140], booking_url_for(user, booking) + "#chat",
                   kind=Notification.Kind.MESSAGE)
    return message


def serialize(message, viewer):
    sender = message.sender
    booking = message.thread.booking
    if sender.pk == booking.guide_id:
        role = "Guide"
    elif sender.pk == booking.user_id:
        role = "Traveler"
    else:
        role = "Office"
    return {
        "id": message.pk,
        "body": message.body,
        "mine": sender.pk == viewer.pk,
        "sender": sender.get_full_name() or sender.username,
        "role": role,
        "time": timezone.localtime(message.created_at).strftime("%d %b, %H:%M"),
    }
