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
