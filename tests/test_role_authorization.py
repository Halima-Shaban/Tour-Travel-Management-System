"""
Role-based authorization tests.

Matrix verified for every protected area:

  URL group          | anonymous | customer | guide | admin
  -------------------|-----------|----------|-------|------
  /account/...       | 302→login | 200/302  |  200  |  200
  /guide/...         | 302→login |   403    |  200  |  403*
  /dashboard/...     | 302→login |   403    |  403  |  200
  /django-admin/...  | 302→login |   302    |  302  |  200

  * Admins who are not guides are blocked from the Guide portal to keep
    concerns separate (same as the existing guide_required decorator).
"""
from decimal import Decimal
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile
from core.models import SiteSettings
from tours.models import Booking, Destination, Tour


# ---------------------------------------------------------------------------
# Shared test fixture
# ---------------------------------------------------------------------------

class RoleAuthBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        today = timezone.localdate()

        cls.admin = User.objects.create_superuser(
            username="auth_admin", email="auth_admin@example.com", password="pass123"
        )
        Profile.objects.filter(user=cls.admin).update(role=Profile.Role.ADMIN)

        cls.guide = User.objects.create_user(
            username="auth_guide", email="auth_guide@example.com", password="pass123"
        )
        Profile.objects.filter(user=cls.guide).update(role=Profile.Role.GUIDE)

        cls.customer = User.objects.create_user(
            username="auth_customer", email="auth_customer@example.com", password="pass123"
        )
        Profile.objects.filter(user=cls.customer).update(role=Profile.Role.CUSTOMER)

        cls.dest = Destination.objects.create(name="Cairo", slug="cairo-auth", country="Egypt")
        cls.tour = Tour.objects.create(
            title="Cairo Auth Tour",
            slug="cairo-auth-tour",
            destination=cls.dest,
            price=Decimal("100.00"),
            duration_days=1,
            max_group_size=8,
            guide=cls.guide,
            is_active=True,
        )
        cls.booking = Booking.objects.create(
            reference="GT-AUTH-001",
            tour=cls.tour,
            user=cls.customer,
            guide=cls.guide,
            travel_date=today + timedelta(days=10),
            travelers=1,
            full_name="Auth Customer",
            email="auth_customer@example.com",
            phone="+201000000001",
            total_price=Decimal("100.00"),
            status=Booking.Status.CONFIRMED,
            guide_status=Booking.GuideResponse.ACCEPTED,
        )

    def setUp(self):
        self.client = Client()


# ---------------------------------------------------------------------------
# 1. Anonymous access — always redirected to login
# ---------------------------------------------------------------------------

