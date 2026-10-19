"""Giving: online through the provider layer, at the door, acknowledgements, and privacy."""

import json
import secrets
from datetime import timedelta

import pytest
from django.core import mail
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import AuditLog
from apps.donations import services
from apps.donations.models import (
    Acknowledgement,
    AcknowledgementTemplate,
    Donation,
    DonationCheckout,
)
from apps.donations.tasks import purge_donation_contacts
from apps.memberships.models import WebhookEvent
from apps.memberships.providers.sandbox import sign
from apps.pages.models import SiteSettings
from tests.conftest import staff_login

pytestmark = pytest.mark.django_db
CHECKOUT = "/api/donations/checkout/"
WEBHOOK = "/api/payments/webhook/sandbox/"


@pytest.fixture
def wording():
    site = SiteSettings.load()
    site.legal_name = "Example House Association"
    site.ein = "12-3456789"
    site.save()
    return AcknowledgementTemplate.objects.create(
        body="Dear {donor_name}, thank you for {amount} on {date}. {legal_name}, EIN {ein}."
    )


def token_from(redirect_url):
    return redirect_url.rsplit("/dev/checkout/", 1)[1]


def test_options_without_an_online_provider(api_client):
    data = api_client.get("/api/donations/options/").json()
    assert data["online"] is False
    assert data["minimum_cents"] == 500 and data["presets_cents"] == [2500, 5000, 10000, 25000]
    assert set(data) == {
        "online",
        "presets_cents",
        "minimum_cents",
        "maximum_cents",
        "nonprofit_status",
        "check_payable_to",
        "mailing_address",
    }


def test_no_online_checkout_without_a_provider(csrf_client):
    response = csrf_client.post(CHECKOUT, {"amount_cents": 2500}, format="json")
    assert response.status_code == 400
    assert not DonationCheckout.objects.exists()


def test_minimum_gift_is_five_dollars(sandbox, csrf_client):
    response = csrf_client.post(CHECKOUT, {"amount_cents": 499}, format="json")
    assert response.status_code == 400 and "$5" in response.json()["detail"]


def test_sandbox_checkout_records_the_gift_from_the_webhook(sandbox, csrf_client, wording):
    response = csrf_client.post(
        CHECKOUT, {"amount_cents": 3000, "email": "giver@private.example"}, format="json"
    )
    assert response.status_code == 201
    redirect = response.json()["redirect_url"]
    assert redirect.startswith("https://site.example/dev/checkout/")
    checkout = DonationCheckout.objects.get()
    assert checkout.provider == "sandbox" and checkout.donor is None

    # The hosted checkout describes it neutrally, then the person pays.
    token = token_from(redirect)
    details = csrf_client.get(f"/api/payments/sandbox/{token}/").json()
    assert details["description"] == "Donation" and details["amount_cents"] == 3000
    assert details["reference"] == checkout.reference
    # Nothing is recorded from the browser coming back; only from the webhook.
    assert not Donation.objects.exists()
    paid = csrf_client.post(f"/api/payments/sandbox/{token}/", {"outcome": "pay"}, format="json")
    assert paid.json()["redirect_url"].endswith("/get-involved/donate?thanks=1")

    donation = Donation.objects.get()
    assert donation.status == "succeeded" and donation.method == "online"
    assert donation.amount_cents == 3000 and donation.donor_display == "Anonymous"
    assert donation.reference == checkout.reference and donation.acknowledgement_requested
    # The acknowledgement went out under a neutral subject, and the address is forgotten.
    assert [m.subject for m in mail.outbox] == ["Thank you for your gift"]
    assert "EIN 12-3456789" in mail.outbox[0].body
    acknowledgement = Acknowledgement.objects.get()
    assert acknowledgement.email == "" and acknowledgement.emailed_at
    checkout.refresh_from_db()
    assert checkout.acknowledgement_email == "" and checkout.completed_at


def test_show_name_links_the_gift_only_when_asked(sandbox, signed_in):
    client, user = signed_in(display_name="generous_one")
    redirect = client.post(CHECKOUT, {"amount_cents": 2500}, format="json").json()["redirect_url"]
    client.post(f"/api/payments/sandbox/{token_from(redirect)}/", {"outcome": "pay"}, format="json")
    redirect = client.post(
        CHECKOUT, {"amount_cents": 2500, "show_name": True}, format="json"
    ).json()["redirect_url"]
    client.post(f"/api/payments/sandbox/{token_from(redirect)}/", {"outcome": "pay"}, format="json")
    anonymous, named = Donation.objects.order_by("created_at")
    assert (anonymous.donor, anonymous.donor_display) == (None, "Anonymous")
    assert (named.donor, named.donor_display) == (user, "generous_one")


def webhook(client, payload):
    body = json.dumps(payload).encode()
    return client.post(
        WEBHOOK, data=body, content_type="application/json", HTTP_X_SANDBOX_SIGNATURE=sign(body)
    )


def test_webhooks_are_idempotent(sandbox, client):
    checkout = DonationCheckout.objects.create(amount_cents=5000, provider="sandbox")
    payload = {
        "id": f"evt_{secrets.token_hex(6)}",
        "type": "payment_succeeded",
        "purpose": checkout.purpose,
        "payment": "pay_1",
        "amount": 5000,
    }
    assert webhook(client, payload).json() == {"received": 1, "new": 1}
    assert webhook(client, payload).json() == {"received": 1, "new": 0}
    assert Donation.objects.count() == 1
    assert WebhookEvent.objects.count() == 1


