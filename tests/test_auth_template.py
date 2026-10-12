from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AuthTemplateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testtraveler",
            email="traveler@example.com",
            password="StrongPassword123!",
            first_name="Alex",
            last_name="Rivers",
        )

    def test_login_page_renders_with_template(self):
        url = reverse("accounts:login")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-initial-mode="sign-in"')
        self.assertContains(response, 'auth.css')
        self.assertContains(response, 'auth.js')
        self.assertContains(response, 'boxicons')
        self.assertContains(response, 'Sign in here')
        self.assertContains(response, 'Sign up here')
        self.assertContains(response, 'Forgot password?')
        self.assertContains(response, 'forgotModal')

    def test_signup_page_renders_with_template(self):
        url = reverse("accounts:signup")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-initial-mode="sign-up"')
        self.assertContains(response, 'Sign in here')
        self.assertContains(response, 'Sign up here')

    def test_successful_login(self):
        url = reverse("accounts:login")
        response = self.client.post(
            url,
            {"username": "testtraveler", "password": "StrongPassword123!"},
        )
        self.assertEqual(response.status_code, 302)

    def test_failed_login_shows_error(self):
        url = reverse("accounts:login")
        response = self.client.post(
            url,
            {"username": "testtraveler", "password": "WrongPassword!"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'auth-alert error')

    def test_successful_signup(self):
        url = reverse("accounts:signup")
        response = self.client.post(
            url,
            {
                "username": "newwanderer",
                "email": "wanderer@example.com",
                "password1": "SecurePass2026!",
                "password2": "SecurePass2026!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="newwanderer").exists())
        new_user = User.objects.get(username="newwanderer")
        self.assertEqual(new_user.email, "wanderer@example.com")
        self.assertEqual(new_user.first_name, "newwanderer")

    def test_signup_password_mismatch_shows_error(self):
        url = reverse("accounts:signup")
        response = self.client.post(
            url,
            {
                "username": "mismatchuser",
                "email": "mismatch@example.com",
                "password1": "SecurePass2026!",
                "password2": "DifferentPass2026!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'auth-alert error')
        self.assertFalse(User.objects.filter(username="mismatchuser").exists())

    def test_signup_duplicate_email_shows_error(self):
        url = reverse("accounts:signup")
        response = self.client.post(
            url,
            {
                "username": "anotheruser",
                "email": "traveler@example.com",
                "password1": "SecurePass2026!",
                "password2": "SecurePass2026!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'An account with this email already exists.')

    def test_forgot_password_submission(self):
        url = reverse("accounts:forgot_password")
        response = self.client.post(url, {"email": "traveler@example.com"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("accounts:reset_password"))