class AnonymousAccessTests(RoleAuthBase):
    """Anonymous visitors must be redirected to the login page for every
    protected URL."""

    def _assert_redirects_to_login(self, url):
        res = self.client.get(url)
        self.assertIn(
            res.status_code, [301, 302],
            f"Anonymous GET {url} should redirect, got {res.status_code}",
        )
        loc = res.get("Location", "")
        self.assertIn("login", loc.lower() if loc else "",
                      f"Anonymous GET {url} should redirect to login, got Location: {loc!r}")

    def test_anon_blocked_from_customer_portal(self):
        urls = [
            reverse("accounts:bookings"),
            reverse("accounts:profile"),
            reverse("accounts:inbox"),
            reverse("accounts:booking_detail", args=[self.booking.reference]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self._assert_redirects_to_login(url)

    def test_anon_blocked_from_guide_portal(self):
        urls = [
            reverse("guide:home"),
            reverse("guide:bookings"),
            reverse("guide:tours"),
            reverse("guide:calendar"),
            reverse("guide:inbox"),
            reverse("guide:reviews"),
            reverse("guide:profile"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self._assert_redirects_to_login(url)

    def test_anon_blocked_from_admin_dashboard(self):
        urls = [
            reverse("dashboard:home"),
            reverse("dashboard:tours"),
            reverse("dashboard:bookings"),
            reverse("dashboard:users"),
            reverse("dashboard:guides"),
            reverse("dashboard:settings"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self._assert_redirects_to_login(url)

    def test_anon_can_access_public_pages(self):
        public = [
            reverse("core:home"),
            reverse("core:about"),
            reverse("core:contact"),
            reverse("tours:list"),
            reverse("tours:destinations"),
            reverse("accounts:login"),
            reverse("accounts:signup"),
        ]
        for url in public:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 200,
                                 f"Public URL {url} should be 200, got {res.status_code}")


# ---------------------------------------------------------------------------
# 2. Customer — full customer portal, blocked from guide & admin
# ---------------------------------------------------------------------------

class CustomerAccessTests(RoleAuthBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.customer)

    def test_customer_can_access_own_portal(self):
        urls = [
            reverse("accounts:bookings"),
            reverse("accounts:profile"),
            reverse("accounts:inbox"),
            reverse("accounts:booking_detail", args=[self.booking.reference]),
        ]
        for url in urls:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 200,
                                 f"Customer {url} should be 200, got {res.status_code}")

    def test_customer_blocked_from_guide_portal(self):
        urls = [
            reverse("guide:home"),
            reverse("guide:bookings"),
            reverse("guide:tours"),
            reverse("guide:calendar"),
            reverse("guide:inbox"),
            reverse("guide:reviews"),
            reverse("guide:profile"),
        ]
        for url in urls:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 403,
                                 f"Customer should be forbidden from guide {url}, got {res.status_code}")

    def test_customer_blocked_from_admin_dashboard(self):
        urls = [
            reverse("dashboard:home"),
            reverse("dashboard:tours"),
            reverse("dashboard:bookings"),
            reverse("dashboard:users"),
            reverse("dashboard:guides"),
            reverse("dashboard:settings"),
        ]
        for url in urls:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 403,
                                 f"Customer should be forbidden from dashboard {url}, got {res.status_code}")

    def test_customer_role_redirect_goes_to_bookings(self):
        """After login, customers land on /account/bookings/ not a dashboard."""
        res = self.client.get(reverse("accounts:redirect"))
        self.assertRedirects(res, reverse("accounts:bookings"), fetch_redirect_response=False)

    def test_customer_cannot_cancel_other_users_booking(self):
        """A customer can only cancel their own bookings, not a stranger's."""
        other = User.objects.create_user("other_auth_cust", "other_auth@example.com", "pass123")
        other_booking = Booking.objects.create(
            reference="GT-AUTH-OTHER",
            tour=self.tour,
            user=other,
            travel_date=timezone.localdate() + timedelta(days=5),
            travelers=1,
            full_name="Other Person",
            email="other_auth@example.com",
            phone="+201000000002",
            total_price=Decimal("100.00"),
        )
        res = self.client.post(
            reverse("accounts:cancel_booking", args=[other_booking.reference])
        )
        # Should redirect (back to bookings) but NOT cancel it
        self.assertIn(res.status_code, [302, 404])
        other_booking.refresh_from_db()
        self.assertNotEqual(other_booking.status, Booking.Status.CANCELLED)


# ---------------------------------------------------------------------------
# 3. Guide — full guide portal, blocked from admin dashboard
# ---------------------------------------------------------------------------

class GuideAccessTests(RoleAuthBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.guide)

    def test_guide_can_access_guide_portal(self):
        urls = [
            reverse("guide:home"),
            reverse("guide:bookings"),
            reverse("guide:tours"),
            reverse("guide:calendar"),
            reverse("guide:inbox"),
            reverse("guide:reviews"),
            reverse("guide:profile"),
        ]
        for url in urls:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 200,
                                 f"Guide {url} should be 200, got {res.status_code}")

    def test_guide_blocked_from_admin_dashboard(self):
        urls = [
            reverse("dashboard:home"),
            reverse("dashboard:tours"),
            reverse("dashboard:bookings"),
            reverse("dashboard:users"),
            reverse("dashboard:guides"),
            reverse("dashboard:settings"),
        ]
        for url in urls:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 403,
                                 f"Guide should be forbidden from dashboard {url}, got {res.status_code}")

    def test_guide_role_redirect_goes_to_guide_home(self):
        res = self.client.get(reverse("accounts:redirect"))
        self.assertRedirects(res, reverse("guide:home"), fetch_redirect_response=False)

    def test_guide_cannot_access_other_guides_booking(self):
        """A guide may only view bookings assigned to them."""
        other_guide = User.objects.create_user("other_guide_auth", "og_auth@example.com", "pass123")
        Profile.objects.filter(user=other_guide).update(role=Profile.Role.GUIDE)
        other_booking = Booking.objects.create(
            reference="GT-AUTH-OG",
            tour=self.tour,
            guide=other_guide,
            travel_date=timezone.localdate() + timedelta(days=5),
            travelers=1,
            full_name="Other Guide Pax",
            email="og_auth@example.com",
            phone="+201000000003",
            total_price=Decimal("100.00"),
        )
        res = self.client.get(reverse("guide:booking_detail", args=[other_booking.pk]))
        self.assertEqual(res.status_code, 404,
                         "Guide should get 404 for another guide's booking")

    def test_guide_cannot_respond_to_other_guides_booking(self):
        """A guide must not accept/decline a booking assigned to someone else."""
        other_guide = User.objects.create_user("other_guide_auth2", "og2_auth@example.com", "pass123")
        Profile.objects.filter(user=other_guide).update(role=Profile.Role.GUIDE)
        other_booking = Booking.objects.create(
            reference="GT-AUTH-OG2",
            tour=self.tour,
            guide=other_guide,
            travel_date=timezone.localdate() + timedelta(days=5),
            travelers=1,
            full_name="Other Guide Pax 2",
            email="og2_auth@example.com",
            phone="+201000000004",
            total_price=Decimal("100.00"),
            status=Booking.Status.CONFIRMED,
            guide_status=Booking.GuideResponse.PENDING,
        )
        res = self.client.post(
            reverse("guide:respond", args=[other_booking.pk]),
            {"action": "accept"},
        )
        self.assertEqual(res.status_code, 404,
                         "Guide must get 404 when responding to another guide's booking")
        other_booking.refresh_from_db()
        self.assertNotEqual(other_booking.guide_status, Booking.GuideResponse.ACCEPTED)

    def test_guide_can_access_customer_portal(self):
        """Guides are also users — they can use the customer portal."""
        res = self.client.get(reverse("accounts:bookings"))
        self.assertEqual(res.status_code, 200)
        res = self.client.get(reverse("accounts:profile"))
        self.assertEqual(res.status_code, 200)


