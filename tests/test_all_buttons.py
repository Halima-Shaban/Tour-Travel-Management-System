import sys
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import SiteSettings, NewsletterSubscriber, ContactMessage
from tours.models import Tour, Destination


class AllButtonsFunctionalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.site = SiteSettings.load()
        cls.customer = User.objects.create_user(
            username="customer_tester",
            email="customertest@example.com",
            password="Password123!",
            first_name="Customer",
        )
        cls.dest = Destination.objects.create(name="Bali", slug="bali", country="Indonesia")
        cls.tour = Tour.objects.create(
            title="Bali Paradise Tour",
            slug="bali-paradise",
            destination=cls.dest,
            duration_days=3,
            price=299,
            max_group_size=10,
            is_active=True,
            is_featured=True,
        )

    def setUp(self):
        self.client = Client()

    def test_01_auth_page_buttons_and_actions(self):
        """Test all interactive buttons and endpoints on the Auth sliding template."""
        # 1. GET /account/login/ renders all required buttons and dynamic triggers
        res = self.client.get(reverse("accounts:login"))
        self.assertEqual(res.status_code, 200)
        content = res.content.decode("utf-8")
        
        # Verify button elements exist
        self.assertIn('id="btnSignIn"', content, "Sign in button should exist")
        self.assertIn('id="btnSignUp"', content, "Sign up button should exist")
        self.assertIn("toggle('sign-in')", content, "Sign in toggle trigger should exist")
        self.assertIn("toggle('sign-up')", content, "Sign up toggle trigger should exist")
        self.assertIn("openForgotPassword", content, "Forgot password modal trigger should exist")
        self.assertIn("togglePassword", content, "Password show/hide toggle should exist")
        self.assertIn("socialAuthNotice", content, "Social login buttons should exist")
        self.assertIn('class="back-home-btn"', content, "Back to home button should exist")
        
        # 2. Test Sign In button action (POST)
        res_login = self.client.post(
            reverse("accounts:login"),
            {"username": "customer_tester", "password": "Password123!"},
        )
        self.assertEqual(res_login.status_code, 302, "Sign in button should successfully authenticate and redirect")

        # 3. Test Sign Up button action (POST as anonymous user)
        self.client.logout()
        res_signup = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "new_btn_user",
                "email": "new_btn@example.com",
                "password1": "ComplexPass123!",
                "password2": "ComplexPass123!",
            },
        )
        self.assertEqual(res_signup.status_code, 302, "Sign up button should register user, log in, and redirect")
        self.assertTrue(User.objects.filter(username="new_btn_user").exists())

        # 4. Test Forgot Password modal submit button
        res_forgot = self.client.post(
            reverse("accounts:forgot_password"),
            {"email": "customertest@example.com"},
        )
        self.assertEqual(res_forgot.status_code, 302, "Forgot password button should process request and redirect")

    def test_02_navbar_navigation_and_buttons(self):
        """Test all buttons and links in the site navigation bar."""
        nav_buttons = [
            ("Home", reverse("core:home")),
            ("Tours", reverse("tours:list")),
            ("Destinations", reverse("tours:destinations")),
            ("Journal", reverse("blog:list")),
            ("About", reverse("core:about")),
            ("Contact", reverse("core:contact")),
            ("Sign in", reverse("accounts:login")),
            ("Sign up", reverse("accounts:signup")),
        ]
        for label, url in nav_buttons:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f"Navbar button '{label}' -> {url} should respond with 200 OK")

    def test_03_home_page_buttons(self):
        """Test home page interactive buttons."""
        res = self.client.get(reverse("core:home"))
        self.assertEqual(res.status_code, 200)

        # 1. Hero Search button
        search_res = self.client.get(reverse("tours:list"), {"q": "Bali"})
        self.assertEqual(search_res.status_code, 200, "Search button should filter tours")
        self.assertContains(search_res, "Bali Paradise Tour")

        # 2. Newsletter Subscribe button
        news_res = self.client.post(reverse("core:newsletter"), {"email": "subscriber99@example.com"})
        self.assertEqual(news_res.status_code, 302, "Subscribe button should post and redirect")
        self.assertTrue(NewsletterSubscriber.objects.filter(email="subscriber99@example.com").exists())

    def test_04_contact_form_button(self):
        """Test contact form 'Send message' button."""
        res = self.client.post(
            reverse("core:contact"),
            {
                "name": "Alex Traveler",
                "email": "alex@example.com",
                "subject": "Booking inquiry",
                "message": "Hello, I would like more details about custom tour dates.",
            },
        )
        self.assertEqual(res.status_code, 302, "Contact form submit button should create message and redirect")
        self.assertTrue(ContactMessage.objects.filter(email="alex@example.com").exists())

    def test_05_authenticated_user_buttons_and_logout(self):
        """Test authenticated user actions: dropdown links, bookings, and Sign out button."""
        self.client.force_login(self.customer)

        # My Bookings button
        res_bookings = self.client.get(reverse("accounts:bookings"))
        self.assertEqual(res_bookings.status_code, 200)

        # Profile button
        res_profile = self.client.get(reverse("accounts:profile"))
        self.assertEqual(res_profile.status_code, 200)

        # Inbox / Messages button
        res_inbox = self.client.get(reverse("accounts:inbox"))
        self.assertEqual(res_inbox.status_code, 200)

        # Sign out button action (POST)
        res_logout = self.client.post(reverse("accounts:logout"))
        self.assertEqual(res_logout.status_code, 302, "Sign out button should log user out and redirect")
