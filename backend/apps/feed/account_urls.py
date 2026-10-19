from django.urls import path

from . import account_views as views

urlpatterns = [
    path("", views.FeedAccountView.as_view(), name="account-feed"),
    path("join/", views.JoinFeedView.as_view(), name="account-feed-join"),
    path("guidelines/", views.AcceptGuidelinesView.as_view(), name="account-feed-guidelines"),
    path("step-away/", views.StepAwayView.as_view(), name="account-feed-step-away"),
    path("erase/", views.EraseView.as_view(), name="account-feed-erase"),
]
