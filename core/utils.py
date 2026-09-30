import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def notify_staff(subject, body):
    """Email the configured recipient; never let a mail failure break the request."""
    recipient = settings.CONTACT_RECIPIENT_EMAIL
    if not recipient:
        return
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=False)
    except Exception:  # pragma: no cover - depends on SMTP
        logger.exception("Could not send notification email")
