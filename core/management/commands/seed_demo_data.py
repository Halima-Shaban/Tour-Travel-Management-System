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
from tours.models import Booking, Destination, Review, Tour

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

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(42)
        if options["flush"]:
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
                booking = Booking(
                    tour=tour, user=customer, full_name=customer.get_full_name(), email=customer.email,
                    phone="+20 111 222 3333", travel_date=travel_date, travelers=random.randint(1, 4), status=status,
                    payment_status="paid" if status in ("completed", "confirmed") else ("refunded" if status == "cancelled" and random.random() < .5 else "unpaid"),
                )
                booking.save()
                created_at = timezone.now() + timedelta(days=min(offset, 0) - random.randint(3, 40))
                Booking.objects.filter(pk=booking.pk).update(created_at=created_at)

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
