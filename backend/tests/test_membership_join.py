"""Joining: in person (manual) and online (sandbox). Activation only ever comes from a webhook."""

import re

import pytest
from django.core import mail

from apps.memberships.emails import REFERENCE_SUBJECT
from apps.memberships.models import AgreementSignature, IdCheck, Membership, Payment

pytestmark = pytest.mark.django_db

TYPED = "Jordan Q. Realname"


@pytest.fixture
def monthly(make_tier):
    return make_tier(name="Monthly", slug="monthly", price_cents=2500)


def join(client, agreement, method="manual", tier="monthly", **overrides):
    payload = {
        "tier": tier,
        "agreement_version": agreement.version,
        "typed_name": TYPED,
        "method": method,
        **overrides,
    }
    return client.post("/api/membership/join/", payload, format="json")


def test_manual_join_gives_a_reference_code(signed_in, monthly, agreement):
    client, user = signed_in()
    response = join(client, agreement)
    assert response.status_code == 201
    data = response.json()
    code = data["membership"]["reference_code"]
    assert re.fullmatch(r"[2-9A-HJKMNP-Z]{3}-[2-9A-HJKMNP-Z]{3}", code)
    assert data["membership"]["status"] == "pending_payment"
    assert data["redirect_url"] is None
    assert data["entitlements"] == []
    assert TYPED not in response.content.decode()
    signature = AgreementSignature.objects.get(user=user)
    assert signature.typed_name == TYPED and signature.agreement == agreement

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.subject == REFERENCE_SUBJECT
    assert code in message.body and "photo ID" in message.body
    assert TYPED not in message.body


def test_join_needs_current_agreement_version(signed_in, monthly, agreement):
    client, _ = signed_in()
    response = join(client, agreement, agreement_version=agreement.version + 1)
    assert response.status_code == 400
    assert response.json()["code"] == "agreement_changed"
    assert not Membership.objects.exists()


@pytest.mark.parametrize("typed_name", ["", " ", "J"])
def test_join_needs_a_typed_name(typed_name, signed_in, monthly, agreement):
    client, _ = signed_in()
    response = join(client, agreement, typed_name=typed_name)
    assert response.status_code == 400
    assert not AgreementSignature.objects.exists()


def test_join_twice_is_refused(signed_in, monthly, agreement):
    client, _ = signed_in()
    assert join(client, agreement).status_code == 201
    response = join(client, agreement)
    assert response.status_code == 409
    assert Membership.objects.count() == 1


def test_unverified_and_anonymous_cannot_join(signed_in, csrf_client, monthly, agreement):
    client, _ = signed_in(verified=False)
    assert join(client, agreement).status_code == 403
    assert join(csrf_client, agreement).status_code in (401, 403)


def test_online_method_refused_without_an_online_provider(signed_in, monthly, agreement):
    client, _ = signed_in()
    response = join(client, agreement, method="sandbox")
    assert response.status_code == 400
    options = client.get("/api/membership/options/").json()
    assert [m["key"] for m in options["methods"]] == ["manual"]


def test_placeholders_are_never_offered_with_debug_off(signed_in, make_tier):
    from django.utils import timezone

    from apps.memberships.models import MembershipAgreement, Tier

    tier = make_tier(slug="demo")
    Tier.objects.filter(pk=tier.pk).update(is_placeholder=True)
    placeholder = MembershipAgreement(body="<p>Placeholder</p>", published_at=timezone.now())
    placeholder.is_placeholder = True
    placeholder.save()
    client, _ = signed_in()
    assert client.get("/api/membership/tiers/").json() == []
    assert client.get("/api/membership/options/").json()["agreement"] is None
    response = join(client, placeholder, tier="demo")
    assert response.status_code == 400
    assert not Membership.objects.exists()


def test_placeholders_are_offered_in_development(signed_in, make_tier, settings):
    from apps.memberships.models import Tier

    settings.DEBUG = True
    tier = make_tier(slug="demo")
    Tier.objects.filter(pk=tier.pk).update(is_placeholder=True)
    client, _ = signed_in()
    assert [t["slug"] for t in client.get("/api/membership/tiers/").json()] == ["demo"]


# Online, through the sandbox


def checkout_token(redirect_url):
    match = re.search(r"/dev/checkout/([^/?#]+)$", redirect_url)
    assert match, redirect_url
    return match.group(1)


