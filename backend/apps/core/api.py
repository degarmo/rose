from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.exceptions import Throttled
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView

from .ratelimit import is_over_limit

THROTTLED = "Too many requests. Please wait a little and try again."


def check_write_limit(view, request):
    """One limit per endpoint for every unsafe method: per account, or per IP when signed out.

    Endpoints with their own tighter limits (login, registration, contact, the
    webhook) keep those as well. Every limit is listed in docs/ops/security.md.
    """
    if request.method in SAFE_METHODS:
        return
    rate = getattr(settings, getattr(view, "write_limit", None) or "WRITE_RATE_LIMIT")
    key = f"user:{request.user.pk}" if request.user.is_authenticated else "ip"
    if is_over_limit(request, f"write:{type(view).__name__}", [(key, rate)]):
        raise Throttled(detail=THROTTLED)


@method_decorator(csrf_protect, name="dispatch")
class CsrfProtectedAPIView(APIView):
    """DRF exempts API views from CSRF; every state-changing view here opts back in."""

    #: Name of the setting holding this endpoint's write limit.
    write_limit = None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        check_write_limit(self, request)


def too_many_requests(message="Too many attempts. Please try again later."):
    return Response({"detail": message}, status=status.HTTP_429_TOO_MANY_REQUESTS)
