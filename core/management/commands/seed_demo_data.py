"""Populate the database with realistic demo content: users of every role, tours, bookings, reviews, posts."""
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Profile
from blog.models import Category, Comment, Post
from core.models import ContactMessage, NewsletterSubscriber, SiteSettings
from messaging.models import Message, Thread
from notifications.models import Notification
from tours.models import Booking, Destination, GuideUnavailability, Participant, Review, Tour

DESTINATIONS = [
    ("Cairo", "Egypt", "Pyramids of Giza, the Egyptian Museum and the buzzing lanes of Khan El Khalili."),
    ("Luxor", "Egypt", "The world's greatest open-air museum: Karnak, the Valley of the Kings and sunrise balloons."),
    ("Sharm El Sheikh", "Egypt", "Red Sea reefs, desert canyons and Mount Sinai sunrises."),
    ("Siwa Oasis", "Egypt", "Salt lakes, palm groves and the timeless Great Sand Sea."),
    ("Istanbul", "Turkey", "Where Europe meets Asia - bazaars, mosques and Bosphorus cruises."),
    ("Santorini", "Greece", "Whitewashed villages, volcanic beaches and the Aegean's best sunsets."),
    ("Dubai", "UAE", "Skyscrapers, desert safaris and world-class shopping."),
    ("Marrakech", "Morocco", "Souks, riads and day trips into the Atlas Mountains."),
]

TOURS = [
    ("Pyramids & Sphinx Private Day Tour", "Cairo", "cultural", "easy", 1, 85, None, True),
    ("Classic Egypt: Cairo, Luxor & Aswan", "Cairo", "cultural", "moderate", 8, 1290, 1090, True),
    ("Luxor Hot Air Balloon at Sunrise", "Luxor", "adventure", "easy", 1, 120, None, True),
    ("Nile Cruise Luxor to Aswan", "Luxor", "cruise", "easy", 5, 780, 690, True),
    ("Ras Mohammed Snorkeling Trip", "Sharm El Sheikh", "beach", "easy", 1, 65, None, False),
    ("Mount Sinai Sunrise Trek", "Sharm El Sheikh", "adventure", "challenging", 2, 95, None, True),
    ("Siwa Great Sand Sea Expedition", "Siwa Oasis", "desert", "moderate", 4, 540, None, True),
    ("Istanbul Highlights Walking Tour", "Istanbul", "city", "easy", 3, 390, 349, False),
    ("Cappadocia & Istanbul Explorer", "Istanbul", "adventure", "moderate", 7, 1150, None, True),
    ("Santorini Caldera Sailing", "Santorini", "beach", "easy", 1, 150, None, False),
    ("Greek Islands Hopper", "Santorini", "beach", "easy", 6, 980, 890, True),
    ("Dubai Desert Safari & BBQ", "Dubai", "desert", "easy", 1, 75, None, False),
    ("Dubai City & Abu Dhabi Combo", "Dubai", "city", "easy", 4, 690, None, False),
    ("Atlas Mountains & Berber Villages", "Marrakech", "nature", "moderate", 3, 320, None, True),
    ("Imperial Cities of Morocco", "Marrakech", "cultural", "moderate", 9, 1390, 1240, False),
]

GUIDES = [
    ("guide", "Omar", "Hassan", "English, Arabic, French", 9),
    ("layla", "Layla", "Mahmoud", "English, Arabic, German", 6),
    ("mehmet", "Mehmet", "Yilmaz", "English, Turkish", 11),
    ("sofia", "Sofia", "Papadopoulos", "English, Greek, Italian", 5),
]

CUSTOMERS = [
    ("customer", "Sara", "Ali"), ("john", "John", "Carter"), ("emma", "Emma", "Schmidt"),
    ("ahmed", "Ahmed", "Nabil"), ("lucas", "Lucas", "Martin"), ("mona", "Mona", "Farouk"),
    ("james", "James", "Wilson"), ("nour", "Nour", "Khaled"), ("olivia", "Olivia", "Brown"),
    ("yusuf", "Yusuf", "Demir"),
]

REVIEWS = [
    (5, "Absolutely unforgettable - our guide knew every detail and the logistics were flawless."),
    (5, "Best trip of our lives. Small group, great pace, zero stress."),
    (4, "Great experience overall; one long drive but totally worth it."),
    (5, "Professional, punctual and genuinely friendly. Highly recommended!"),
    (4, "Beautiful itinerary and comfortable hotels. Would book again."),
    (3, "Good tour, though lunch could have been better."),
]

POSTS = [
    ("10 things to know before visiting Egypt", "Travel tips"),
    ("How to choose the right Nile cruise", "Guides"),
    ("A perfect 3 days in Istanbul", "Itineraries"),
    ("Packing list for a desert safari", "Travel tips"),
    ("Why small-group tours are worth it", "Guides"),
    ("Santorini on a budget", "Itineraries"),
]