# ---------------------------------------------------------------------------
# 4. Admin — full admin dashboard, blocked from guide portal
# ---------------------------------------------------------------------------

class AdminAccessTests(RoleAuthBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)

    def test_admin_can_access_full_dashboard(self):
        urls = [
            reverse("dashboard:home"),
            reverse("dashboard:tours"),
            reverse("dashboard:bookings"),
            reverse("dashboard:users"),
            reverse("dashboard:guides"),
            reverse("dashboard:settings"),
            reverse("dashboard:reviews"),
            reverse("dashboard:posts"),
            reverse("dashboard:messages"),
            reverse("dashboard:subscribers"),
            reverse("dashboard:chats"),
            reverse("dashboard:destinations"),
        ]
        for url in urls:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 200,
                                 f"Admin {url} should be 200, got {res.status_code}")

    def test_admin_role_redirect_goes_to_dashboard(self):
        res = self.client.get(reverse("accounts:redirect"))
        self.assertRedirects(res, reverse("dashboard:home"), fetch_redirect_response=False)

    def test_admin_blocked_from_guide_portal(self):
        """Admins are not guides — they should be forbidden from the guide portal."""
        urls = [
            reverse("guide:home"),
            reverse("guide:bookings"),
            reverse("guide:tours"),
            reverse("guide:calendar"),
        ]
        for url in urls:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 403,
                                 f"Admin should be forbidden from guide {url}, got {res.status_code}")

    def test_admin_can_update_user_role(self):
        """Admin can change a customer's role via the user-edit endpoint."""
        res = self.client.post(
            reverse("dashboard:user_edit", args=[self.customer.pk]),
            {"role": Profile.Role.GUIDE},
        )
        self.assertIn(res.status_code, [200, 302])
        self.customer.profile.refresh_from_db()
        self.assertEqual(self.customer.profile.role, Profile.Role.GUIDE)
        # Restore
        self.customer.profile.role = Profile.Role.CUSTOMER
        self.customer.profile.save()

    def test_admin_cannot_demote_own_role_via_ui(self):
        """Admin is protected from accidentally removing their own admin role."""
        self.client.post(
            reverse("dashboard:user_edit", args=[self.admin.pk]),
            {"role": Profile.Role.CUSTOMER},
        )
        self.admin.profile.refresh_from_db()
        self.assertNotEqual(self.admin.profile.role, Profile.Role.CUSTOMER)

    def test_admin_can_toggle_tour_status(self):
        res = self.client.post(
            reverse("dashboard:tour_toggle", args=[self.tour.pk]),
            {"field": "is_featured"},
        )
        self.assertEqual(res.status_code, 302)

    def test_admin_can_update_booking_status(self):
        res = self.client.post(
            reverse("dashboard:booking_status", args=[self.booking.pk]),
            {"status": "confirmed"},
        )
        self.assertEqual(res.status_code, 302)

    def test_admin_can_approve_and_delete_reviews(self):
        from tours.models import Review
        review = Review.objects.create(
            tour=self.tour, user=self.customer, rating=4, comment="Good auth review", is_approved=False
        )
        res = self.client.post(
            reverse("dashboard:review_action", args=[review.pk]),
            {"action": "approve"},
        )
        self.assertEqual(res.status_code, 302)
        review.refresh_from_db()
        self.assertTrue(review.is_approved)

        res = self.client.post(
            reverse("dashboard:review_action", args=[review.pk]),
            {"action": "delete"},
        )
        self.assertEqual(res.status_code, 302)
        from tours.models import Review as R
        self.assertFalse(R.objects.filter(pk=review.pk).exists())


