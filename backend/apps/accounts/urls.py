from django.urls import path

from apps.events.views import MyRSVPListView

from . import views

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