class Command(BaseCommand):
    help = "Create demo users, tours, bookings, reviews and blog posts (safe to re-run)."

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="Delete existing demo content first.")

    def user(self, username, first, last, password, role, **profile):
        user, created = User.objects.get_or_create(
            username=username, defaults={"first_name": first, "last_name": last, "email": f"{username}@gotrip.test"}
        )
        if created:
            user.set_password(password)
            user.save()
        Profile.objects.filter(user=user).update(role=role, **profile)
        return user

    def seed_collaboration(self, guides, admin):
        """Participants, chats, a declined request, time off and a few notifications."""
        today = timezone.localdate()
        upcoming = list(Booking.objects.filter(travel_date__gte=today).exclude(status="cancelled").select_related("tour", "user", "guide"))
        names = ["Sara Ali", "Omar Ali", "Lina Ali", "John Carter", "Emma Schmidt", "Lucas Martin", "Mona Farouk", "Yusuf Demir"]
        for booking in upcoming[:12]:
            if not booking.participants.exists():
                for i in range(booking.travelers):
                    Participant.objects.create(booking=booking, full_name=names[(booking.pk + i) % len(names)],
                                               age=random.randint(8, 70), nationality=random.choice(["Egypt", "UK", "Germany", "USA"]),
                                               notes=random.choice(["", "", "Vegetarian", "Nut allergy"]))
        if not Message.objects.exists():
            for booking in upcoming[:5]:
                if booking.user and booking.guide:
                    thread, _ = Thread.objects.get_or_create(booking=booking)
                    Message.objects.create(thread=thread, sender=booking.user, body="Hi! Where exactly do we meet on the first day?")
                    Message.objects.create(thread=thread, sender=booking.guide, body="Hello! I'll pick you up from your hotel lobby at 7:30am. Please share the hotel name.")
                    Message.objects.create(thread=thread, sender=booking.user, body="Perfect, we're at the Nile View Hotel. Thank you!")
        declined = next((b for b in upcoming if b.guide_status == "pending" and b.guide), None)
        if declined and not Booking.objects.filter(guide_status="declined").exists():
            Booking.objects.filter(pk=declined.pk).update(guide_status="declined", guide_decline_reason="Already guiding a private group that week")
        if not GuideUnavailability.objects.exists():
            GuideUnavailability.objects.create(guide=guides[0], start_date=today + timedelta(days=40), end_date=today + timedelta(days=44), reason="Family wedding")
        if not Notification.objects.exists():
            for g in guides:
                n = Booking.objects.filter(guide=g, guide_status="pending", travel_date__gte=today).count()
                if n:
                    Notification.objects.create(recipient=g, kind="guide", title=f"You have {n} trip request(s) to answer", url="/guide/bookings/")
            Notification.objects.create(recipient=admin, kind="guide", title="A guide declined a trip - reassign it", url="/dashboard/bookings/?guide=needs")

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(42)
        if options["flush"]:
            Notification.objects.all().delete()
            GuideUnavailability.objects.all().delete()
            Booking.objects.all().delete()
            Review.objects.all().delete()
            Tour.objects.all().delete()
            Destination.objects.all().delete()
            Post.objects.all().delete()

        SiteSettings.load()

        admin, created = User.objects.get_or_create(
            username="admin", defaults={"email": "admin@gotrip.test", "first_name": "Site", "last_name": "Admin"}
        )
        if created:
            admin.set_password("admin12345")
        admin.is_staff = admin.is_superuser = True
        admin.save()
        Profile.objects.filter(user=admin).update(role=Profile.Role.ADMIN)

        guides = [
            self.user(u, f, l, "guide12345", Profile.Role.GUIDE, languages=langs, years_experience=years,
                      phone="+20 100 555 0101", bio=f"Licensed guide with {years} years of experience. Loves history, food and good stories.")
            for u, f, l, langs, years in GUIDES
        ]
        guide_for_country = {"Egypt": guides[:2], "Turkey": [guides[2]], "Greece": [guides[3]], "UAE": [guides[1]], "Morocco": [guides[0]]}
        customers = [self.user(u, f, l, "customer12345", Profile.Role.CUSTOMER) for u, f, l in CUSTOMERS]

        destinations = {}
        for i, (name, country, desc) in enumerate(DESTINATIONS):
            destinations[name], _ = Destination.objects.get_or_create(
                name=name, defaults={"country": country, "description": desc, "is_featured": i < 6}
            )

        tours = []
        for i, (title, dest, cat, diff, days, price, sale, featured) in enumerate(TOURS):
            destination = destinations[dest]
            tour, _ = Tour.objects.get_or_create(
                title=title,
                defaults={
                    "destination": destination,
                    "category": cat,
                    "difficulty": diff,
                    "duration_days": days,
                    "price": Decimal(price),
                    "sale_price": Decimal(sale) if sale else None,
                    "max_group_size": random.choice([8, 12, 16, 20]),
                    "is_featured": featured,
                    "guide": random.choice(guide_for_country[destination.country]),
                    "summary": f"{days}-day {cat} experience in {destination.name} with a certified local guide.",
                    "description": (
                        f"{destination.description} This {days}-day journey is designed for travelers who want "
                        "depth without the hassle: hand-picked stays, skip-the-line entries and plenty of free time. "
                        "Groups are kept small so your guide can tailor the day to your interests."
                    ),
                    "highlights": "Certified English-speaking guide\nSkip-the-line entry tickets\nSmall group, max comfort\nFree cancellation up to 7 days",
                    "itinerary": "\n".join(
                        [f"Day {d}: " + ("Arrival, welcome briefing and dinner" if d == 1 else
                                         "Departure after breakfast" if d == days and days > 1 else
                                         f"Guided exploration of {destination.name}") for d in range(1, days + 1)]
                    ),
                    "included": "Hotel pickup & drop-off\nProfessional guide\nEntrance fees\nBottled water"
                    + ("\nAccommodation\nDaily breakfast" if days > 1 else ""),
                },
            )
            tours.append(tour)

        if not Booking.objects.exists():
            today = timezone.localdate()
            for _ in range(140):
                tour = random.choice(tours)
                customer = random.choice(customers)
                offset = random.randint(-330, 75)
                travel_date = today + timedelta(days=offset)
                if offset < 0:
                    status = random.choice(["completed"] * 8 + ["cancelled"])
                else:
                    status = random.choice(["confirmed", "confirmed", "pending", "pending", "cancelled"])
                paid = status in ("completed", "confirmed")
                booking = Booking(
                    tour=tour, user=customer, full_name=customer.get_full_name(), email=customer.email,
                    phone="+20 111 222 3333", travel_date=travel_date, travelers=random.randint(1, 4), status=status,
                    payment_status="paid" if paid else ("refunded" if status == "cancelled" and random.random() < .5 else "unpaid"),
                    guide_status="accepted" if paid else "pending",
                )
                booking.save()
                if paid:
                    Booking.objects.filter(pk=booking.pk).update(amount_paid=booking.total_price, paid_at=timezone.now())
                created_at = timezone.now() + timedelta(days=min(offset, 0) - random.randint(3, 40))
                Booking.objects.filter(pk=booking.pk).update(created_at=created_at)

        self.seed_collaboration(guides, admin)

        for booking in Booking.objects.filter(status="completed").select_related("tour", "user")[:45]:
            rating, comment = random.choice(REVIEWS)
            Review.objects.get_or_create(tour=booking.tour, user=booking.user, defaults={"rating": rating, "comment": comment})

        for title, cat in POSTS:
            category, _ = Category.objects.get_or_create(name=cat)
            post, created = Post.objects.get_or_create(
                title=title,
                defaults={
                    "author": random.choice([admin, *guides]),
                    "category": category,
                    "excerpt": "Practical advice from our guides to help you plan a smoother, richer trip.",
                    "body": "\n\n".join([
                        "Planning a trip is half the fun - but only when you know what to expect. Our guides "
                        "have put together what they wish every traveler knew before arriving.",
                        "Start with timing. Shoulder seasons bring pleasant weather, thinner crowds and better prices. "
                        "Book popular experiences early, and keep one flexible day for the unexpected.",
                        "Finally, travel light and travel curious. Talk to locals, try the street food and let your guide "
                        "take you off the beaten path. That's where the best memories are made.",
                    ]),
                },
            )
            if created:
                Comment.objects.create(post=post, name="Hana", email="hana@example.com", body="Super helpful, thank you!")

        if not ContactMessage.objects.exists():
            ContactMessage.objects.create(name="Mark Evans", email="mark@example.com", subject="Private group of 12",
                                          message="Hi, can you arrange a private Classic Egypt tour for 12 people in March?")
            ContactMessage.objects.create(name="Aya Samir", email="aya@example.com", subject="Honeymoon package",
                                          message="Looking for a romantic 7-day trip - Santorini or Nile cruise?", is_read=True)
        for email in ["deals@example.com", "traveler@example.com", "wander@example.com"]:
            NewsletterSubscriber.objects.get_or_create(email=email)

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write("  Admin     -> admin / admin12345        (/dashboard/)")
        self.stdout.write("  Guide     -> guide / guide12345        (/guide/)")
        self.stdout.write("  Customer  -> customer / customer12345  (/account/bookings/)")
        self.stdout.write(self.style.WARNING("  Change these passwords before deploying!"))
