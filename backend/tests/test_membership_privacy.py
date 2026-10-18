"""Payments and membership status are sensitive: no leaks, own records only."""

import pytest
from django.core import mail
from rest_framework.test import APIClient

from apps.memberships.models import AgreementSignature, Membership, Payment

pytestmark = pytest.mark.django_db
TYPED = "Riley Verysecretname"


@pytest.fixture
def paying_member(make_user, make_membership, agreement):
    user = make_user(display_name="paying_member")
    AgreementSignature.objects.create(user=user, agreement=agreement, typed_name=TYPED)
    membership = make_membership(
        user=user,
        source="provider",
        provider="sandbox",
        provider_customer_ref="cus_secret_ref",
        provider_subscription_ref="sub_secret_ref",
    )
    payment = Payment.objects.create(
        membership=membership,
        amount_cents=2500,
        method="online",
        provider_payment_ref="pay_secret_ref",
    )
    return user, membership, payment


def test_typed_name_and_provider_refs_never_reach_any_api(paying_member, signed_in):
    """Crawl every API route as the member, as someone else and anonymously."""
    from tests.test_privacy import api_routes

    user, membership, payment = paying_member
    owner, _ = signed_in(user=user)
    other, _ = signed_in(display_name="curious_other")
    secrets = [TYPED, "cus_secret_ref", "sub_secret_ref", "pay_secret_ref"]
    for client in (owner, other, APIClient()):
        for route, _name in api_routes():
            path = "/" + route.replace("<int:payment_id>", str(payment.pk))
            if "<" in path:
                continue
            body = client.get(path).content.decode()
            for secret in secrets:
                assert secret not in body, f"{secret!r} at {path}"
        receipt = client.get(f"/api/membership/receipts/{payment.pk}/").content.decode()
        assert all(s not in receipt for s in secrets)


def test_membership_status_is_only_visible_to_its_owner(paying_member, signed_in):
    user, membership, payment = paying_member
    other, _ = signed_in()
    assert other.get("/api/membership/me/").json()["membership"] is None
    assert other.get(f"/api/membership/receipts/{payment.pk}/").status_code == 404
    assert APIClient().get("/api/membership/me/").status_code in (401, 403)


def test_receipt_is_neutral(paying_member, signed_in, settings):
    settings.MERCHANT_DISPLAY_NAME = "Rose House LLC"
    user, membership, payment = paying_member
    client, _ = signed_in(user=user)
    receipt = client.get(f"/api/membership/receipts/{payment.pk}/").json()
    assert receipt["title"] == "Receipt"
    assert receipt["merchant"] == "Rose House LLC"
    assert receipt["description"] == "Membership"
    assert receipt["reference"] == f"{membership.reference_code}-{payment.pk}"
    assert receipt["amount_cents"] == 2500
    assert set(receipt) == {
        "title",
        "merchant",
        "description",
        "reference",
        "date",
        "amount_cents",
        "currency",
        "method",
        "kind",
    }
    assert membership.tier.name not in str(receipt)


def test_failed_payments_have_no_receipt(paying_member, signed_in):
    user, membership, _ = paying_member
    failed = Payment.objects.create(
        membership=membership, amount_cents=2500, method="online", status="failed"
    )
    client, _ = signed_in(user=user)
    assert client.get(f"/api/membership/receipts/{failed.pk}/").status_code == 404


def test_my_membership_payload_is_minimal(paying_member, signed_in):
    user, membership, _ = paying_member
    client, _ = signed_in(user=user)
    data = client.get("/api/membership/me/").json()
    assert set(data["membership"]) == {
        "reference_code",
        "tier",
        "status",
        "status_label",
        "current_period_start",
        "current_period_end",
        "auto_renew",
        "cancel_at_period_end",
        "paid_awaiting_id_check",
        "source",
        "online",
        "id_checked",
        "last_payment_failed",
        "payments",
        "created_at",
    }
    assert data["membership"]["id_checked"] is True  # whether, never what
    assert set(data["membership"]["payments"][0]) == {
        "id",
        "created_at",
        "amount_cents",
        "method",
        "method_label",
        "status",
        "status_label",
    }


def test_account_deletion_keeps_payments_detached(paying_member, signed_in):
    from tests.conftest import PASSWORD

    user, membership, payment = paying_member
    client, _ = signed_in(user=user)
    response = client.post("/api/account/delete/", {"password": PASSWORD}, format="json")
    assert response.status_code in (200, 204), response.content
    membership.refresh_from_db()
    assert membership.user is None and membership.status == "cancelled"
    assert Payment.objects.filter(pk=payment.pk).exists()
    assert not AgreementSignature.objects.filter(typed_name=TYPED).exists()


def test_member_can_cancel_and_toggle_auto_renew(sandbox, paying_member, signed_in):
    user, membership, _ = paying_member
    client, _ = signed_in(user=user)
    off = client.post("/api/membership/auto-renew/", {"enabled": False}, format="json").json()
    assert off["membership"]["auto_renew"] is False and off["membership"]["cancel_at_period_end"]
    on = client.post("/api/membership/auto-renew/", {"enabled": True}, format="json").json()
    assert on["membership"]["auto_renew"] is True and not on["membership"]["cancel_at_period_end"]
    cancelled = client.post("/api/membership/cancel/", {}, format="json").json()
    assert cancelled["membership"]["status"] == "active"
    assert cancelled["membership"]["cancel_at_period_end"] is True
    assert mail.outbox == []


def test_in_person_membership_has_no_auto_renew(signed_in, make_membership):
    client, user = signed_in()
    make_membership(user=user)
    response = client.post("/api/membership/auto-renew/", {"enabled": True}, format="json")
    assert response.status_code == 400


def test_pending_cancel_ends_immediately(signed_in, make_membership):
    client, user = signed_in()
    make_membership(user=user, status="pending_payment")
    data = client.post("/api/membership/cancel/", {}, format="json").json()
    assert data["membership"]["status"] == "cancelled"
    assert Membership.objects.non_terminal().count() == 0


def test_no_serializer_outputs_the_typed_name():
    from tests.test_privacy import project_serializer_classes

    for serializer_class in project_serializer_classes():
        for name, field in serializer_class().fields.items():
            source = getattr(field, "source", name) or name
            if "typed_name" in (name, source):
                assert field.write_only, f"{serializer_class.__name__}.{name} would output it"
