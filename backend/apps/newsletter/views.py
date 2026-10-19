from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api import CsrfProtectedAPIView, too_many_requests
from apps.core.email import site_link
from apps.core.ratelimit import is_over_limit

from . import services

# The same answer for a new, pending, confirmed or unsubscribed address.
CHECK_INBOX = {"detail": "Check your inbox for a link to confirm."}


class SubscribeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)


class TokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=64)


class SubscribeView(CsrfProtectedAPIView):
    def post(self, request):
        serializer = SubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        if is_over_limit(
            request,
            "newsletter-subscribe",
            [
                ("ip", settings.NEWSLETTER_RATE_LIMIT_IP),
                (email, settings.NEWSLETTER_RATE_LIMIT_EMAIL),
            ],
        ):
            return too_many_requests("Too many attempts. Please try again later.")
        if not serializer.validated_data.get("website"):
            services.subscribe(email)
        return Response(CHECK_INBOX, status=status.HTTP_200_OK)


class ConfirmView(CsrfProtectedAPIView):
    write_limit = "TOKEN_RATE_LIMIT"

    def post(self, request):
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not services.confirm(serializer.validated_data["token"]):
            return Response(
                {"detail": "This link has expired or was already used. Sign up again below."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "You are subscribed. Thank you."})


class UnsubscribeView(CsrfProtectedAPIView):
    """The page's one-click button."""

    write_limit = "TOKEN_RATE_LIMIT"

    def post(self, request):
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not services.unsubscribe(serializer.validated_data["token"]):
            return Response(
                {"detail": "This link is not valid. You may already be unsubscribed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "You are unsubscribed. No more email will be sent."})


@method_decorator(csrf_exempt, name="dispatch")
class OneClickUnsubscribeView(APIView):
    """RFC 8058 List-Unsubscribe-Post. Mail apps POST without cookies or a CSRF token.

    GET (a person opening the link, or a link scanner) changes nothing: it sends
    them to the site's page, which asks for the click.
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request, token):
        return HttpResponseRedirect(site_link(f"/unsubscribe#token={token}"))

    def post(self, request, token):
        if is_over_limit(request, "newsletter-one-click", [("ip", settings.TOKEN_RATE_LIMIT)]):
            return HttpResponse("Slow down.", status=429, content_type="text/plain")
        if not services.unsubscribe(token):
            raise Http404
        return HttpResponse("Unsubscribed.", content_type="text/plain")
