"""Chatbot engine: Groq LLM (with model fallback) and an offline, database-backed assistant."""
import logging
import re

import requests
from django.conf import settings
from django.db.models import Q

from core.models import SiteSettings
from tours.models import Tour

from .knowledge import system_prompt

logger = logging.getLogger("chatbot")
HISTORY_LIMIT = 10
ARABIC = re.compile(r"[؀-ۿ]")


class LLMUnavailable(Exception):
    pass


def call_groq(messages):
    """Call Groq's OpenAI-compatible endpoint, trying the fallback model if the primary fails."""
    if not settings.GROQ_API_KEY:
        raise LLMUnavailable("GROQ_API_KEY is not configured")
    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"}
    last_error = None
    for model in dict.fromkeys([settings.GROQ_MODEL, settings.GROQ_FALLBACK_MODEL]):
        if not model:
            continue
        try:
            response = requests.post(
                settings.GROQ_API_URL,
                headers=headers,
                json={"model": model, "messages": messages, "temperature": 0.4, "max_tokens": 600},
                timeout=25,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
            last_error = exc
            logger.warning("Groq model %s failed: %s", model, exc)
    raise LLMUnavailable(str(last_error))


# --------------------------------------------------------------------------- offline assistant
INTENTS = [
    ("greeting", r"\b(hi|hello|hey|salam)\b|مرحب|السلام|اهلا|أهلا"),
    ("cancel", r"cancel|refund|الغاء|إلغاء|استرداد|استرجاع"),
    ("book", r"\bbook|reserv|how (do|can) i|احجز|حجز"),
    ("contact", r"contact|phone|email|call|whatsapp|تواصل|رقم|ايميل|اتصال|واتس"),
    ("cheap", r"cheap|budget|lowest|afford|رخيص|ارخص|أرخص|سعر|اسعار|أسعار|price"),
    ("thanks", r"thank|thx|شكرا|متشكر"),
]

REPLIES = {
    "en": {
        "greeting": "Hello! 👋 Tell me where you'd like to go, your budget or how many days you have, and I'll suggest tours.",
        "cancel": "Our policy: {policy} Registered users can cancel from **My bookings** (/account/bookings/).",
        "book": "Booking is easy: open a tour, choose a date and number of travelers, then submit. You'll get a reference like **GT-XXXXXX** instantly.",
        "contact": "You can reach us at **{phone}** or **{email}** ({address}). Or use the [contact form](/contact/).",
        "thanks": "You're welcome! Anything else I can help with?",
        "cheap": "Here are our best-value tours right now:",
        "found": "Here's what I found for you:",
        "fallback": "I couldn't find an exact match. Browse [all tours](/tours/) or ask about a destination, budget or trip length.",
    },
    "ar": {
        "greeting": "أهلاً بيك! 👋 قولّي عايز تسافر فين، ميزانيتك قد إيه أو عندك كام يوم، وأنا أرشحلك رحلات.",
        "cancel": "سياسة الإلغاء: {policy} لو عندك حساب تقدر تلغي من **حجوزاتي** (/account/bookings/).",
        "book": "الحجز سهل: افتح صفحة الرحلة، اختار التاريخ وعدد المسافرين واضغط احجز. هيظهرلك رقم حجز زي **GT-XXXXXX** فوراً.",
        "contact": "تقدر تكلمنا على **{phone}** أو **{email}** ({address})، أو من [صفحة التواصل](/contact/).",
        "thanks": "العفو! تحب أساعدك في حاجة تانية؟",
        "cheap": "دي أوفر رحلات عندنا دلوقتي:",
        "found": "دي الرحلات اللي لقيتها ليك:",
        "fallback": "مالقيتش نتيجة مطابقة. تقدر تتصفح [كل الرحلات](/tours/) أو تسألني عن وجهة أو ميزانية أو مدة الرحلة.",
    },
}

STOP_WORDS = {"tour", "tours", "trip", "trips", "want", "looking", "for", "the", "and", "with", "show", "me", "any", "about", "what"}


def _format_tours(tours, currency):
    return "\n".join(
        f"- [**{t.title}**]({t.get_absolute_url()}) - {t.destination.name}, "
        f"{t.duration_days} day{'s' if t.duration_days > 1 else ''}, "
        f"**{currency}{t.current_price:,.0f}**"
        for t in tours
    )


def offline_reply(text):
    site = SiteSettings.load()
    lang = "ar" if ARABIC.search(text) else "en"
    replies = REPLIES[lang]
    lower = text.lower()
    fmt = {"policy": site.cancellation_policy, "phone": site.phone, "email": site.email, "address": site.address}

    intent = next((name for name, pattern in INTENTS if re.search(pattern, lower)), None)
    tours = Tour.objects.active().select_related("destination")

    # Look for destinations/tours mentioned in the message first - that's the most useful answer.
    words = [w for w in re.findall(r"\w{3,}", lower) if w not in STOP_WORDS]
    if words:
        query = Q()
        for word in words:
            query |= (
                Q(title__icontains=word) | Q(destination__name__icontains=word)
                | Q(destination__country__icontains=word) | Q(category__icontains=word)
            )
        matches = list(tours.filter(query).distinct()[:4])
        if matches and intent not in ("cancel", "contact", "thanks"):
            return f"{replies['found']}\n{_format_tours(matches, site.currency_symbol)}", matches

    days = re.search(r"(\d+)\s*(day|days|يوم|ايام|أيام)", lower)
    if days:
        matches = list(tours.filter(duration_days__lte=int(days.group(1))).order_by("-duration_days")[:4])
        if matches:
            return f"{replies['found']}\n{_format_tours(matches, site.currency_symbol)}", matches

    if intent == "cheap":
        matches = sorted(tours, key=lambda t: t.current_price)[:4]
        return f"{replies['cheap']}\n{_format_tours(matches, site.currency_symbol)}", matches
    if intent:
        return replies[intent].format(**fmt), []
    return replies["fallback"], []


def mentioned_tours(reply):
    """Tours whose link or title appears in an LLM reply - rendered as cards in the widget."""
    found = []
    for tour in Tour.objects.active().select_related("destination"):
        if tour.get_absolute_url() in reply or tour.title.lower() in reply.lower():
            found.append(tour)
        if len(found) == 3:
            break
    return found


def generate_reply(conversation, user_text):
    """Return (reply_text, source, tours) for a user message within a conversation."""
    history = list(conversation.messages.order_by("-created_at")[:HISTORY_LIMIT])[::-1]
    messages = [{"role": "system", "content": system_prompt()}]
    messages += [{"role": m.role, "content": m.content} for m in history]
    messages.append({"role": "user", "content": user_text})
    try:
        reply = call_groq(messages)
        return reply, "groq", mentioned_tours(reply)
    except LLMUnavailable:
        reply, tours = offline_reply(user_text)
        return reply, "offline", tours
