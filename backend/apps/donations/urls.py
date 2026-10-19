from django.urls import path

from . import views

urlpatterns = [
    path("options/", views.DonationOptionsView.as_view(), name="donation-options"),
    path("checkout/", views.DonationCheckoutView.as_view(), name="donation-checkout"),
]
