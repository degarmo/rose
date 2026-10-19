from django.urls import path

from . import views

urlpatterns = [
    path("subscribe/", views.SubscribeView.as_view(), name="newsletter-subscribe"),
    path("confirm/", views.ConfirmView.as_view(), name="newsletter-confirm"),
    path("unsubscribe/", views.UnsubscribeView.as_view(), name="newsletter-unsubscribe"),
    path(
        "unsubscribe/<str:token>/",
        views.OneClickUnsubscribeView.as_view(),
        name="newsletter-one-click",
    ),
]
