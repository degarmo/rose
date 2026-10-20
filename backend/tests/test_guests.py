"""Guests: a one-night pass on the existing tier and join flow, run at the door desk."""

from datetime import timedelta

import pytest
from django.core import mail
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from apps.core.models import AuditLog
from apps.memberships import desk, lifecycle
from apps.memberships.models import IdCheck, Membership, Payment, Tier
from tests.conftest import staff_login

pytestmark = pytest.mark.django_db


@pytest.fixture
def guest_tier(make_tier):
    return make_tier(
        name="Guest night pass",
        slug="guest-night",
        price_cents=1500,
        interval=Tier.Interval.ONCE,
        duration_days=1,
        grants_feed_access=False,
        grants_members_events=False,
        grants_members_education=False,
        is_guest_pass=True,
    )


@pytest.fixture
def desk_client(client, desk_staff):
    staff_login(client, desk_staff)
    return client


def join_as_guest(client, tier, agreement, method="manual"):
    return client.post(
        "/api/membership/join/",
        {
            "tier": tier.slug,
            "agreement_version": agreement.version,
            "typed_name": "Casey Guestperson",
            "method": method,
        },
        format="json",
    )


def guest_visit(client, membership, **extra):
    return client.post(
        reverse("admin:memberships_door_desk"),
        {
            "action": "guest_visit",
            "membership": membership.pk,
            "q": membership.reference_code,
            "method": "cash",
            "amount": "15.00",
            **extra,
        },
    )


def test_a_guest_pass_must_be_one_day_with_no_online_access(make_tier):
    tier = Tier(name="Guest", slug="g", price_cents=1500, interval="month", is_guest_pass=True)
    with pytest.raises(ValidationError):
        tier.full_clean()
    tier.interval, tier.duration_days = "once", 1
    with pytest.raises(ValidationError):
        tier.full_clean()  # still grants the member community and members' events
    tier.grants_feed_access = tier.grants_members_events = tier.grants_members_education = False
    tier.full_clean()


def test_tiers_endpoint_flags_the_guest_pass(api_client, guest_tier, make_tier):
    make_tier(slug="monthly")
    tiers = {t["slug"]: t for t in api_client.get("/api/membership/tiers/").json()}
    assert tiers["guest-night"]["is_guest_pass"] is True
    assert tiers["monthly"]["is_guest_pass"] is False


def test_guest_passes_are_paid_at_the_door_only(sandbox, signed_in, guest_tier, agreement):
    client, _ = signed_in()
    response = join_as_guest(client, guest_tier, agreement, method="sandbox")
    assert response.status_code == 400
    assert response.json()["code"] == "method"


def test_guest_flow_end_to_end_through_the_door_desk(
    signed_in, guest_tier, agreement, desk_client, desk_staff
):
    """Sign up as a guest, get a code, ID checked and paid at the door, in for one night,
    then the pass simply ends; a second visit reuses the account, code and ID check."""
    client, user = signed_in(display_name="first_timer")
    response = join_as_guest(client, guest_tier, agreement)
    assert response.status_code == 201
    membership = Membership.objects.get(user=user)
    assert membership.status == "pending_payment" and membership.tier.is_guest_pass
    assert [m.subject for m in mail.outbox] == ["Your reference code"]

    # The desk shows a guest pass, with Guest visit instead of membership actions.
    page = desk_client.get(
        reverse("admin:memberships_door_desk"), {"q": membership.reference_code}
    ).content.decode()
    assert "Guest pass" in page and "Guest visit" in page and "Convert to member" in page
    assert "Record payment and activate" not in page

    # No ID check yet: refused until the box is ticked.
    guest_visit(desk_client, membership)
    membership.refresh_from_db()
    assert membership.status == "pending_payment"
    guest_visit(desk_client, membership, id_checked="on")
    membership.refresh_from_db()
    assert membership.status == "active"
    assert membership.current_period_end - membership.current_period_start == timedelta(days=1)
    assert IdCheck.objects.filter(membership=membership).count() == 1
    assert Payment.objects.get(membership=membership).amount_cents == 1500
    entry = AuditLog.objects.get(category=AuditLog.Category.DOOR_DESK, action="guest_visit")
    assert entry.actor == desk_staff and entry.target_ref == membership.reference_code

    # The next day the pass ends: no grace period and no email.
    mail.outbox.clear()
    counts = lifecycle.run(now=timezone.now() + timedelta(days=2))
    membership.refresh_from_db()
    assert membership.status == "expired" and counts["guest_passes_ended"] == 1
    assert mail.outbox == []

    # A returning guest: same account and code, and no second ID check needed.
    guest_visit(desk_client, membership)
    membership.refresh_from_db()
    assert membership.status == "active"
    assert IdCheck.objects.filter(membership__user=user).count() == 1
    assert Payment.objects.filter(membership=membership).count() == 2


