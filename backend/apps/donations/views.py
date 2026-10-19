from django.conf import settings
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api import CsrfProtectedAPIView, too_many_requests
from apps.core.ratelimit import is_over_limit
from apps.pages.models import SiteSettings

from . import services


class CheckoutSerializer(serializers.Serializer):
    amount_cents = serializers.IntegerField(min_value=1)
    email = serializers.EmailField(required=False, allow_blank=True)
    show_name = serializers.BooleanField(required=False, default=False)
    # Honeypot: hidden from people, filled in by most bots.
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)


class DonationOptionsView(APIView):
    """How people can give. Never anything about who has given."""

    def get(self, request):
        site = SiteSettings.load()
        return Response(
            {
                "online": services.online_provider() is not None,
                "presets_cents": settings.DONATION_PRESETS_CENTS,
                "minimum_cents": settings.DONATION_MINIMUM_CENTS,
                "maximum_cents": settings.DONATION_MAXIMUM_CENTS,
                "nonprofit_status": site.nonprofit_status_text,
                "check_payable_to": site.check_payable_to,
                "mailing_address": site.mailing_address,
            }
        )


class DonationCheckoutView(CsrfProtectedAPIView):
    """Start an online gift. Answers with the hosted checkout's address only."""

    def post(self, request):
        if is_over_limit(request, "donation-checkout", [("ip", settings.DONATION_RATE_LIMIT)]):
            return too_many_requests("Too many attempts. Please try again later.")
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data.get("website"):
            return Response({"detail": "Online giving is not available."}, status=400)
        try:
            redirect_url = services.start_online_checkout(
                data["amount_cents"],
                email=data.get("email", ""),
                show_name=data.get("show_name", False),
                user=request.user,
            )
        except services.DonationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"redirect_url": redirect_url}, status=status.HTTP_201_CREATED)
