from django.urls import path

from . import views

urlpatterns = [
    path("inquiries/", views.RentalInquiryCreateView.as_view(), name="rental-inquiry"),
]
