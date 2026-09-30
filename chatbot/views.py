import json

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from core.models import SiteSettings

from .models import Conversation, Message
from .services import generate_reply

MAX_LENGTH = 1000


def _conversation(request, create=True):
    if not request.session.session_key:
        request.session.save()
    conv_id = request.session.get("chat_conversation")
    conversation = Conversation.objects.filter(pk=conv_id).first() if conv_id else None
    if conversation is None and create:
        conversation = Conversation.objects.create(
            session_key=request.session.session_key,
            user=request.user if request.user.is_authenticated else None,
        )
        request.session["chat_conversation"] = conversation.pk
    return conversation


def _rate_limited(request):
    key = f"chatbot.rate.{request.session.session_key}"
    count = cache.get(key, 0)
    if count >= settings.CHATBOT_MAX_MESSAGES_PER_HOUR:
        return True
    cache.set(key, count + 1, 3600)
    return False


def _tour_card(tour, currency):
    return {
        "title": tour.title,
        "url": tour.get_absolute_url(),
        "image": tour.cover,
        "meta": f"{tour.destination.name} · {tour.duration_days} day{'s' if tour.duration_days > 1 else ''}",
        "price": f"{currency}{tour.current_price:,.0f}",
    }


@require_POST
def send_message(request):
    site = SiteSettings.load()
    if not site.chatbot_enabled:
        return JsonResponse({"error": "The assistant is currently offline."}, status=503)
    try:
        text = (json.loads(request.body or "{}").get("message") or "").strip()
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid request."}, status=400)
    if not text:
        return JsonResponse({"error": "Message is empty."}, status=400)
    text = text[:MAX_LENGTH]

    conversation = _conversation(request)
    if _rate_limited(request):
        return JsonResponse({"error": "You're sending messages too quickly. Please try again later."}, status=429)

    reply, source, tours = generate_reply(conversation, text)
    Message.objects.create(conversation=conversation, role=Message.Role.USER, content=text, source=Message.Source.USER)
    Message.objects.create(conversation=conversation, role=Message.Role.ASSISTANT, content=reply, source=source)
    conversation.save(update_fields=["updated_at"])
    return JsonResponse(
        {"reply": reply, "source": source, "tours": [_tour_card(t, site.currency_symbol) for t in tours]}
    )


@require_GET
def history(request):
    conversation = _conversation(request, create=False)
    messages = conversation.messages.values("role", "content") if conversation else []
    return JsonResponse({"messages": list(messages)})


@require_POST
def reset(request):
    request.session.pop("chat_conversation", None)
    return JsonResponse({"ok": True})
