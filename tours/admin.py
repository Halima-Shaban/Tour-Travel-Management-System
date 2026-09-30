from django.contrib import admin

from .models import Booking, Destination, Review, Tour


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ["name", "country", "is_featured"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Tour)
class TourAdmin(admin.ModelAdmin):
    list_display = ["title", "destination", "category", "price", "duration_days", "guide", "is_active", "is_featured"]
    list_filter = ["category", "is_active", "is_featured", "destination"]
    search_fields = ["title", "summary"]
    prepopulated_fields = {"slug": ["title"]}


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ["reference", "tour", "full_name", "travel_date", "travelers", "total_price", "status", "payment_status"]
    list_filter = ["status", "payment_status"]
    search_fields = ["reference", "full_name", "email"]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["tour", "user", "rating", "is_approved", "created_at"]
    list_filter = ["is_approved", "rating"]
