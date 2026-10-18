from django.urls import path

from . import views

urlpatterns = [
    path("webhook/<str:provider_key>/", views.WebhookView.as_view(), name="payments-webhook"),
    path("sandbox/<str:token>/", views.SandboxCheckoutView.as_view(), name="payments-sandbox"),
]