def sandbox_outcome(client, token, outcome):
    return client.post(f"/api/payments/sandbox/{token}/", {"outcome": outcome}, format="json")


def test_sandbox_offered_in_development(sandbox, signed_in, monthly, agreement):
    client, _ = signed_in()
    keys = [m["key"] for m in client.get("/api/membership/options/").json()["methods"]]
    assert keys == ["manual", "sandbox"]


def test_sandbox_pay_activates_from_the_webhook(
    sandbox, signed_in, monthly, agreement, make_membership
):
    client, user = signed_in()
    old = make_membership(user=user, status="expired")  # ID seen on an earlier membership
    response = join(client, agreement, method="sandbox")
    assert response.status_code == 201
    redirect = response.json()["redirect_url"]
    assert redirect.startswith("https://site.example/dev/checkout/")
    membership = Membership.objects.non_terminal().get(user=user)
    assert membership.status == "pending_payment"

    token = checkout_token(redirect)
    details = client.get(f"/api/payments/sandbox/{token}/").json()
    assert details == {
        "amount_cents": 2500,
        "reference": membership.reference_code,
        "description": "Membership",
        "interval": "month",
    }

    # Coming back to the return URL changes nothing by itself.
    client.get(f"/api/membership/me/?ref={membership.reference_code}")
    membership.refresh_from_db()
    assert membership.status == "pending_payment"

    result = sandbox_outcome(client, token, "pay").json()
    assert (
        result["redirect_url"]
        == f"https://site.example/join/confirming?ref={membership.reference_code}"
    )
    membership.refresh_from_db()
    assert membership.status == "active"
    assert membership.source == "provider" and membership.provider == "sandbox"
    assert membership.provider_subscription_ref.startswith("sbx_sub_")
    assert membership.auto_renew is True
    payment = membership.payments.get()
    assert payment.method == "online" and payment.amount_cents == 2500
    assert old.status == "expired"
    me = client.get("/api/membership/me/").json()
    assert me["membership"]["online"] is True
    assert "sbx_" not in str(me)


def test_sandbox_pay_without_an_id_check_waits_for_the_door(sandbox, signed_in, monthly, agreement):
    client, user = signed_in()
    token = checkout_token(join(client, agreement, method="sandbox").json()["redirect_url"])
    sandbox_outcome(client, token, "pay")
    membership = Membership.objects.get(user=user)
    assert membership.status == "pending_payment"
    assert membership.paid_awaiting_id_check is True
    assert membership.payments.get().status == "succeeded"
    assert not IdCheck.objects.exists()
    assert client.get("/api/membership/me/").json()["entitlements"] == []


def test_sandbox_failed_payment(sandbox, signed_in, monthly, agreement):
    client, user = signed_in()
    token = checkout_token(join(client, agreement, method="sandbox").json()["redirect_url"])
    sandbox_outcome(client, token, "fail")
    membership = Membership.objects.get(user=user)
    assert membership.status == "pending_payment"
    assert membership.payments.get().status == Payment.Status.FAILED
    me = client.get("/api/membership/me/").json()["membership"]
    assert me["last_payment_failed"] is True

    # Retry with a fresh checkout for the same membership.
    retry = client.post("/api/membership/checkout/", {"method": "sandbox"}, format="json")
    assert retry.status_code == 200
    assert retry.json()["redirect_url"].startswith("https://site.example/dev/checkout/")


def test_sandbox_cancel_sends_nothing(sandbox, signed_in, monthly, agreement):
    client, user = signed_in()
    token = checkout_token(join(client, agreement, method="sandbox").json()["redirect_url"])
    result = sandbox_outcome(client, token, "cancel").json()
    assert result["redirect_url"] == "https://site.example/join?cancelled=1"
    assert not Payment.objects.exists()


def test_sandbox_checkout_rejects_tampered_tokens(sandbox, signed_in):
    client, _ = signed_in()
    assert client.get("/api/payments/sandbox/not-a-token/").status_code == 404


def test_sandbox_checkout_does_not_exist_in_production(signed_in, monthly, agreement, settings):
    client, _ = signed_in()
    assert client.get("/api/payments/sandbox/anything/").status_code == 404
    settings.PAYMENT_PROVIDERS = ["manual", "sandbox"]  # misconfigured, DEBUG still off
    assert client.get("/api/payments/sandbox/anything/").status_code == 404
