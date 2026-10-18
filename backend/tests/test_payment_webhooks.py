"""The provider layer: signatures, idempotency, ordering, and the sandbox guard."""

import json
import secrets

import pytest
from django.core.exceptions import ImproperlyConfigured

from apps.memberships.models import Membership, Payment, WebhookEvent
from apps.memberships.providers import registry
from apps.memberships.providers.sandbox import SandboxProvider, sign

pytestmark = pytest.mark.django_db
URL = "/api/payments/webhook/sandbox/"


def post_event(client, payload, signature=None):
    body = json.dumps(payload).encode()
    return client.post(
        URL,
        data=body,
        content_type="application/json",
        HTTP_X_SANDBOX_SIGNATURE=sign(body) if signature is None else signature,
    )


def event(kind, membership, **extra):
    return {
        "id": f"evt_{secrets.token_hex(6)}",
        "type": kind,
        "membership": membership.reference_code,
        **extra,
    }


@pytest.fixture
def pending(make_membership, make_tier):
    return make_membership(
        status="pending_payment", id_check=True, tier=make_tier(price_cents=4000)
    )


def test_payment_succeeded_activates(sandbox, client, pending):
    response = post_event(
        client,
        event("payment_succeeded", pending, payment="pay_1", amount=4000, subscription="sub_1"),
    )
    assert response.status_code == 200
    assert response.json() == {"received": 1, "new": 1}
    pending.refresh_from_db()
    assert pending.status == "active"
    assert pending.current_period_end is not None
    assert WebhookEvent.objects.get().processed_at is not None


def test_same_event_twice_is_applied_once(sandbox, client, pending):
    payload = event("payment_succeeded", pending, payment="pay_1", amount=4000)
    post_event(client, payload)
    pending.refresh_from_db()
    end = pending.current_period_end
    second = post_event(client, payload)
    assert second.status_code == 200 and second.json()["new"] == 0
    pending.refresh_from_db()
    assert pending.current_period_end == end
    assert Payment.objects.count() == 1
    assert WebhookEvent.objects.count() == 1


def test_bad_signature_is_rejected_and_not_stored(sandbox, client, pending):
    response = post_event(
        client, event("payment_succeeded", pending, amount=4000), signature="0" * 64
    )
    assert response.status_code == 400
    missing = post_event(client, event("payment_succeeded", pending, amount=4000), signature="")
    assert missing.status_code == 400
    assert not WebhookEvent.objects.exists()
    pending.refresh_from_db()
    assert pending.status == "pending_payment"


def test_out_of_order_events(sandbox, client, pending):
    """The payment arrives before checkout completes; both still apply correctly."""
    post_event(
        client,
        event("payment_succeeded", pending, payment="pay_1", amount=4000, subscription="sub_9"),
    )
    post_event(client, event("checkout_completed", pending, customer="cus_9", subscription="sub_9"))
    pending.refresh_from_db()
    assert pending.status == "active"
    assert pending.provider_customer_ref == "cus_9"
    assert pending.provider_subscription_ref == "sub_9"
    # A later renewal names only the subscription.
    end = pending.current_period_end
    post_event(
        client,
        {
            "id": "evt_renew",
            "type": "payment_succeeded",
            "subscription": "sub_9",
            "payment": "pay_2",
            "amount": 4000,
        },
    )
    pending.refresh_from_db()
    assert pending.current_period_end > end
    assert pending.payments.count() == 2


def test_cancel_and_refund_events(sandbox, client, pending):
    post_event(
        client,
        event("payment_succeeded", pending, payment="pay_1", amount=4000, subscription="sub_1"),
    )
    post_event(client, event("subscription_cancelled", pending, subscription="sub_1"))
    post_event(client, event("refunded", pending, payment="pay_1", amount=1500))
    pending.refresh_from_db()
    assert pending.status == "active"  # access continues to period end
    assert pending.cancel_at_period_end is True and pending.auto_renew is False
    refund = Payment.objects.get(status="refunded")
    assert refund.amount_cents == 1500 and refund.refund_of.provider_payment_ref == "pay_1"


def test_event_for_unknown_membership_is_stored_with_error(sandbox, client):
    response = post_event(
        client, {"id": "evt_x", "type": "payment_succeeded", "membership": "ZZZ-ZZZ", "amount": 1}
    )
    assert response.status_code == 200
    stored = WebhookEvent.objects.get()
    assert stored.processed_at is None and "LookupError" in stored.error


def test_unknown_or_offline_providers_are_404(sandbox, client):
    assert (
        client.post(
            "/api/payments/webhook/nope/", data=b"{}", content_type="application/json"
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/payments/webhook/manual/", data=b"{}", content_type="application/json"
        ).status_code
        == 404
    )


def test_webhook_is_404_in_production(client, pending):
    response = post_event(client, event("payment_succeeded", pending, amount=4000))
    assert response.status_code == 404
    pending.refresh_from_db()
    assert pending.status == "pending_payment"


def test_webhook_is_rate_limited(sandbox, client, settings):
    settings.PAYMENT_WEBHOOK_RATE_LIMIT = "2/m"
    codes = [
        post_event(client, {"id": f"e{i}", "type": "payment_failed"}, signature="x").status_code
        for i in range(3)
    ]
    assert codes == [400, 400, 429]


def test_webhook_needs_no_csrf_token(sandbox, pending):
    from rest_framework.test import APIClient

    client = APIClient(enforce_csrf_checks=True)
    assert post_event(client, event("payment_failed", pending, amount=4000)).status_code == 200


# The sandbox can never exist in production


def test_sandbox_refuses_to_construct_with_debug_off(settings):
    settings.DEBUG = False
    with pytest.raises(ImproperlyConfigured):
        SandboxProvider()


def test_registry_refuses_sandbox_with_debug_off(settings):
    settings.DEBUG = False
    settings.PAYMENT_PROVIDERS = ["manual", "sandbox"]
    with pytest.raises(ImproperlyConfigured):
        registry.validate()
    with pytest.raises(ImproperlyConfigured):
        registry.get("sandbox")


def test_registry_requires_manual_and_known_keys(settings):
    settings.PAYMENT_PROVIDERS = ["sandbox"]
    with pytest.raises(ImproperlyConfigured):
        registry.validate()
    settings.PAYMENT_PROVIDERS = ["manual", "made-up"]
    with pytest.raises(ImproperlyConfigured):
        registry.validate()


@pytest.mark.parametrize(
    "debug,expected", [("False", "['manual']"), ("True", "['manual', 'sandbox']")]
)
def test_provider_default_follows_debug(debug, expected):
    """With DEBUG off and nothing configured, only the in-person provider exists."""
    import os
    import subprocess
    import sys
    from pathlib import Path

    env = {
        **os.environ,
        "DJANGO_DEBUG": debug,
        "DJANGO_SECRET_KEY": "x" * 50,
        "DJANGO_SETTINGS_MODULE": "config.settings",
    }
    env.pop("PAYMENT_PROVIDERS", None)
    script = "from django.conf import settings; print(settings.PAYMENT_PROVIDERS)"
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parent.parent,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == expected


def test_sandbox_delivery_refuses_in_production(settings):
    from apps.memberships.sandbox_delivery import deliver

    with pytest.raises(ImproperlyConfigured):
        deliver({"id": "e", "type": "payment_failed"})


def test_membership_status_untouched_by_failed_events(sandbox, client, pending):
    post_event(client, event("payment_failed", pending, amount=4000))
    pending.refresh_from_db()
    assert pending.status == Membership.Status.PENDING_PAYMENT
