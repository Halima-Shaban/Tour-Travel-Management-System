from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.SignInView.as_view(), name="login"),
    path("signup/", views.signup, name="signup"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("redirect/", views.role_redirect, name="redirect"),
    path("bookings/", views.my_bookings, name="bookings"),
    path("bookings/<str:reference>/", views.booking_detail, name="booking_detail"),
    path("bookings/<str:reference>/cancel/", views.cancel_booking, name="cancel_booking"),
    path("messages/", views.inbox, name="inbox"),
    path("profile/", views.profile, name="profile"),
]
