"""Base class for every members-area endpoint.

The access check runs before anything else, including CSRF, so anyone
without feed access gets an identical 404 for every path and method.
"""

from django.conf import settings
from django.http import Http404
from rest_framework.authentication import CSRFCheck, SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api import check_write_limit

from .access import can_view_feed
from .services import FeedError


class SessionWithoutCsrf(SessionAuthentication):
    """Session auth that defers CSRF until after the access check."""

    def enforce_csrf(self, request):
        return None


def enforce_csrf(request):
    check = CSRFCheck(lambda req: None)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        raise PermissionDenied(f"CSRF Failed: {reason}")


class FeedAPIView(APIView):
    authentication_classes = [SessionWithoutCsrf]
    write_limit = None

    def initial(self, request, *args, **kwargs):
        # FEED_ENABLED is the incident kill switch (docs/ops/incident.md).
        if not settings.FEED_ENABLED or not can_view_feed(request.user):
            raise Http404
        if request.method not in SAFE_METHODS:
            enforce_csrf(request._request)
        super().initial(request, *args, **kwargs)
        check_write_limit(self, request)

    def handle_exception(self, exc):
        if isinstance(exc, FeedError):
            if exc.status == 404:
                raise Http404 from exc
            return Response({"detail": exc.message, "code": exc.code}, status=exc.status)
        return super().handle_exception(exc)
