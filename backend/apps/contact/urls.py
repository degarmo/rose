from django.urls import path

from . import views

urlpatterns = [
    path("", views.ContactMessageCreateView.as_view(), name="contact-create"),
]
