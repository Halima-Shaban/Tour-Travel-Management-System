from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("checkout/<str:reference>/", views.checkout, name="checkout"),
    path("success/<str:reference>/", views.success, name="success"),
    path("webhook/", views.webhook, name="webhook"),
]
