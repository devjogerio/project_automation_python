from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("messages/text", views.send_text_view, name="send_text"),
    path("sessions/manage", views.sessions_manage_view, name="sessions_manage"),
]
