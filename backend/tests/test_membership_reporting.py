"""Membership summary and the logged CSV export."""

import csv
import io

import pytest
from django.urls import reverse

from apps.core.models import AuditLog
from apps.memberships.models import Payment
from tests.conftest import staff_login

pytestmark = pytest.mark.django_db


@pytest.fixture
def members(make_membership, make_user, make_tier):
    tier = make_tier(name="Monthly")
    active = make_membership(user=make_user(display_name="ada_active"), tier=tier)
    Payment.objects.create(membership=active, amount_cents=2500, method="cash")
    paid = Payment.objects.create(
        membership=active, amount_cents=2500, method="online", provider_payment_ref="p1"
    )
    Payment.objects.create(
        membership=active, amount_cents=500, method="online", status="refunded", refund_of=paid
    )
    make_membership(user=make_user(display_name="=cmd|calc"), tier=tier, status="grace")
    make_membership(status="expired")
    return active


def test_summary_counts_and_revenue(admin_client, members):
    """The same figures and rules as the dashboard (apps.core.metrics): few payments are
    withheld, five or more show their total with refunds subtracted."""
    page = admin_client.get(reverse("admin:memberships_summary")).content.decode()
    assert "Membership summary" in page
    assert "Grace period" in page and "Monthly" in page
    assert "&lt;5" in page and "25.00" not in page
    for _ in range(4):
        Payment.objects.create(membership=members, amount_cents=1000, method="cash")
    page = admin_client.get(reverse("admin:memberships_summary")).content.decode()
    assert "$65" in page  # cash: 25 + 4 x 10
    assert "$85" in page  # the month's total: 65 + 25 online - 5 refunded


def test_summary_needs_view_permission(client, django_user_model):
    staff = django_user_model.objects.create_user(
        email="s@example.org", display_name="no_perms", password="pw-123456789", is_staff=True
    )
    staff_login(client, staff)
    assert client.get(reverse("admin:memberships_summary")).status_code == 403


def rows(response):
    return list(csv.reader(io.StringIO(response.content.decode())))


def test_export_is_logged_and_has_no_emails(client, desk_staff, members):
    staff_login(client, desk_staff)
    response = client.post(reverse("admin:memberships_export"))
    assert response.status_code == 200
    assert "no-store" in response["Cache-Control"]
    data = rows(response)
    assert data[0] == ["Display name", "Tier", "Status", "Period end", "Source"]
    assert len(data) == 4
    assert "@" not in response.content.decode()
    assert "'=cmd|calc" in [r[0] for r in data]  # spreadsheet formulas are neutralised
    entry = AuditLog.objects.get(category="export")
    assert entry.action == "membership_csv" and entry.actor == desk_staff


def test_only_superusers_can_include_email_and_it_is_logged(
    client, desk_staff, admin_client, members
):
    staff_login(client, desk_staff)
    assert (
        client.post(reverse("admin:memberships_export"), {"include_email": "on"}).status_code == 403
    )
    assert not AuditLog.objects.exists()

    response = admin_client.post(reverse("admin:memberships_export"), {"include_email": "on"})
    assert rows(response)[0][-1] == "Email"
    assert members.user.email in response.content.decode()
    entry = AuditLog.objects.get(category="export")
    assert entry.action == "membership_csv_with_email" and entry.reason == "Included contact email"


def test_export_is_post_only(admin_client):
    assert admin_client.get(reverse("admin:memberships_export")).status_code == 403
