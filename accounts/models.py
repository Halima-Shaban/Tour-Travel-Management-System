from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        GUIDE = "guide", "Tour guide"
        ADMIN = "admin", "Administrator"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    phone = models.CharField(max_length=30, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True)
    bio = models.TextField(blank=True)
    # Guide-specific fields (ignored for other roles)
    languages = models.CharField(max_length=200, blank=True, help_text="Comma separated, e.g. English, Arabic")
    years_experience = models.PositiveSmallIntegerField(default=0)
    is_available = models.BooleanField(default=True, help_text="Guides: accepting new assignments")

    def __str__(self):
        return f"{self.user} ({self.get_role_display()})"

    @property
    def is_guide(self):
        return self.role == self.Role.GUIDE

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.user.is_superuser

    @property
    def language_list(self):
        return [lang.strip() for lang in self.languages.split(",") if lang.strip()]


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile(sender, instance, created, **kwargs):
    if created:
        role = Profile.Role.ADMIN if instance.is_superuser else Profile.Role.CUSTOMER
        Profile.objects.get_or_create(user=instance, defaults={"role": role})


class EmailOTP(models.Model):
    class Purpose(models.TextChoices):
        SIGNUP = "signup", "Sign Up Verification"
        RESET_PASSWORD = "reset_password", "Password Reset"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="email_otps",
    )
    email = models.EmailField(db_index=True)
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=Purpose.choices, default=Purpose.SIGNUP)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "purpose", "is_used"]),
        ]

    def __str__(self):
        status = "Used" if self.is_used else ("Expired" if self.is_expired else "Active")
        return f"OTP for {self.email} ({self.purpose}) - {status}"

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @classmethod
    def generate_otp(cls, email, purpose, user=None, validity_minutes=10):
        import secrets
        from datetime import timedelta
        from django.utils import timezone

        clean_email = email.strip().lower()
        # Invalidate existing unused OTPs for this email and purpose
        cls.objects.filter(email__iexact=clean_email, purpose=purpose, is_used=False).update(is_used=True)

        # Generate 6-digit code
        code = f"{secrets.randbelow(900000) + 100000}"
        expires_at = timezone.now() + timedelta(minutes=validity_minutes)

        otp = cls.objects.create(
            user=user,
            email=clean_email,
            code=code,
            purpose=purpose,
            expires_at=expires_at,
        )
        return otp

    @classmethod
    def verify_otp(cls, email, code, purpose, max_attempts=5):
        from django.utils import timezone

        clean_email = email.strip().lower()
        clean_code = str(code).strip()

        otp = cls.objects.filter(
            email__iexact=clean_email,
            purpose=purpose,
            is_used=False,
            expires_at__gte=timezone.now(),
        ).first()

        if not otp:
            return False, "Invalid or expired verification code. Please request a new one."

        if otp.attempts >= max_attempts:
            otp.is_used = True
            otp.save(update_fields=["is_used"])
            return False, "Too many failed attempts. Please request a new code."

        if otp.code != clean_code:
            otp.attempts += 1
            otp.save(update_fields=["attempts"])
            remaining = max_attempts - otp.attempts
            return False, f"Incorrect code. {remaining} attempt(s) remaining."

        otp.is_used = True
        otp.save(update_fields=["is_used"])
        return True, otp

