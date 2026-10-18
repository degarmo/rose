from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.core import is_ratelimited
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api import CsrfProtectedAPIView, too_many_requests
from apps.core.ratelimit import hashed_ip_key, is_over_limit

from . import account, join
from .access import entitlements
from .models import Payment
from .providers import registry
from .providers.base import WebhookVerificationError
from .providers.sandbox import SandboxProvider
from .providers.service import handle_events
from .serializers import (
    AgreementSerializer,
    JoinSerializer,
    MyMembershipSerializer,
    TierSerializer,
    receipt_payload,
)


def membership_payload(user):
    membership = join.open_membership(user)
    if membership is None:
        membership = user.memberships.select_related("tier").first()
    return {
        "membership": MyMembershipSerializer(membership).data if membership else None,
        "entitlements": sorted(entitlements(user)),
    }


class TiersView(APIView):
    def get(self, request):
        return Response(TierSerializer(join.offered_tiers(), many=True).data)


class OptionsView(APIView):
    """Payment methods on offer and the current agreement."""

    def get(self, request):
        agreement = join.current_agreement()
        return Response(
            {
                "methods": join.payment_methods(),
                "agreement": AgreementSerializer(agreement).data if agreement else None,
            }
        )


class MyMembershipView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(membership_payload(request.user))


class JoinView(CsrfProtectedAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if is_over_limit(request, "membership-join", [(f"user:{request.user.pk}", "10/h")]):
            return too_many_requests()
        serializer = JoinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            _, redirect_url = join.join(
                request.user,
                data["tier"],
                data["agreement_version"],
                data["typed_name"],
                data["method"],
            )
        except join.JoinError as exc:
            return Response({"detail": exc.message, "code": exc.code}, status=exc.status)
        return Response(
            {**membership_payload(request.user), "redirect_url": redirect_url},
            status=status.HTTP_201_CREATED,
        )


class CheckoutView(CsrfProtectedAPIView):
    """Pay online for your current membership: a retry after a failure, or a renewal."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        membership = join.open_membership(request.user)
        if membership is None:
            return Response({"detail": "You have no membership to pay for."}, status=404)
        try:
            session = join.start_checkout(membership, str(request.data.get("method", "")))
        except join.JoinError as exc:
            return Response({"detail": exc.message, "code": exc.code}, status=exc.status)
        return Response({"redirect_url": session.redirect_url})


class CancelView(CsrfProtectedAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        membership = join.open_membership(request.user)
        if membership is None:
            return Response({"detail": "You have no membership to cancel."}, status=404)
        try:
            account.cancel(membership)
        except account.AccountError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(membership_payload(request.user))


class AutoRenewView(CsrfProtectedAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        membership = join.open_membership(request.user)
        if membership is None:
            return Response({"detail": "You have no membership."}, status=404)
        try:
            account.set_auto_renew(membership, bool(request.data.get("enabled")))
        except account.AccountError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(membership_payload(request.user))


class ReceiptView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id):
        payment = get_object_or_404(
            Payment.objects.select_related("membership__tier"),
            pk=payment_id,
            membership__user=request.user,
            status__in=[Payment.Status.SUCCEEDED, Payment.Status.REFUNDED],
        )
        return Response(receipt_payload(payment))


@method_decorator(csrf_exempt, name="dispatch")
class WebhookView(APIView):
    """Provider webhooks. Signature verified by the adapter; 200 only once stored."""

    authentication_classes = []
    permission_classes = []

    def post(self, request, provider_key):
        if is_ratelimited(
            request._request,
            group="payments-webhook",
            key=hashed_ip_key,
            rate=settings.PAYMENT_WEBHOOK_RATE_LIMIT,
            method="POST",
            increment=True,
        ):
            return JsonResponse({"detail": "Slow down."}, status=429)
        provider = registry.get(provider_key)
        if provider is None or not provider.online:
            raise Http404
        try:
            events = provider.parse_webhook(request._request)
        except WebhookVerificationError:
            return JsonResponse({"detail": "Signature verification failed."}, status=400)
        new = handle_events(provider.key, events)
        return JsonResponse({"received": len(events), "new": new})


class SandboxCheckoutView(CsrfProtectedAPIView):
    """The fake hosted checkout's backend. Only exists when the sandbox is enabled."""

    def initial(self, request, *args, **kwargs):
        if not settings.DEBUG or registry.get("sandbox") is None:
            raise Http404
        super().initial(request, *args, **kwargs)

    def get(self, request, token):
        session = SandboxProvider.read_session(token)
        if session is None:
            raise Http404
        return Response(
            {
                "amount_cents": session["amount"],
                "reference": session["membership"],
                "interval": session["interval"],
            }
        )

    def post(self, request, token):
        from .tasks import deliver_sandbox_events

        session = SandboxProvider.read_session(token)
        if session is None:
            raise Http404
        outcome = request.data.get("outcome")
        if outcome not in ("pay", "fail", "cancel"):
            return Response({"detail": "Choose pay, fail or cancel."}, status=400)
        payloads = SandboxProvider.event_payloads(session, outcome)
        if payloads:
            deliver_sandbox_events.delay(payloads)
        return Response(
            {"redirect_url": session["cancel"] if outcome == "cancel" else session["success"]}
        )
