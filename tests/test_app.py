"""End-to-end tests covering public pages, role-based dashboards, booking rules and the chatbot."""
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile
from chatbot.models import Message
from chatbot.services import offline_reply
from core.models import SiteSettings
from tours.models import Booking, Destination, Tour


class BaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("boss", "boss@example.com", "pass12345!")
        cls.guide = User.objects.create_user("omar", "omar@example.com", "pass12345!", first_name="Omar")
        Profile.objects.filter(user=cls.guide).update(role=Profile.Role.GUIDE)
        cls.other_guide = User.objects.create_user("layla", "layla@example.com", "pass12345!")
        Profile.objects.filter(user=cls.other_guide).update(role=Profile.Role.GUIDE)
        cls.customer = User.objects.create_user("sara", "sara@example.com", "pass12345!", first_name="Sara")

        cls.cairo = Destination.objects.create(name="Cairo", country="Egypt", is_featured=True)
        cls.tour = Tour.objects.create(
            title="Pyramids Day Tour", destination=cls.cairo, summary="See the pyramids", description="Full day.",
            price=Decimal("100"), sale_price=Decimal("80"), duration_days=1, max_group_size=4, guide=cls.guide,
            is_featured=True,
        )
        cls.other_tour = Tour.objects.create(
            title="Istanbul Walk", destination=Destination.objects.create(name="Istanbul", country="Turkey"),
            summary="Walk", description="Walk.", price=Decimal("300"), duration_days=3, guide=cls.other_guide,
        )

    def setUp(self):
        cache.clear()

    def future(self, days=10):
        return timezone.localdate() + timedelta(days=days)


class PublicPagesTests(BaseTestCase):
    def test_pages_render(self):
        for name, args in [("core:home", []), ("core:about", []), ("core:contact", []), ("tours:list", []),
                           ("tours:destinations", []), ("tours:destination", ["cairo"]),
                           ("tours:detail", [self.tour.slug]), ("blog:list", []), ("accounts:login", []),
                           ("accounts:signup", [])]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 200)

    def test_tour_filters(self):
        response = self.client.get(reverse("tours:list"), {"q": "istanbul"})
        self.assertContains(response, "Istanbul Walk")
        self.assertNotContains(response, "Pyramids Day Tour")
        response = self.client.get(reverse("tours:list"), {"max_price": 150})
        self.assertContains(response, "Pyramids Day Tour")
        self.assertNotContains(response, "Istanbul Walk")

    def test_contact_form_saves_message(self):
        self.client.post(reverse("core:contact"), {"name": "A", "email": "a@b.co", "subject": "Hi", "message": "Hello"})
        self.assertEqual(self.client.get(reverse("core:home")).status_code, 200)
        from core.models import ContactMessage
        self.assertTrue(ContactMessage.objects.filter(subject="Hi").exists())

    def test_customisation_is_applied(self):
        site = SiteSettings.load()
        site.site_name, site.primary_color = "NileWays", "#123456"
        site.save()
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "NileWays")
        self.assertContains(response, "--brand: #123456")


class BookingTests(BaseTestCase):
    def book(self, travelers=2, date=None):
        return self.client.post(reverse("tours:detail", args=[self.tour.slug]), {
            "book": "1", "full_name": "Sara Ali", "email": "sara@example.com", "phone": "+20 100",
            "travel_date": (date or self.future()).isoformat(), "travelers": travelers,
        })

    def test_booking_uses_sale_price_and_redirects(self):
        response = self.book(travelers=2)
        booking = Booking.objects.get()
        self.assertRedirects(response, reverse("tours:booking_success", args=[booking.reference]))
        self.assertEqual(booking.total_price, Decimal("160"))
        self.assertEqual(booking.status, Booking.Status.PENDING)

    def test_capacity_is_enforced(self):
        self.book(travelers=3)
        response = self.book(travelers=2)
        self.assertEqual(Booking.objects.count(), 1)
        self.assertContains(response, "Only 1 seat(s) left")

    def test_past_dates_rejected(self):
        self.book(date=timezone.localdate() - timedelta(days=1))
        self.assertFalse(Booking.objects.exists())

    def test_customer_can_cancel_own_booking(self):
        self.client.force_login(self.customer)
        self.book()
        booking = Booking.objects.get()
        self.assertEqual(booking.user, self.customer)
        self.client.post(reverse("accounts:cancel_booking", args=[booking.reference]))
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)


