"""A fake hosted checkout for development and tests only.

The checkout page (/dev/checkout/<ref>) has Pay, Fail and Cancel buttons. They
post signed fake webhooks to the real webhook endpoint, so the whole online
path runs end to end. Constructing this provider with DEBUG off raises, except
in the end-to-end test stack (DJANGO_ENV=e2e), which is never deployed.
"""

import hashlib
import hmac
import json
import secrets

from django.conf import settings
from django.core import signing
from django.core.exceptions import ImproperlyConfigured

from .base import (
    CHECKOUT_COMPLETED,
    PAYMENT_FAILED,
    PAYMENT_SUCCEEDED,
    CheckoutSession,
    PaymentProvider,
    ProviderEvent,
    WebhookVerificationError,
)

SIGNATURE_HEADER = "HTTP_X_SANDBOX_SIGNATURE"
SESSION_SALT = "memberships.sandbox-checkout"


def sandbox_allowed():
    """Development (DEBUG) and the end-to-end test stack only. Never deployed:
    the deployment checks refuse the sandbox in staging and production too."""
    return settings.DEBUG or settings.DJANGO_ENV == "e2e"


def webhook_secret():
    return hashlib.sha256(f"sandbox-webhook:{settings.SECRET_KEY}".encode()).hexdigest()


def sign(body: bytes) -> str:
    return hmac.new(webhook_secret().encode(), body, hashlib.sha256).hexdigest()


class SandboxProvider(PaymentProvider):
    key = "sandbox"
    label = "Pay online (sandbox)"
    online = True

    def __init__(self):
        if not sandbox_allowed():
            raise ImproperlyConfigured(
                "The sandbox payment provider is for development and the end-to-end "
                "tests only, and cannot run with DEBUG off anywhere else."
            )

    def create_checkout(self, membership, success_url, cancel_url) -> CheckoutSession:
        provider_ref = f"sbx_cs_{secrets.token_hex(8)}"
        token = signing.dumps(
            {
                "ref": provider_ref,
                "membership": membership.reference_code,
                "amount": membership.tier.price_cents,
                "success": success_url,
                "cancel": cancel_url,
                "interval": membership.tier.interval,
            },
            salt=SESSION_SALT,
        )
        return CheckoutSession(
            redirect_url=f"{settings.SITE_URL}/dev/checkout/{token}", provider_ref=provider_ref
        )

    def create_one_time_checkout(
        self, amount_cents, purpose, success_url, cancel_url
    ) -> CheckoutSession:
        provider_ref = f"sbx_cs_{secrets.token_hex(8)}"
        token = signing.dumps(
            {
                "ref": provider_ref,
                "purpose": purpose,
                "amount": amount_cents,
                "success": success_url,
                "cancel": cancel_url,
                "interval": "once",
            },
            salt=SESSION_SALT,
        )
        return CheckoutSession(
            redirect_url=f"{settings.SITE_URL}/dev/checkout/{token}", provider_ref=provider_ref
        )

    @staticmethod
    def read_session(token):
        try:
            return signing.loads(token, salt=SESSION_SALT, max_age=60 * 60 * 6)
        except signing.BadSignature:
            return None

    @staticmethod
    def event_payloads(session, outcome):
        """The webhook bodies a real processor would send for this outcome.

        Membership checkouts carry our reference code; one-time checkouts carry
        their purpose instead, exactly as the processor would echo them back.
        """
        target = (
            {"purpose": session["purpose"]}
            if session.get("purpose")
            else {"membership": session["membership"]}
        )
        subscription = None if session["interval"] == "once" else f"sbx_sub_{secrets.token_hex(6)}"
        customer = f"sbx_cus_{secrets.token_hex(6)}"
        if outcome == "pay":
            payment = f"sbx_pay_{secrets.token_hex(8)}"
            return [
                {
                    "id": f"sbx_evt_{secrets.token_hex(8)}",
                    "type": CHECKOUT_COMPLETED,
                    **target,
                    "customer": customer,
                    "subscription": subscription,
                },
                {
                    "id": f"sbx_evt_{secrets.token_hex(8)}",
                    "type": PAYMENT_SUCCEEDED,
                    **target,
                    "customer": customer,
                    "subscription": subscription,
                    "payment": payment,
                    "amount": session["amount"],
                },
            ]
        if outcome == "fail":
            return [
                {
                    "id": f"sbx_evt_{secrets.token_hex(8)}",
                    "type": PAYMENT_FAILED,
                    **target,
                    "amount": session["amount"],
                }
            ]
        return []

    def parse_webhook(self, request):
        body = request.body
        given = request.META.get(SIGNATURE_HEADER, "")
        if not given or not hmac.compare_digest(given, sign(body)):
            raise WebhookVerificationError("Bad sandbox signature.")
        try:
            data = json.loads(body)
        except ValueError as exc:
            raise WebhookVerificationError("Unreadable sandbox payload.") from exc
        return [
            ProviderEvent(
                event_id=data["id"],
                type=data["type"],
                membership_ref=data.get("membership"),
                purpose=data.get("purpose"),
                customer_ref=data.get("customer"),
                subscription_ref=data.get("subscription"),
                payment_ref=data.get("payment"),
                amount_cents=data.get("amount"),
                payload={
                    k: data.get(k)
                    for k in ("type", "membership", "purpose", "subscription", "payment", "amount")
                },
            )
        ]

    def cancel_subscription(self, membership) -> None:
        """The sandbox has no remote subscription to stop; the service records the cancel."""

    def resume_subscription(self, membership) -> None:
        """The sandbox has no remote subscription to resume; the service records it."""

    def refund(self, payment, amount_cents) -> str | None:
        return f"sbx_re_{secrets.token_hex(8)}"
