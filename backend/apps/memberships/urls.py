from django.urls import path

from . import views

urlpatterns = [
    path("tiers/", views.TiersView.as_view(), name="membership-tiers"),
    path("options/", views.OptionsView.as_view(), name="membership-options"),
    path("me/", views.MyMembershipView.as_view(), name="membership-me"),
    path("join/", views.JoinView.as_view(), name="membership-join"),
    path("checkout/", views.CheckoutView.as_view(), name="membership-checkout"),
    path("cancel/", views.CancelView.as_view(), name="membership-cancel"),
    path("auto-renew/", views.AutoRenewView.as_view(), name="membership-auto-renew"),
    path("receipts/<int:payment_id>/", views.ReceiptView.as_view(), name="membership-receipt"),
]
