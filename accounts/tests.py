from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import EmailOTP

User = get_user_model()


class OTPAuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_signup_creates_inactive_user_and_sends_otp(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "testuser_otp",
                "email": "testuser_otp@example.com",
                "password1": "ComplexPass123!@",
                "password2": "ComplexPass123!@",
            },
            follow=True,
        )
        self.assertRedirects(response, reverse("accounts:verify_signup_otp"))
        user = User.objects.get(username="testuser_otp")
        self.assertFalse(user.is_active)

        otp = EmailOTP.objects.filter(email="testuser_otp@example.com", purpose=EmailOTP.Purpose.SIGNUP).first()
        self.assertIsNotNone(otp)
        self.assertFalse(otp.is_used)
        self.assertEqual(len(otp.code), 6)

    def test_verify_signup_otp_invalid_code(self):
        # Register user
        self.client.post(
            reverse("accounts:signup"),
            {
                "username": "testuser_otp2",
                "email": "testuser_otp2@example.com",
                "password1": "ComplexPass123!@",
                "password2": "ComplexPass123!@",
            },
        )
        # Verify with wrong code
        response = self.client.post(
            reverse("accounts:verify_signup_otp"),
            {"code": "000000"},
            follow=True,
        )
        self.assertContains(response, "Incorrect code")
        user = User.objects.get(username="testuser_otp2")
        self.assertFalse(user.is_active)

    def test_verify_signup_otp_success_activates_user(self):
        # Register user
        self.client.post(
            reverse("accounts:signup"),
            {
                "username": "testuser_otp3",
                "email": "testuser_otp3@example.com",
                "password1": "ComplexPass123!@",
                "password2": "ComplexPass123!@",
            },
        )
        otp = EmailOTP.objects.filter(email="testuser_otp3@example.com", purpose=EmailOTP.Purpose.SIGNUP).first()
        
        response = self.client.post(
            reverse("accounts:verify_signup_otp"),
            {"code": otp.code},
            follow=True,
        )
        user = User.objects.get(username="testuser_otp3")
        self.assertTrue(user.is_active)
        # Check that user is logged in
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_forgot_password_and_reset_password_flow(self):
        # Create active user
        user = User.objects.create_user(
            username="resetuser",
            email="resetuser@example.com",
            password="OldPassword123!@",
        )

        # Submit forgot password
        response = self.client.post(
            reverse("accounts:forgot_password"),
            {"email": "resetuser@example.com"},
            follow=True,
        )
        self.assertRedirects(response, reverse("accounts:reset_password"))

        otp = EmailOTP.objects.filter(email="resetuser@example.com", purpose=EmailOTP.Purpose.RESET_PASSWORD).first()
        self.assertIsNotNone(otp)
        self.assertFalse(otp.is_used)

        # Reset password with correct OTP
        reset_response = self.client.post(
            reverse("accounts:reset_password"),
            {
                "email": "resetuser@example.com",
                "code": otp.code,
                "new_password": "NewSecretPass456!@",
                "confirm_password": "NewSecretPass456!@",
            },
            follow=True,
        )
        self.assertRedirects(reset_response, reverse("accounts:login"))

        # Verify old password fails and new password succeeds
        self.assertFalse(self.client.login(username="resetuser", password="OldPassword123!@"))
        self.assertTrue(self.client.login(username="resetuser", password="NewSecretPass456!@"))
