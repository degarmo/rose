"""Base class for the staff section's endpoints.

The role and two-step checks run before anything else, including CSRF, so anyone
without them gets the same 404 as an unknown address, for every path and method.
"""

from django.http import Http404
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api import check_write_limit
from apps.feed.api import SessionWithoutCsrf, enforce_csrf

from . import roles
from .services import SafetyError


class StaffAPIView(APIView):
    authentication_classes = [SessionWithoutCsrf]
    minimum_role = roles.MODERATOR
    write_limit = None

    def initial(self, request, *args, **kwargs):
        if not roles.can_use_staff_section(request.user, self.minimum_role):
            raise Http404
        if request.method not in SAFE_METHODS:
            enforce_csrf(request._request)
        super().initial(request, *args, **kwargs)
        check_write_limit(self, request)

    def handle_exception(self, exc):
        if isinstance(exc, SafetyError):
            if exc.status == 404:
                raise Http404 from exc
            return Response({"detail": exc.message, "code": exc.code}, status=exc.status)
        return super().handle_exception(exc)