def test_failed_and_refunded_gifts_are_new_rows(sandbox, client):
    checkout = DonationCheckout.objects.create(amount_cents=5000, provider="sandbox")
    webhook(client, {"id": "e1", "type": "payment_failed", "purpose": checkout.purpose})
    webhook(
        client,
        {"id": "e2", "type": "payment_succeeded", "purpose": checkout.purpose, "payment": "p9"},
    )
    webhook(
        client,
        {
            "id": "e3",
            "type": "refunded",
            "purpose": checkout.purpose,
            "payment": "p9",
            "amount": 2000,
        },
    )
    statuses = sorted(Donation.objects.values_list("status", flat=True))
    assert statuses == ["failed", "refunded", "succeeded"]
    refund = Donation.objects.get(status="refunded")
    assert refund.refund_of.status == "succeeded" and refund.amount_cents == 2000


def test_unknown_purpose_is_stored_with_an_error(sandbox, client):
    webhook(client, {"id": "e1", "type": "payment_succeeded", "purpose": "raffle:XYZ"})
    stored = WebhookEvent.objects.get()
    assert "No handler" in stored.error and not Donation.objects.exists()


# Immutability


def test_donations_are_append_only():
    donation = Donation.objects.create(amount_cents=1000, method="cash")
    donation.amount_cents = 1
    with pytest.raises(ValidationError):
        donation.save()
    with pytest.raises(ValidationError):
        donation.delete()
    with pytest.raises(ValidationError):
        Donation.objects.update(amount_cents=1)
    with pytest.raises(ValidationError):
        Donation.objects.all().delete()


def test_admin_cannot_add_change_or_delete_donations(admin_client):
    donation = Donation.objects.create(amount_cents=1000, method="cash")
    assert admin_client.get(reverse("admin:donations_donation_add")).status_code == 403
    change = admin_client.get(reverse("admin:donations_donation_change", args=[donation.pk]))
    assert change.status_code == 200 and 'name="_save"' not in change.content.decode()
    delete = admin_client.get(reverse("admin:donations_donation_delete", args=[donation.pk]))
    assert delete.status_code == 403


# At the door


def test_door_desk_records_a_donation(client, desk_staff, wording):
    staff_login(client, desk_staff)
    client.post(
        reverse("admin:memberships_door_desk"),
        {
            "action": "record_donation",
            "method": "check",
            "amount": "40",
            "donor_display": "",
            "acknowledgement_email": "giver@private.example",
        },
    )
    donation = Donation.objects.get()
    assert (donation.method, donation.amount_cents, donation.donor_display) == (
        "check",
        4000,
        "Anonymous",
    )
    assert donation.recorded_by == desk_staff
    entry = AuditLog.objects.get(category="donations", action="record_donation")
    assert entry.target_ref == donation.reference and "giver" not in entry.reason
    assert [m.subject for m in mail.outbox] == ["Thank you for your gift"]


def test_desk_refuses_online_as_a_method(desk_staff):
    with pytest.raises(services.DonationError):
        services.record_desk_donation(desk_staff, 1000, "online")


# Acknowledgements


def test_printable_acknowledgement_uses_the_wording_and_is_logged(admin_client, wording):
    donation = Donation.objects.create(amount_cents=2500, method="cash", donor_display="Pat")
    url = reverse("admin:donations_acknowledgement", args=[donation.pk])
    page = admin_client.get(url).content.decode()
    assert "Dear Pat, thank you for $25.00" in page and "EIN 12-3456789" in page
    admin_client.post(url, {"action": "printed"})
    assert AuditLog.objects.filter(action="acknowledgement_printed").exists()


def test_placeholder_wording_is_never_used_with_debug_off(settings):
    template = AcknowledgementTemplate(body="PLACEHOLDER")
    template.is_placeholder = True
    template.save()
    settings.DEBUG = False
    assert AcknowledgementTemplate.current() is None
    donation = Donation.objects.create(amount_cents=2500, method="cash")
    with pytest.raises(services.DonationError):
        services.render_acknowledgement(donation)
    settings.DEBUG = True
    assert AcknowledgementTemplate.current() == template


def test_unsent_acknowledgement_emails_are_forgotten(settings):
    donation = Donation.objects.create(amount_cents=2500, method="cash")
    ack = Acknowledgement.objects.create(donation=donation, email="late@private.example")
    Acknowledgement.objects.filter(pk=ack.pk).update(created_at=timezone.now() - timedelta(days=31))
    old = DonationCheckout.objects.create(amount_cents=1000, acknowledgement_email="x@y.example")
    DonationCheckout.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=8))
    assert purge_donation_contacts() == {"checkouts": 1, "emails": 1}
    ack.refresh_from_db()
    assert ack.email == ""


# No public donor data, anywhere


def test_no_api_route_reveals_a_donor(sandbox, signed_in):
    from tests.test_privacy import api_routes

    donor_client, donor = signed_in(display_name="secret_donor_name")
    Donation.objects.create(
        amount_cents=12345, method="cash", donor=donor, donor_display="secret_donor_name"
    )
    Acknowledgement.objects.create(
        donation=Donation.objects.get(), email="secret.donor@private.example"
    )
    other, _ = signed_in(display_name="curious_other")
    secrets_ = ["secret_donor_name", "secret.donor@private.example", "123.45", "12345"]
    for client in (APIClient(), other, donor_client):
        for route, _name in api_routes():
            path = "/" + route
            if "<" in path:
                continue
            body = client.get(path).content.decode()
            for secret in secrets_:
                if secret == "secret_donor_name" and client is donor_client:
                    continue  # the donor's own session names them, as it always has
                assert secret not in body, f"{secret!r} at {path}"