class RoleAccessTests(BaseTestCase):
    def test_anonymous_redirected_to_login(self):
        for url in [reverse("dashboard:home"), reverse("guide:home")]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("accounts:login"), response.url)

    def test_customer_forbidden_from_dashboards(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 403)
        self.assertEqual(self.client.get(reverse("dashboard:tours")).status_code, 403)
        self.assertEqual(self.client.get(reverse("guide:home")).status_code, 403)

    def test_guide_cannot_open_admin_dashboard(self):
        self.client.force_login(self.guide)
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 403)

    def test_login_redirects_by_role(self):
        for user, target in [(self.admin, "dashboard:home"), (self.guide, "guide:home"), (self.customer, "accounts:bookings")]:
            self.client.force_login(user)
            self.assertRedirects(self.client.get(reverse("accounts:redirect")), reverse(target), fetch_redirect_response=False)


class AdminDashboardTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)
        Booking.objects.create(tour=self.tour, full_name="X", email="x@x.co", phone="1", travel_date=self.future())

    def test_all_admin_pages_render(self):
        booking = Booking.objects.get()
        names = ["home", "tours", "tour_create", "destinations", "destination_create", "bookings", "guides",
                 "guide_create", "users", "reviews", "messages", "subscribers", "posts", "post_create", "chats",
                 "settings"]
        for name in names:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(f"dashboard:{name}")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:booking_edit", args=[booking.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:tour_edit", args=[self.tour.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:user_edit", args=[self.guide.pk])).status_code, 200)

    def test_quick_status_and_export(self):
        booking = Booking.objects.get()
        self.client.post(reverse("dashboard:booking_status", args=[booking.pk]), {"status": "confirmed"})
        booking.refresh_from_db()
        self.assertEqual(booking.status, "confirmed")
        response = self.client.get(reverse("dashboard:booking_export"))
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn(booking.reference, response.content.decode())

    def test_create_guide_account(self):
        self.client.post(reverse("dashboard:guide_create"), {
            "username": "newguide", "first_name": "New", "last_name": "Guide", "email": "ng@example.com",
            "password1": "Sup3r-secret-pw", "password2": "Sup3r-secret-pw", "years_experience": 3,
        })
        self.assertEqual(User.objects.get(username="newguide").profile.role, Profile.Role.GUIDE)

    def test_protected_tour_not_deleted(self):
        response = self.client.post(reverse("dashboard:tour_delete", args=[self.tour.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Tour.objects.filter(pk=self.tour.pk).exists())

    def test_settings_update(self):
        data = {f: getattr(SiteSettings.load(), f) for f in [
            "site_name", "tagline", "primary_color", "secondary_color", "dark_color", "font_family", "border_radius",
            "hero_title", "hero_subtitle", "hero_image_url", "about_title", "about_text", "email", "phone",
            "address", "footer_text", "currency_symbol", "cancellation_policy", "chatbot_name", "chatbot_welcome"]}
        data.update(site_name="Renamed", primary_color="#ff0000", booking_enabled="on", chatbot_enabled="on")
        response = self.client.post(reverse("dashboard:settings"), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SiteSettings.load().site_name, "Renamed")


class GuideDashboardTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.guide)
        self.mine = Booking.objects.create(tour=self.tour, full_name="Mine", email="m@x.co", phone="1", travel_date=self.future())
        self.theirs = Booking.objects.create(tour=self.other_tour, full_name="Theirs", email="t@x.co", phone="1", travel_date=self.future())

    def test_pages_render(self):
        for name in ["home", "tours", "bookings", "calendar", "reviews", "profile"]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(f"guide:{name}")).status_code, 200)
        self.assertEqual(self.client.get(reverse("guide:tour_detail", args=[self.tour.slug])).status_code, 200)
        manifest = reverse("guide:manifest", args=[self.tour.slug, self.future().isoformat()])
        self.assertContains(self.client.get(manifest), "Mine")

    def test_guide_only_sees_own_bookings(self):
        response = self.client.get(reverse("guide:bookings"))
        self.assertContains(response, "Mine")
        self.assertNotContains(response, "Theirs")
        self.assertEqual(self.client.get(reverse("guide:booking_detail", args=[self.theirs.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("guide:tour_detail", args=[self.other_tour.slug])).status_code, 404)

    def test_guide_confirms_booking_but_cannot_cancel(self):
        url = reverse("guide:booking_detail", args=[self.mine.pk])
        self.client.post(url, {"status": "confirmed", "guide_notes": "Pickup 7am"})
        self.mine.refresh_from_db()
        self.assertEqual((self.mine.status, self.mine.guide_notes), ("confirmed", "Pickup 7am"))
        self.client.post(url, {"status": "cancelled"})
        self.mine.refresh_from_db()
        self.assertEqual(self.mine.status, "confirmed")

    def test_calendar_feed(self):
        events = self.client.get(reverse("guide:calendar_events")).json()
        self.assertEqual(len(events), 1)
        self.assertIn("Pyramids", events[0]["title"])


@override_settings(GROQ_API_KEY="")
class ChatbotTests(BaseTestCase):
    def post(self, text):
        return self.client.post(reverse("chatbot:message"), {"message": text}, content_type="application/json")

    def test_offline_reply_finds_tours(self):
        reply, tours = offline_reply("any tours in Cairo?")
        self.assertIn("Pyramids Day Tour", reply)
        self.assertEqual(tours, [self.tour])

    def test_offline_reply_arabic(self):
        reply, _ = offline_reply("ازاي احجز؟")
        self.assertIn("الحجز", reply)

    def test_endpoint_stores_conversation(self):
        response = self.post("cheapest tours?")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["source"], "offline")
        self.assertTrue(data["tours"])
        self.assertEqual(Message.objects.count(), 2)
        history = self.client.get(reverse("chatbot:history")).json()["messages"]
        self.assertEqual([m["role"] for m in history], ["user", "assistant"])

    def test_empty_message_rejected(self):
        self.assertEqual(self.post("  ").status_code, 400)

    @override_settings(GROQ_API_KEY="test-key")
    def test_groq_is_used_when_configured(self):
        fake = mock.Mock()
        fake.json.return_value = {"choices": [{"message": {"content": "Try [Pyramids Day Tour](/tours/pyramids-day-tour/)"}}]}
        fake.raise_for_status.return_value = None
        with mock.patch("chatbot.services.requests.post", return_value=fake) as post:
            data = self.post("pyramids?").json()
        self.assertEqual(data["source"], "groq")
        self.assertEqual(data["tours"][0]["title"], "Pyramids Day Tour")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertIn("Pyramids Day Tour", payload["messages"][0]["content"])

    @override_settings(GROQ_API_KEY="test-key")
    def test_falls_back_offline_when_groq_fails(self):
        import requests
        with mock.patch("chatbot.services.requests.post", side_effect=requests.ConnectionError):
            data = self.post("tours in Cairo").json()
        self.assertEqual(data["source"], "offline")

    @override_settings(CHATBOT_MAX_MESSAGES_PER_HOUR=2)
    def test_rate_limit(self):
        self.post("hi")
        self.post("hi")
        self.assertEqual(self.post("hi").status_code, 429)

    def test_disabled_chatbot(self):
        site = SiteSettings.load()
        site.chatbot_enabled = False
        site.save()
        self.assertEqual(self.post("hi").status_code, 503)