def test_a_running_guest_pass_cannot_be_opened_twice(make_membership, guest_tier, desk_staff):
    membership = make_membership(tier=guest_tier, status="active")
    with pytest.raises(desk.DeskError, match="already open"):
        desk.guest_visit(desk_staff, membership, "cash", 1500)


def test_membership_actions_refuse_a_guest_pass(make_membership, guest_tier, desk_staff):
    membership = make_membership(tier=guest_tier, status="pending_payment", id_check=True)
    with pytest.raises(desk.DeskError, match="Guest visit"):
        desk.record_payment_and_activate(desk_staff, membership, "cash", 1500)
    with pytest.raises(desk.DeskError, match="Guest visit"):
        desk.comp(desk_staff, membership, "friend of the house")


def test_guest_visit_refuses_a_membership(make_membership, desk_staff):
    membership = make_membership(status="pending_payment", id_check=True)
    with pytest.raises(desk.DeskError, match="not a guest pass"):
        desk.guest_visit(desk_staff, membership, "cash", 1500)


def test_converting_to_a_member_replaces_the_guest_pass(
    signed_in, guest_tier, make_tier, agreement, desk_staff
):
    client, user = signed_in()
    join_as_guest(client, guest_tier, agreement)
    guest = Membership.objects.get(user=user)
    desk.guest_visit(desk_staff, guest, "cash", 1500, id_checked=True)
    monthly = make_tier(slug="monthly")
    response = client.post(
        "/api/membership/join/",
        {
            "tier": monthly.slug,
            "agreement_version": agreement.version,
            "typed_name": "Casey Guestperson",
            "method": "manual",
        },
        format="json",
    )
    assert response.status_code == 201
    guest.refresh_from_db()
    assert guest.status == "expired"
    member = Membership.objects.non_terminal().get(user=user)
    assert member.tier == monthly
    # The ID check carries over: activation needs no new one.
    desk.record_payment_and_activate(desk_staff, member, "cash", 2500)
    member.refresh_from_db()
    assert member.status == "active"


def test_a_member_cannot_buy_a_guest_pass(signed_in, guest_tier, make_membership, agreement):
    client, user = signed_in()
    make_membership(user=user)
    response = join_as_guest(client, guest_tier, agreement)
    assert response.status_code == 409


def test_guest_passes_get_no_renewal_reminders(make_membership, guest_tier):
    make_membership(tier=guest_tier, status="active", current_period_end=timezone.now())
    Membership.objects.update(current_period_end=timezone.now() + timedelta(hours=12))
    counts = lifecycle.run()
    assert counts["reminders"] == 0
    assert mail.outbox == []


def test_summary_counts_guest_visits_by_month(admin_client, make_membership, guest_tier):
    membership = make_membership(tier=guest_tier, status="expired", id_check=True)
    for _ in range(3):
        Payment.objects.create(membership=membership, amount_cents=1500, method="cash")
    page = admin_client.get(reverse("admin:memberships_summary")).content.decode()
    month = timezone.localtime().strftime("%b %Y")
    assert "Guest visits, last 12 months" in page
    assert f'<tr><th scope="row">{month}</th><td class="rose-num">3</td></tr>' in page
