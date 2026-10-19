from django.urls import path

from apps.events.views import MyRSVPListView
from apps.feed.account_views import ExportDownloadView

from . import settings_views, views

urlpatterns = [
    path("session/", views.SessionView.as_view(), name="account-session"),
    path("register/", views.RegisterView.as_view(), name="account-register"),
    path("verify-email/", views.VerifyEmailView.as_view(), name="account-verify-email"),
    path(
        "verify-email/resend/",
        views.ResendVerificationView.as_view(),
        name="account-verify-email-resend",
    ),
    path("login/", views.LoginView.as_view(), name="account-login"),
    path("login/two-step/", views.LoginTwoStepView.as_view(), name="account-login-two-step"),
    path("preferences/", settings_views.PreferencesView.as_view(), name="account-preferences"),
    path("two-step/", settings_views.TwoStepView.as_view(), name="account-two-step"),
    path(
        "two-step/setup/", settings_views.TwoStepSetupView.as_view(), name="account-two-step-setup"
    ),
    path(
        "two-step/confirm/",
        settings_views.TwoStepConfirmView.as_view(),
        name="account-two-step-confirm",
    ),
    path(
        "two-step/disable/",
        settings_views.TwoStepDisableView.as_view(),
        name="account-two-step-disable",
    ),
    path("sessions/", settings_views.SessionsView.as_view(), name="account-sessions"),
    path("export/", settings_views.ExportView.as_view(), name="account-export"),
    path("export/download/", ExportDownloadView.as_view(), name="account-export-download"),
    path("logout/", views.LogoutView.as_view(), name="account-logout"),
    path(
        "sign-out-everywhere/",
        views.SignOutEverywhereView.as_view(),
        name="account-sign-out-everywhere",
    ),
    path("password-reset/", views.PasswordResetRequestView.as_view(), name="account-reset"),
    path(
        "password-reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="account-reset-confirm",
    ),
    path("password/", views.ChangePasswordView.as_view(), name="account-password"),
    path("delete/", views.DeleteAccountView.as_view(), name="account-delete"),
    path("rsvps/", MyRSVPListView.as_view(), name="account-rsvps"),
]
