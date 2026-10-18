from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


@method_decorator(csrf_protect, name="dispatch")
class CsrfProtectedAPIView(APIView):
    """DRF exempts API views from CSRF; every state-changing view here opts back in."""


def too_many_requests(message="Too many attempts. Please try again later."):
    return Response({"detail": message}, status=status.HTTP_429_TOO_MANY_REQUESTS)
