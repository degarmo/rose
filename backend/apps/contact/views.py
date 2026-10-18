import logging

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django_ratelimit.core import is_ratelimited
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.ratelimit import hashed_ip_key

from .notifications import notify_new_message
from .serializers import ContactMessageSerializer

logger = logging.getLogger(__name__)

RATE_LIMIT_GROUP = "contact"


@method_decorator(csrf_protect, name="dispatch")
class ContactMessageCreateView(APIView):
    authentication_classes = []

    def post(self, request):
        limited = is_ratelimited(
            request,
            group=RATE_LIMIT_GROUP,
            key=hashed_ip_key,
            rate=settings.CONTACT_RATE_LIMIT,
            method="POST",
            increment=True,
        )
        if limited:
            return Response(
                {"detail": "Too many messages. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = ContactMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data.get("website"):
            # Honeypot tripped: look successful, store nothing.
            return Response({"ok": True}, status=status.HTTP_201_CREATED)

        message = serializer.save()
        try:
            notify_new_message(message)
        except Exception:
            logger.exception("Contact notification failed for message %s", message.pk)
        return Response({"ok": True}, status=status.HTTP_201_CREATED)
