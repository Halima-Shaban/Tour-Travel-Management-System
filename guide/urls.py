from django.urls import path

from . import views

app_name = "guide"

urlpatterns = [
    path("", views.home, name="home"),
    path("tours/", views.tour_list, name="tours"),
    path("tours/<slug:slug>/", views.tour_detail, name="tour_detail"),
    path("tours/<slug:slug>/manifest/<str:date>/", views.manifest, name="manifest"),
    path("bookings/", views.booking_list, name="bookings"),
    path("bookings/<int:pk>/", views.booking_detail, name="booking_detail"),
    path("bookings/<int:pk>/respond/", views.respond, name="respond"),
    path("schedule/", views.calendar, name="calendar"),
    path("schedule/events/", views.calendar_events, name="calendar_events"),
    path("schedule/time-off/<int:pk>/delete/", views.delete_time_off, name="delete_time_off"),
    path("messages/", views.inbox, name="inbox"),
    path("reviews/", views.reviews, name="reviews"),
    path("profile/", views.profile, name="profile"),
]
