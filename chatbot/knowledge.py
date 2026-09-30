"""Builds the business context the assistant is grounded on (tours, destinations, policies)."""
from django.core.cache import cache
from django.urls import reverse

from core.models import SiteSettings
from tours.models import Destination, Tour

CACHE_KEY = "chatbot.knowledge"


def tour_line(tour, currency):
    price = f"{currency}{tour.current_price:,.0f}"
    if tour.discount_percent:
        price += f" (was {currency}{tour.price:,.0f}, -{tour.discount_percent}%)"
    guide = tour.guide.get_full_name() if tour.guide else "assigned on booking"
    return (
        f"- {tour.title} | {tour.destination.name}, {tour.destination.country} | {tour.get_category_display()} | "
        f"{tour.duration_days} days | {price} per person | max {tour.max_group_size} people | "
        f"difficulty: {tour.get_difficulty_display()} | rating {tour.rating}/5 | guide: {guide} | "
        f"link: {reverse('tours:detail', args=[tour.slug])}\n  {tour.summary}"
    )


def build_knowledge():
    cached = cache.get(CACHE_KEY)
    if cached:
        return cached
    site = SiteSettings.load()
    tours = Tour.objects.active().select_related("destination", "guide").with_rating()[:60]
    destinations = Destination.objects.all()[:40]
    text = "\n".join(
        [
            f"COMPANY: {site.site_name} - {site.tagline}",
            f"CONTACT: email {site.email}, phone {site.phone}, address {site.address}"
            + (f", WhatsApp {site.whatsapp}" if site.whatsapp else ""),
            f"CURRENCY: {site.currency_symbol}",
            f"ONLINE BOOKING: {'enabled' if site.booking_enabled else 'temporarily disabled - ask users to contact us'}",
            f"CANCELLATION POLICY: {site.cancellation_policy}",
            "HOW TO BOOK: open a tour page, pick a date and number of travelers, fill in contact details and submit. "
            "A booking reference (GT-XXXXXX) is shown instantly; registered users can track/cancel bookings at /account/bookings/.",
            "USEFUL PAGES: all tours /tours/, destinations /tours/destinations/, contact /contact/, blog /blog/, sign up /account/signup/.",
            "",
            "DESTINATIONS:",
            *[f"- {d.name}, {d.country}: {d.description[:160]}" for d in destinations],
            "",
            "TOURS (only these exist - never invent others):",
            *[tour_line(t, site.currency_symbol) for t in tours],
        ]
    )
    cache.set(CACHE_KEY, text, 120)
    return text


def system_prompt():
    site = SiteSettings.load()
    prompt = (
        f"You are {site.chatbot_name}, the friendly virtual travel consultant of {site.site_name}.\n"
        "Rules:\n"
        "1. Answer ONLY using the company data below. If something isn't there, say you're not sure and "
        "suggest contacting the team.\n"
        "2. Reply in the same language the user writes in (Arabic, English, ...).\n"
        "3. Be concise: 2-6 short sentences or a short bullet list. Use **bold** for tour names and prices.\n"
        "4. When recommending tours, include the tour link as a markdown link, e.g. [Tour name](/tours/slug/).\n"
        "5. Never collect card/payment details in chat. Never make up prices, dates or availability.\n"
        "6. Stay on topic (travel, tours, bookings, destinations). Politely decline unrelated requests.\n"
    )
    if site.chatbot_instructions:
        prompt += f"\nAdditional instructions from the business:\n{site.chatbot_instructions}\n"
    return prompt + "\n=== COMPANY DATA ===\n" + build_knowledge()
