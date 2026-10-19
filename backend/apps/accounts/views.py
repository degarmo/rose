import functools
import time

from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.db import transaction
from django.middleware.csrf import get_token
from django_otp import login as otp_login
from django_otp.middleware import is_verified as otp_is_verified
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
from apps.safety.models import BlockedEmail
from apps.safety.owner import prepare_owner
from apps.volunteers.models import forget_account as forget_volunteer

from . import lockout, tasks, two_step
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
from .session_tracking import current_hash
from .sessions import start_staff_session
from .tokens import user_from_reset_params, user_from_verification_token

LOGIN_FAILED = "That email and password do not match an account."
PENDING_USER = "login_pending_user"
PENDING_AT = "login_pending_at"
PENDING_SECONDS = 5 * 60
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
        if request.user.is_authenticated and request.user.is_superuser:
            # An owner signed in before their account was prepared gets it now, not next login.
            prepare_owner(request.user)
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
        if BlockedEmail.blocks(data["email"]):
            # Barred after a ban: the same answer as any sign-up, and nothing is created or sent.
            pass
        elif existing:
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
        if two_step.is_enabled(user):
            # The password was right; the authenticator code comes next. Nobody is signed in yet.
            request.session.cycle_key()
            request.session[PENDING_USER] = user.pk
            request.session[PENDING_AT] = time.time()
            return Response({**session_payload(request), "two_step": True})
        login(request, user)
        return Response(session_payload(request))


class LoginTwoStepView(CsrfProtectedAPIView):
    """The second step of logging in, for accounts with an authenticator app."""

    def post(self, request):
        user_id = request.session.get(PENDING_USER)
        started = request.session.get(PENDING_AT, 0)
        user = None
        if user_id and time.time() - started <= PENDING_SECONDS:
            user = User.objects.filter(pk=user_id, is_active=True).first()
        if user is None:
            return Response(
                {"detail": "Your sign-in timed out. Enter your email and password again."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if is_over_limit(request, "login", [("ip", settings.LOGIN_RATE_LIMIT_IP)]):
            return too_many_requests()
        if lockout.is_locked(user.email):
            return too_many_requests(LOCKED)
        device = two_step.verify(user, str(request.data.get("code", "")))
        if device is None:
            lockout.register_failure(user.email)
            if lockout.is_locked(user.email):
                return too_many_requests(LOCKED)
            return Response({"detail": "That code did not work."}, status=400)
        for key in (PENDING_USER, PENDING_AT):
            request.session.pop(key, None)
        lockout.clear(user.email)
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        otp_login(request, device)
        # As django-otp's middleware would on the next request, so this reply says so too.
        user.is_verified = functools.partial(otp_is_verified, user)
        if user.is_staff:
            start_staff_session(request)
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
        before = current_hash(request)
        update_session_auth_hash(request, request.user)
        # Every other session ended with the old password; this one has a new key.
        sessions = request.user.account_sessions
        sessions.exclude(key_hash=before).delete()
        sessions.filter(key_hash=before).update(key_hash=current_hash(request))
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
