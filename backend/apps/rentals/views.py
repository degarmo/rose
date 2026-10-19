import logging

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

from apps.core.api import CsrfProtectedAPIView, too_many_requests
from apps.core.ratelimit import is_over_limit

from . import emails
from .serializers import RentalInquirySerializer

logger = logging.getLogger(__name__)

RECEIVED = {"detail": "Thank you. A volunteer will reply by email, usually within a few days."}


class RentalInquiryCreateView(CsrfProtectedAPIView):
    """Rate limited per client, with a honeypot. The reply never echoes the inquiry."""

    def post(self, request):
        if is_over_limit(request, "rental-inquiry", [("ip", settings.RENTAL_INQUIRY_RATE_LIMIT)]):
            return too_many_requests("Too many requests. Please try again later.")
        serializer = RentalInquirySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data.get("website"):
            # Honeypot tripped: look successful, store and send nothing.
            return Response(RECEIVED, status=status.HTTP_201_CREATED)
        user = request.user if request.user.is_authenticated else None
        inquiry = serializer.save(user=user)
        for send in (emails.send_confirmation, emails.notify_staff):
            try:
                send(inquiry)
            except Exception:
                logger.exception("Rental email failed for inquiry %s", inquiry.pk)
        return Response(RECEIVED, status=status.HTTP_201_CREATED)
