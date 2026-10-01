from django import template

register = template.Library()


@register.inclusion_tag("notifications/_bell.html", takes_context=True)
def notification_bell(context, variant="dash"):
    user = context["request"].user
    if not user.is_authenticated:
        return {"show": False}
    qs = user.notifications.all()
    return {
        "show": True,
        "variant": variant,
        "unread": qs.filter(is_read=False).count(),
        "items": qs[:6],
        "csrf_token": context.get("csrf_token"),
    }
