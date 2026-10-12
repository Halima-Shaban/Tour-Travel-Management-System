"""Comprehensive route coverage test suite.
Verifies all application endpoints function without errors across different user roles.
"""
from datetime import timedelta
from decimal import Decimal
import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile
from blog.models import Category, Post
from core.models import ContactMessage, NewsletterSubscriber, SiteSettings
from messaging.models import Message as ChatMessage, Thread
from notifications.models import Notification
from tours.models import Booking, Destination, GuideUnavailability, Participant, Review, Tour


class RouteCoverageTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.today = timezone.localdate()
        SiteSettings.load()

        # Users & profiles
        cls.admin = User.objects.create_superuser("admin_user", "admin@example.com", "pass123")
        Profile.objects.filter(user=cls.admin).update(role=Profile.Role.ADMIN)

        cls.guide_user = User.objects.create_user("guide_user", "guide@example.com", "pass123", first_name="Ali")
        Profile.objects.filter(user=cls.guide_user).update(
            role=Profile.Role.GUIDE,
            languages="English, Arabic",
            years_experience=5,
        )

        cls.customer = User.objects.create_user("customer_user", "customer@example.com", "pass123", first_name="Sara")
        Profile.objects.filter(user=cls.customer).update(role=Profile.Role.CUSTOMER)

        # Destinations & Tours
        cls.dest = Destination.objects.create(
            name="Aswan",
            country="Egypt",
            slug="aswan",
            description="Philae and Nile views.",
            is_featured=True,
        )
        cls.tour = Tour.objects.create(
            title="Aswan Highlights",
            slug="aswan-highlights",
            destination=cls.dest,
            summary="A scenic day along the Nile",
            description="Detailed tour itinerary in Aswan.",
            price=Decimal("150.00"),
            sale_price=Decimal("120.00"),
            duration_days=1,
            max_group_size=6,
            guide=cls.guide_user,
            is_featured=True,
            is_active=True,
        )

        # Blog
        cls.blog_cat = Category.objects.create(name="Guides", slug="guides")
        cls.post = Post.objects.create(
            title="Guide to Aswan",
            slug="guide-to-aswan",
            category=cls.blog_cat,
            author=cls.admin,
            excerpt="Everything about Aswan.",
            body="Full post content.",
            is_published=True,
        )

        # Booking
        cls.booking = Booking.objects.create(
            reference="GT-COVERAGE-01",
            tour=cls.tour,
            user=cls.customer,
            guide=cls.guide_user,
            travel_date=cls.today + timedelta(days=14),
            travelers=2,
            full_name="Sara Ali",
            email="customer@example.com",
            phone="+201000000000",
            total_price=Decimal("240.00"),
            status=Booking.Status.CONFIRMED,
            guide_status="accepted",
        )
        cls.participant = Participant.objects.create(
            booking=cls.booking,
            full_name="Sara Ali",
            age=30,
            nationality="Egypt",
        )

        # Review
        cls.review = Review.objects.create(
            tour=cls.tour,
            user=cls.customer,
            rating=5,
            comment="Outstanding experience!",
            is_approved=True,
        )

        # Contact & Newsletter
        cls.contact_msg = ContactMessage.objects.create(
            name="Guest User",
            email="guest@example.com",
            subject="Question",
            message="What is included?",
        )
        cls.subscriber = NewsletterSubscriber.objects.create(email="subscriber@example.com")

        # Messaging Thread
        cls.thread = Thread.objects.create(booking=cls.booking)
        cls.chat_msg = ChatMessage.objects.create(
            thread=cls.thread,
            sender=cls.customer,
            body="Looking forward to the tour!",
        )

        # Notification
        cls.notif = Notification.objects.create(
            recipient=cls.customer,
            kind="booking",
            title="Booking confirmed",
            url=f"/account/bookings/{cls.booking.reference}/",
        )

        # Guide unavailability
        cls.time_off = GuideUnavailability.objects.create(
            guide=cls.guide_user,
            start_date=cls.today + timedelta(days=30),
            end_date=cls.today + timedelta(days=35),
            reason="Vacation",
        )

    def test_all_public_routes(self):
        routes = [
            ("core:home", []),
            ("core:about", []),
            ("core:contact", []),
            ("tours:list", []),
            ("tours:destinations", []),
            ("tours:destination", [self.dest.slug]),
            ("tours:detail", [self.tour.slug]),
            ("blog:list", []),
            ("blog:detail", [self.post.slug]),
            ("accounts:login", []),
            ("accounts:signup", []),
        ]
        for name, args in routes:
            with self.subTest(route=name):
                url = reverse(name, args=args)
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 200, f"Route {name} ({url}) failed with {resp.status_code}")

    def test_newsletter_submission(self):
        resp = self.client.post(reverse("core:newsletter"), {"email": "newbie@example.com"})
        self.assertEqual(resp.status_code, 302)

    def test_customer_portal_routes(self):
        self.client.force_login(self.customer)
        routes = [
            ("accounts:bookings", []),
            ("accounts:booking_detail", [self.booking.reference]),
            ("tours:booking_success", [self.booking.reference]),
            ("accounts:inbox", []),
            ("accounts:profile", []),
            ("notifications:list", []),
        ]
        for name, args in routes:
            with self.subTest(route=name):
                url = reverse(name, args=args)
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 200, f"Route {name} ({url}) failed with {resp.status_code}")

        # Notification read all (POST)
        resp = self.client.post(reverse("notifications:read_all"))
        self.assertEqual(resp.status_code, 302)

        # Notification open (GET redirect)
        resp = self.client.get(reverse("notifications:open", args=[self.notif.pk]))
        self.assertEqual(resp.status_code, 302)

        # Messaging poll
        resp = self.client.get(reverse("messaging:poll", args=[self.booking.reference]))
        self.assertEqual(resp.status_code, 200)

        # Messaging send
        resp = self.client.post(
            reverse("messaging:send", args=[self.booking.reference]),
            data=json.dumps({"body": "Can't wait!"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_chatbot_routes(self):
        self.client.force_login(self.customer)
        # History
        resp = self.client.get(reverse("chatbot:history"))
        self.assertEqual(resp.status_code, 200)

        # Reset
        resp = self.client.post(reverse("chatbot:reset"))
        self.assertEqual(resp.status_code, 200)

        # Message
        resp = self.client.post(
            reverse("chatbot:message"),
            data={"message": "What tours are available?"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_guide_portal_routes(self):
        self.client.force_login(self.guide_user)
        routes = [
            ("guide:home", []),
            ("guide:tours", []),
            ("guide:tour_detail", [self.tour.slug]),
            ("guide:manifest", [self.tour.slug, str(self.booking.travel_date)]),
            ("guide:bookings", []),
            ("guide:booking_detail", [self.booking.pk]),
            ("guide:calendar", []),
            ("guide:calendar_events", []),
            ("guide:inbox", []),
            ("guide:reviews", []),
            ("guide:profile", []),
        ]
        for name, args in routes:
            with self.subTest(route=name):
                url = reverse(name, args=args)
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 200, f"Guide route {name} ({url}) failed with {resp.status_code}")

    def test_admin_dashboard_routes(self):
        self.client.force_login(self.admin)
        routes = [
            ("dashboard:home", []),
            ("dashboard:tours", []),
            ("dashboard:tour_create", []),
            ("dashboard:tour_edit", [self.tour.pk]),
            ("dashboard:tour_delete", [self.tour.pk]),
            ("dashboard:destinations", []),
            ("dashboard:destination_create", []),
            ("dashboard:destination_edit", [self.dest.pk]),
            ("dashboard:destination_delete", [self.dest.pk]),
            ("dashboard:bookings", []),
            ("dashboard:booking_export", []),
            ("dashboard:booking_edit", [self.booking.pk]),
            ("dashboard:conversations", []),
            ("dashboard:guides", []),
            ("dashboard:guide_create", []),
            ("dashboard:users", []),
            ("dashboard:user_edit", [self.customer.pk]),
            ("dashboard:reviews", []),
            ("dashboard:messages", []),
            ("dashboard:message_detail", [self.contact_msg.pk]),
            ("dashboard:subscribers", []),
            ("dashboard:posts", []),
            ("dashboard:post_create", []),
            ("dashboard:post_edit", [self.post.pk]),
            ("dashboard:post_delete", [self.post.pk]),
            ("dashboard:chats", []),
            ("dashboard:settings", []),
            ("admin:index", []),
        ]
        for name, args in routes:
            with self.subTest(route=name):
                url = reverse(name, args=args)
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 200, f"Dashboard route {name} ({url}) failed with {resp.status_code}")

    def test_dashboard_toggle_actions(self):
        self.client.force_login(self.admin)
        # Toggle tour active state
        resp = self.client.post(reverse("dashboard:tour_toggle", args=[self.tour.pk]))
        self.assertEqual(resp.status_code, 302)

        # Quick booking status update
        resp = self.client.post(reverse("dashboard:booking_status", args=[self.booking.pk]), {"status": "completed"})
        self.assertEqual(resp.status_code, 302)

        # Review action approve
        resp = self.client.post(reverse("dashboard:review_action", args=[self.review.pk]), {"action": "approve"})
        self.assertEqual(resp.status_code, 302)