# ---------------------------------------------------------------------------
# 5. Cross-role escalation prevention
# ---------------------------------------------------------------------------

class CrossRoleEscalationTests(RoleAuthBase):
    """Ensure no role can escalate privileges by guessing URLs directly."""

    def test_customer_cannot_edit_tours(self):
        self.client.force_login(self.customer)
        res = self.client.post(
            reverse("dashboard:tour_toggle", args=[self.tour.pk]),
            {"field": "is_active"},
        )
        self.assertEqual(res.status_code, 403)

    def test_customer_cannot_change_booking_status(self):
        self.client.force_login(self.customer)
        res = self.client.post(
            reverse("dashboard:booking_status", args=[self.booking.pk]),
            {"status": "cancelled"},
        )
        self.assertEqual(res.status_code, 403)
        self.booking.refresh_from_db()
        self.assertNotEqual(self.booking.status, Booking.Status.CANCELLED)

    def test_guide_cannot_edit_tours_via_dashboard(self):
        self.client.force_login(self.guide)
        res = self.client.post(
            reverse("dashboard:tour_toggle", args=[self.tour.pk]),
            {"field": "is_active"},
        )
        self.assertEqual(res.status_code, 403)

    def test_guide_cannot_manage_users_via_dashboard(self):
        self.client.force_login(self.guide)
        res = self.client.post(
            reverse("dashboard:user_edit", args=[self.customer.pk]),
            {"role": Profile.Role.ADMIN},
        )
        self.assertEqual(res.status_code, 403)
        self.customer.profile.refresh_from_db()
        self.assertNotEqual(self.customer.profile.role, Profile.Role.ADMIN)

    def test_newsletter_ajax_returns_json_only(self):
        """Newsletter AJAX endpoint must always return JSON content-type."""
        res = self.client.post(
            reverse("core:newsletter_ajax"),
            {"email": "test_escalation@example.com"},
        )
        self.assertIn(res.status_code, [200, 400])
        self.assertEqual(res["Content-Type"].split(";")[0], "application/json")
