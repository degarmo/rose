"""Feed controls on /account: join, step away, erase and export.

These live outside /api/members/ because people who have stepped away must
still reach them. They are hidden (404) from anyone with no feed entitlement
and no feed history.
"""

from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api import CsrfProtectedAPIView, check_write_limit
from apps.core.private_media import private_media, with_private_headers

from . import access, services
from .api import SessionWithoutCsrf, enforce_csrf
from .models import DataExport, FeedPost, Guidelines
from .views import guidelines_payload


class FeedAccountBase(APIView):
    """Feed controls on /account. Like the feed itself, anyone without access (signed
    out included) gets the same 404, decided before CSRF or anything else."""

    authentication_classes = [SessionWithoutCsrf]
    write_limit = None

    def initial(self, request, *args, **kwargs):
        user = request.user
        if not (
            settings.FEED_ENABLED and user.is_authenticated and access.feed_account_visible(user)
        ):
            raise Http404
        if request.method not in SAFE_METHODS:
            enforce_csrf(request._request)
        super().initial(request, *args, **kwargs)
        check_write_limit(self, request)

    def handle_exception(self, exc):
        if isinstance(exc, services.FeedError):
            if exc.status == 404:
                raise Http404 from exc
            return Response({"detail": exc.message, "code": exc.code}, status=exc.status)
        return super().handle_exception(exc)


def account_feed_payload(user):
    profile = user.profile
    current = Guidelines.current()
    export = DataExport.objects.filter(user=user, used_at__isnull=True).first()
    return {
        "participating": profile.participates_in_feed,
        "can_join": access.can_join_feed(user),
        "can_view": access.can_view_feed(user),
        "banned": profile.is_feed_banned,
        "suspended_until": profile.feed_suspended_until if profile.is_feed_suspended() else None,
        "accepted_current_guidelines": access.has_accepted_current_guidelines(user),
        "guidelines": guidelines_payload(current) if current else None,
        "has_content": FeedPost.objects.filter(author=user).exists()
        or profile.joined_feed_at is not None,
        "profile": {
            "display_name": user.display_name,
            "bio": profile.bio,
            "hide_from_directory": profile.hide_from_directory,
            "has_avatar": bool(profile.avatar),
        },
        "export": None
        if export is None
        else {"ready": export.ready_at is not None, "expires_at": export.expires_at},
    }


class FeedAccountView(FeedAccountBase):
    def get(self, request):
        return Response(account_feed_payload(request.user))


class JoinFeedView(FeedAccountBase):
    def post(self, request):
        try:
            version = int(request.data.get("guidelines_version"))
        except (TypeError, ValueError):
            return Response({"detail": "Read and accept the guidelines first."}, status=400)
        services.join_feed(
            request.user,
            version,
            bio=str(request.data.get("bio", "")),
            hide_from_directory=bool(request.data.get("hide_from_directory", True)),
        )
        return Response(account_feed_payload(request.user))


class AcceptGuidelinesView(FeedAccountBase):
    def post(self, request):
        try:
            version = int(request.data.get("guidelines_version"))
        except (TypeError, ValueError):
            return Response({"detail": "Read and accept the guidelines first."}, status=400)
        services.accept_guidelines(request.user, version)
        return Response(account_feed_payload(request.user))


class StepAwayView(FeedAccountBase):
    def post(self, request):
        services.step_away(request.user)
        return Response(account_feed_payload(request.user))


class EraseView(FeedAccountBase):
    write_limit = "ACCOUNT_WRITE_RATE_LIMIT"

    def post(self, request):
        if str(request.data.get("display_name", "")) != request.user.display_name:
            return Response(
                {"detail": "Type your display name exactly as it appears to confirm."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Hide everything at once; the worker then deletes it for good.
        services.step_away(request.user)
        from .tasks import erase_member_feed

        services.on_commit(lambda: erase_member_feed.delay(request.user.pk))
        return Response(account_feed_payload(request.user), status=status.HTTP_202_ACCEPTED)


class ExportView(FeedAccountBase):
    write_limit = "ACCOUNT_WRITE_RATE_LIMIT"

    def post(self, request):
        services.request_export(request.user)
        return Response(account_feed_payload(request.user), status=status.HTTP_202_ACCEPTED)


class ExportDownloadView(CsrfProtectedAPIView):
    """Single-use zip download. The token is the credential, so no sign-in is needed."""

    write_limit = "TOKEN_RATE_LIMIT"

    def post(self, request):
        export = services.claim_export(str(request.data.get("token", "")))
        response = FileResponse(
            private_media().storage.open(export.file_name, "rb"),
            content_type="application/zip",
        )
        with_private_headers(response)
        response["Content-Disposition"] = 'attachment; filename="my-data.zip"'
        return response

    def handle_exception(self, exc):
        if isinstance(exc, services.FeedError):
            return Response({"detail": exc.message, "code": exc.code}, status=400)
        return super().handle_exception(exc)
