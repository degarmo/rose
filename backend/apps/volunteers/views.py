import logging

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api import CsrfProtectedAPIView, too_many_requests
from apps.core.ratelimit import is_over_limit

from . import emails
from .models import Availability, Interest
from .serializers import VolunteerSignupSerializer

logger = logging.getLogger(__name__)

RECEIVED = {"detail": "Thank you for offering to help. A volunteer coordinator will be in touch."}


class VolunteerOptionsView(APIView):
    """The roles and availability choices the form offers."""

    def get(self, request):
        return Response(
            {
                "interests": [{"value": v, "label": label} for v, label in Interest.choices],
                "availability": [{"value": v, "label": label} for v, label in Availability.choices],
            }
        )


class VolunteerSignupCreateView(CsrfProtectedAPIView):
    """Rate limited, with a honeypot. Signed-in people are linked to their account."""

    def post(self, request):
        if is_over_limit(request, "volunteer-signup", [("ip", settings.VOLUNTEER_RATE_LIMIT)]):
            return too_many_requests("Too many requests. Please try again later.")
        serializer = VolunteerSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data.get("website"):
            return Response(RECEIVED, status=status.HTTP_201_CREATED)
        user = request.user if request.user.is_authenticated else None
        signup = serializer.save(user=user)
        for send in (emails.send_confirmation, emails.notify_staff):
            try:
                send(signup)
            except Exception:
                logger.exception("Volunteer email failed for signup %s", signup.pk)
        return Response(RECEIVED, status=status.HTTP_201_CREATED)
