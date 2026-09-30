from django.urls import path

from . import views

app_name = "tours"

urlpatterns = [
    path("", views.tour_list, name="list"),
    path("destinations/", views.destination_list, name="destinations"),
    path("destinations/<slug:slug>/", views.destination_detail, name="destination"),
    path("booking/<str:reference>/", views.booking_success, name="booking_success"),
    path("<slug:slug>/", views.tour_detail, name="detail"),
    path("<slug:slug>/review/", views.add_review, name="review"),
]
