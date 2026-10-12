from django.contrib import admin

from .models import EmailOTP, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "phone", "is_available"]
    list_filter = ["role", "is_available"]
    search_fields = ["user__username", "user__email"]


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ["email", "purpose", "code", "created_at", "expires_at", "is_used", "attempts"]
    list_filter = ["purpose", "is_used", "created_at"]
    search_fields = ["email", "code", "user__username"]
    readonly_fields = ["created_at", "expires_at"]
