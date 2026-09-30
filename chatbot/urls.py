from django.urls import path

from . import views

app_name = "chatbot"

urlpatterns = [
    path("message/", views.send_message, name="message"),
    path("history/", views.history, name="history"),
    path("reset/", views.reset, name="reset"),
]
