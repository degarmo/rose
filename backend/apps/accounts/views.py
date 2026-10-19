from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.db import transaction
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.contact.models import anonymize_messages_from
from apps.core.api import CsrfProtectedAPIView, too_many_requests
from apps.core.ratelimit import is_over_limit
from apps.events.services import release_places_held_by
from apps.feed.services import erase_feed_data
from apps.memberships.account import close_for_deleted_account
from apps.rentals.services import forget_account as forget_rental_contact
from apps.volunteers.models import forget_account as forget_volunteer

from . import lockout, tasks
from .models import User
from .serializers import (
    AccountSerializer,
    ChangePasswordSerializer,
    DeleteAccountSerializer,
    EmailSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    RegisterSerializer,
    SessionUpdateSerializer,
    TokenSerializer,
)
from .tokens import user_from_reset_params, user_from_verification_token

LOGIN_FAILED = "That email and password do not match an account."
LOCKED = "Too many attempts. For your security, please wait 15 minutes and try again."


def session_payload(request):
    user = request.user if request.user.is_authenticated else None
    return {
        "user": AccountSerializer(user).data if user else None,
        "csrfToken": get_token(request),
    }


def after_commit(task, *args):
    transaction.on_commit(lambda: task.delay(*args))


class SessionView(CsrfProtectedAPIView):
    """Who is signed in. Returns `user: null` rather than an error when nobody is."""

    write_limit = "ACCOUNT_WRITE_RATE_LIMIT"

    def get(self, request):
        return Response(session_payload(request))

    def patch(self, request):
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = SessionUpdateSerializer(data=request.data, context={"user": request.user})
        serializer.is_valid(raise_exception=True)
        changes = serializer.validated_data
        for field, value in changes.items():
            setattr(request.user, field, value)
        request.user.save(update_fields=list(changes))
        return Response(session_payload(request))


class RegisterView(CsrfProtectedAPIView):
    def post(self, request):
        email = str(request.data.get("email", ""))
        if is_over_limit(
            request,
            "register",
            [("ip", settings.REGISTER_RATE_LIMIT_IP), (email, settings.REGISTER_RATE_LIMIT_EMAIL)],
        ):
            return too_many_requests()

        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        existing = User.objects.filter(email__iexact=data["email"]).first()
        if existing:
            # Same response as a new sign-up, so nobody can test which emails have accounts.
            after_commit(tasks.send_already_registered_email, existing.pk)
        else:
            user = User.objects.create_user(
                email=data["email"], display_name=data["display_name"], password=data["password"]
            )
            after_commit(tasks.send_verification_email, user.pk)
        return Response(
            {"detail": "Check your email for a link to confirm your address."},
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(CsrfProtectedAPIView):
    write_limit = "TOKEN_RATE_LIMIT"

    def post(self, request):
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = user_from_verification_token(serializer.validated_data["token"])
        if user is None:
            return Response(
                {"detail": "This link has expired or is not valid. Sign in to get a new one."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.mark_email_verified()
        return Response({"detail": "Your email is confirmed."})


class ResendVerificationView(CsrfProtectedAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if is_over_limit(request, "verify-resend", [(f"user:{request.user.pk}", "3/h")]):
            return too_many_requests()
        if not request.user.email_verified:
            after_commit(tasks.send_verification_email, request.user.pk)
        return Response(
            {"detail": "If your email still needs confirming, a new link is on its way."}
        )


class LoginView(CsrfProtectedAPIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        if is_over_limit(
            request,
            "login",
            [("ip", settings.LOGIN_RATE_LIMIT_IP), (email, settings.LOGIN_RATE_LIMIT_EMAIL)],
        ):
            return too_many_requests()
        if lockout.is_locked(email):
            return too_many_requests(LOCKED)

        user = authenticate(request, username=email, password=serializer.validated_data["password"])
        if user is None:
            lockout.register_failure(email)
            if lockout.is_locked(email):
                return too_many_requests(LOCKED)
            return Response({"detail": LOGIN_FAILED}, status=status.HTTP_400_BAD_REQUEST)

        lockout.clear(email)
        login(request, user)
        return Response(session_payload(request))


class LogoutView(CsrfProtectedAPIView):
    def post(self, request):
        logout(request)
        return Response(session_payload(request))


class SignOutEverywhereView(CsrfProtectedAPIView):
    """Ends every session this account has, on every device, including this one."""

    permission_classes = [IsAuthenticated]
    write_limit = "ACCOUNT_WRITE_RATE_LIMIT"

    def post(self, request):
        request.user.sign_out_everywhere()
        logout(request)
        return Response(session_payload(request))


class PasswordResetRequestView(CsrfProtectedAPIView):
    def post(self, request):
        email = str(request.data.get("email", ""))
        if is_over_limit(
            request,
            "password-reset",
            [
                ("ip", settings.PASSWORD_RESET_RATE_LIMIT_IP),
                (email, settings.PASSWORD_RESET_RATE_LIMIT_EMAIL),
            ],
        ):
            return too_many_requests()
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(
            email__iexact=serializer.validated_data["email"], is_active=True
        ).first()
        if user:
            after_commit(tasks.send_password_reset_email, user.pk)
        return Response({"detail": "If that email has an account, a reset link is on its way."})


class PasswordResetConfirmView(CsrfProtectedAPIView):
    write_limit = "TOKEN_RATE_LIMIT"

    def post(self, request):
        user = user_from_reset_params(
            str(request.data.get("uid", "")), str(request.data.get("token", ""))
        )
        if user is None:
            return Response(
                {"detail": "This reset link has expired or was already used. Request a new one."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = PasswordResetConfirmSerializer(data=request.data, context={"user": user})
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        # Following the emailed link proves the address belongs to them.
        user.mark_email_verified()
        lockout.clear(user.email)
        after_commit(tasks.send_password_changed_email, user.pk)
        return Response({"detail": "Your password has been changed. You can sign in now."})


class ChangePasswordView(CsrfProtectedAPIView):
    write_limit = "ACCOUNT_WRITE_RATE_LIMIT"
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"user": request.user})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        update_session_auth_hash(request, request.user)
        after_commit(tasks.send_password_changed_email, request.user.pk)
        return Response(session_payload(request))


class DeleteAccountView(CsrfProtectedAPIView):
    write_limit = "ACCOUNT_WRITE_RATE_LIMIT"
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        serializer = DeleteAccountSerializer(data=request.data, context={"user": user})
        serializer.is_valid(raise_exception=True)
        email = user.email
        with transaction.atomic():
            release_places_held_by(user)
            # The same routine as "Leave and erase", so member files are removed too.
            erase_feed_data(user)
            # Stops online renewals; payment records stay, detached from the person.
            close_for_deleted_account(user)
            anonymize_messages_from(email)
            # Volunteer offers go; rental inquiries keep only type, date and status.
            forget_volunteer(user)
            forget_rental_contact(user)
            # Cascades to the profile and every RSVP.
            user.delete()
        logout(request)
        after_commit(tasks.send_account_deleted_email, email)
        return Response(session_payload(request))
