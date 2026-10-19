"""Settings in the member app that belong to the account rather than the feed: the
preferences (pronouns, calendar files, notifications), two-step login and where you
are signed in. Every endpoint answers only for the signed-in person's own account."""

from django.contrib.auth import authenticate
from django.utils import timezone
from django_otp import login as otp_login
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.admin_auth import _otpauth_url, qr_data_uri
from apps.core.api import CsrfProtectedAPIView
from apps.core.models import AuditLog, audit

from . import two_step
from .session_tracking import current_hash, live_sessions

PREFERENCE_FIELDS = (
    "pronouns",
    "calendar_details",
    "email_event_reminders",
    "email_membership_reminders",
    "notify_likes",
    "notify_comments",
)


class PreferencesSerializer(serializers.Serializer):
    """Your own preferences. Discreet email subjects are not a preference: always on."""

    self_only = True
    pronouns = serializers.CharField(max_length=40, allow_blank=True, required=False)
    calendar_details = serializers.BooleanField(required=False)
    email_event_reminders = serializers.BooleanField(required=False)
    email_membership_reminders = serializers.BooleanField(required=False)
    notify_likes = serializers.BooleanField(required=False)
    notify_comments = serializers.BooleanField(required=False)


def preferences_payload(user):
    profile = user.profile
    return {
        **{field: getattr(profile, field) for field in PREFERENCE_FIELDS},
        "discreet_subjects": True,
    }


class PreferencesView(CsrfProtectedAPIView):
    permission_classes = [IsAuthenticated]
    write_limit = "ACCOUNT_WRITE_RATE_LIMIT"

    def get(self, request):
        return Response(preferences_payload(request.user))

    def patch(self, request):
        serializer = PreferencesSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile = request.user.profile
        changed = []
        for field, value in serializer.validated_data.items():
            if field == "pronouns":
                value = " ".join(value.split())
            setattr(profile, field, value)
            changed.append(field)
        if changed:
            profile.save(update_fields=[*changed, "updated_at"])
        return Response(preferences_payload(request.user))


# Two-step login


def two_step_payload(user):
    return {
        "enabled": two_step.is_enabled(user),
        "backup_codes_left": two_step.backup_codes_left(user),
        # Staff must keep it: the admin and the staff section need it.
        "required": user.is_staff,
    }


class TwoStepView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(two_step_payload(request.user))


class TwoStepSetupView(CsrfProtectedAPIView):
    """Start setting up an authenticator: a new secret, shown as a code to scan."""

    permission_classes = [IsAuthenticated]
    write_limit = "ACCOUNT_WRITE_RATE_LIMIT"

    def post(self, request):
        user = request.user
        if two_step.is_enabled(user):
            return Response({"detail": "Two-step login is already on."}, status=400)
        TOTPDevice.objects.filter(user=user, confirmed=False).delete()
        device = TOTPDevice.objects.create(user=user, name="Authenticator app", confirmed=False)
        url, secret = _otpauth_url(device, user)
        return Response(
            {
                "qr": qr_data_uri(url),
                "secret": " ".join(secret[i : i + 4] for i in range(0, len(secret), 4)),
            }
        )


class TwoStepConfirmView(CsrfProtectedAPIView):
    """Finish setting up: the first code proves the app works. Backup codes are shown once."""

    permission_classes = [IsAuthenticated]
    write_limit = "ACCOUNT_WRITE_RATE_LIMIT"

    def post(self, request):
        user = request.user
        device = TOTPDevice.objects.filter(user=user, confirmed=False).first()
        if device is None:
            return Response({"detail": "Start the setup again."}, status=400)
        if not device.verify_token(two_step.clean(request.data.get("code", ""))):
            return Response(
                {"detail": "That code did not work. Try the newest code in the app."},
                status=400,
            )
        device.confirmed = True
        device.save(update_fields=["confirmed"])
        codes = two_step.new_backup_codes(user)
        otp_login(request, device)
        audit(
            AuditLog.Category.SECURITY,
            "two_factor_enrolled",
            user,
            f"Account ({user.display_name})",
            "user",
            target_user=user,
        )
        return Response({**two_step_payload(user), "backup_codes": codes})


class TwoStepDisableView(CsrfProtectedAPIView):
    permission_classes = [IsAuthenticated]
    write_limit = "ACCOUNT_WRITE_RATE_LIMIT"

    def post(self, request):
        user = request.user
        if user.is_staff:
            return Response(
                {"detail": "Staff accounts keep their two-step login."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        password = str(request.data.get("password", ""))
        if authenticate(request, username=user.email, password=password) is None:
            return Response({"detail": "That password is not right."}, status=400)
        two_step.remove(user)
        audit(
            AuditLog.Category.SECURITY,
            "two_factor_removed",
            user,
            f"Account ({user.display_name})",
            "user",
            target_user=user,
        )
        return Response(two_step_payload(user))


# Where you are signed in


class SessionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        current = current_hash(request)
        now = timezone.now()
        return Response(
            [
                {
                    "device": row.device,
                    "signed_in_at": row.created_at,
                    "last_seen_at": row.last_seen_at,
                    "current": row.key_hash == current,
                    "active_now": (now - row.last_seen_at).total_seconds() < 15 * 60,
                }
                for row in live_sessions(request.user)
            ]
        )


# A copy of your data


def export_payload(user):
    from apps.feed.models import DataExport

    export = DataExport.objects.filter(user=user, used_at__isnull=True).first()
    return {
        "export": None
        if export is None
        else {"ready": export.ready_at is not None, "expires_at": export.expires_at}
    }


class ExportView(CsrfProtectedAPIView):
    """Every account can ask for a zip of its data: the account, RSVPs, membership and,
    for feed members, everything they shared. The link is only ever emailed."""

    permission_classes = [IsAuthenticated]
    write_limit = "ACCOUNT_WRITE_RATE_LIMIT"

    def get(self, request):
        return Response(export_payload(request.user))

    def post(self, request):
        from apps.feed.services import FeedError, request_export

        try:
            request_export(request.user)
        except FeedError as error:
            return Response({"detail": error.message, "code": error.code}, status=error.status)
        return Response(export_payload(request.user), status=status.HTTP_202_ACCEPTED)
