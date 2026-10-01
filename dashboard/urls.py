from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    # Tours & destinations
    path("tours/", views.tour_list, name="tours"),
    path("tours/new/", views.TourCreate.as_view(), name="tour_create"),
    path("tours/<int:pk>/edit/", views.TourUpdate.as_view(), name="tour_edit"),
    path("tours/<int:pk>/delete/", views.TourDelete.as_view(), name="tour_delete"),
    path("tours/<int:pk>/toggle/", views.tour_toggle, name="tour_toggle"),
    path("destinations/", views.destination_list, name="destinations"),
    path("destinations/new/", views.DestinationCreate.as_view(), name="destination_create"),
    path("destinations/<int:pk>/edit/", views.DestinationUpdate.as_view(), name="destination_edit"),
    path("destinations/<int:pk>/delete/", views.DestinationDelete.as_view(), name="destination_delete"),
    # Bookings
    path("bookings/", views.booking_list, name="bookings"),
    path("bookings/export/", views.booking_export, name="booking_export"),
    path("bookings/<int:pk>/", views.BookingUpdate.as_view(), name="booking_edit"),
    path("bookings/<int:pk>/status/", views.booking_quick_status, name="booking_status"),
    path("bookings/<int:pk>/action/", views.booking_action, name="booking_action"),
    path("conversations/", views.conversation_list, name="conversations"),
    # People
    path("guides/", views.guide_list, name="guides"),
    path("guides/new/", views.GuideCreate.as_view(), name="guide_create"),
    path("users/", views.user_list, name="users"),
    path("users/<int:pk>/", views.user_edit, name="user_edit"),
    # Content & communication
    path("reviews/", views.review_list, name="reviews"),
    path("reviews/<int:pk>/", views.review_action, name="review_action"),
    path("messages/", views.message_list, name="messages"),
    path("messages/<int:pk>/", views.message_detail, name="message_detail"),
    path("subscribers/", views.subscriber_list, name="subscribers"),
    path("posts/", views.post_list, name="posts"),
    path("posts/new/", views.PostCreate.as_view(), name="post_create"),
    path("posts/<int:pk>/edit/", views.PostUpdate.as_view(), name="post_edit"),
    path("posts/<int:pk>/delete/", views.PostDelete.as_view(), name="post_delete"),
    path("chats/", views.chat_list, name="chats"),
    path("chats/<int:pk>/", views.chat_detail, name="chat_detail"),
    # Customisation
    path("settings/", views.SettingsView.as_view(), name="settings"),
]
