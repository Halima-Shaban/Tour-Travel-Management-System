"""Single entry point for telling people that something happened."""
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import Q

from .models import Notification

logger = logging.getLogger(__name__)


def admins():
    User = get_user_model()
    return User.objects.filter(Q(is_superuser=True) | Q(profile__role="admin"), is_active=True).distinct()


def notify(recipients, title, body="", url="", kind=Notification.Kind.SYSTEM, email=False, exclude=None):
    """Create a notification for every recipient (users or querysets, ``None`` entries ignored)."""
    seen = set()
    created = []
    for user in recipients:
        if user is None or user.pk in seen or (exclude is not None and user.pk == exclude.pk):
            continue
        seen.add(user.pk)
        created.append(Notification(recipient=user, title=title, body=body[:300], url=url, kind=kind))
        if email and user.email:
            try:
                send_mail(title, f"{body}\n\n{url}", settings.DEFAULT_FROM_EMAIL, [user.email])
            except Exception:  # pragma: no cover - depends on SMTP
                logger.exception("Notification email failed")
    Notification.objects.bulk_create(created)
    return created
