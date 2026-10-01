from django.urls import path

from . import views

app_name = "messaging"

urlpatterns = [
    path("<str:reference>/", views.poll, name="poll"),
    path("<str:reference>/send/", views.send, name="send"),
]
