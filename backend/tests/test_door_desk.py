"""The door desk: find, check ID, take payment, and log every action."""

from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from apps.core.models import AuditLog
from apps.memberships import desk
from apps.memberships.models import AgreementSignature, IdCheck, Membership, Payment

pytestmark = pytest.mark.django_db
TYPED = "Morgan Legalname"


@pytest.fixture
def desk_client(client, desk_staff):
    client.force_login(desk_staff)
    return client


@pytest.fixture
def joined(make_user, make_tier, agreement):
    user = make_user(display_name="quiet_heron")
    AgreementSignature.objects.create(user=user, agreement=agreement, typed_name=TYPED)
    return Membership.objects.create(user=user, tier=make_tier(price_cents=3000))


def desk_url():
    return reverse("admin:memberships_door_desk")


def act(client, membership, action, **data):
    return client.post(
        desk_url(),
        {"action": action, "membership": membership.pk, "q": membership.reference_code, **data},
    )


def door_log(action):
    return AuditLog.objects.filter(category=AuditLog.Category.DOOR_DESK, action=action)


# Finding people


def test_search_by_code_with_or_without_dash(desk_client, joined):
    code = joined.reference_code
    for query in (code, code.replace("-", ""), code.lower()):
        page = desk_client.get(desk_url(), {"q": query}).content.decode()
        assert "quiet_heron" in page and code in page


def test_search_by_display_name(desk_client, joined):
    page = desk_client.get(desk_url(), {"q": "heron"}).content.decode()
    assert joined.reference_code in page


def test_search_never_shows_the_typed_name_or_email(desk_client, joined):
    page = desk_client.get(desk_url(), {"q": joined.reference_code}).content.decode()
    assert TYPED not in page
    assert joined.user.email not in page
    assert "Show signature name" in page


def test_show_signature_name_is_logged(desk_client, joined, desk_staff):
    response = act(desk_client, joined, "show_signature")
    assert response.status_code == 200
    assert TYPED in response.content.decode()
    entry = door_log("show_signature_name").get()
    assert entry.actor == desk_staff and entry.target_ref == joined.reference_code
    assert TYPED not in entry.reason and TYPED not in entry.target_label


def test_desk_allows_the_camera_only_there(desk_client, joined):
    assert "camera=(self)" in desk_client.get(desk_url())["Permissions-Policy"]
    assert "camera=()" in desk_client.get(reverse("admin:index"))["Permissions-Policy"]


def test_desk_needs_permission(client, django_user_model):
    plain_staff = django_user_model.objects.create_user(
        email="s@example.org", display_name="plain_staff", password="pw-123456789", is_staff=True
    )
    client.force_login(plain_staff)
    assert client.get(desk_url()).status_code == 403


# Actions


def test_first_activation_needs_the_id_checkbox(desk_client, joined):
    act(desk_client, joined, "activate", method="cash", amount="30.00")
    joined.refresh_from_db()
    assert joined.status == "pending_payment"
    assert not Payment.objects.exists()
    assert not door_log("activate").exists()


def test_record_payment_and_activate(desk_client, joined, desk_staff):
    act(
        desk_client,
        joined,
        "activate",
        method="cash",
        amount="30.00",
        id_checked="on",
        note="At the door",
    )
    joined.refresh_from_db()
    assert joined.status == "active"
    assert joined.current_period_end > timezone.now() + timedelta(days=29)
    payment = joined.payments.get()
    assert (payment.amount_cents, payment.method, payment.recorded_by) == (3000, "cash", desk_staff)
    check = IdCheck.objects.get()
    assert check.checked_by == desk_staff and check.verified_18_plus
    assert door_log("activate").get().reason == "At the door"


def test_returning_person_needs_no_second_id_check(desk_staff, make_membership, make_tier):
    old = make_membership(status="expired")
    fresh = Membership.objects.create(user=old.user, tier=make_tier())
    desk.record_payment_and_activate(desk_staff, fresh, "card_in_person", 2500)
    fresh.refresh_from_db()
    assert fresh.status == "active"
    assert IdCheck.objects.count() == 1


def test_online_payment_waiting_for_id(desk_client, joined):
    Membership.objects.filter(pk=joined.pk).update(paid_awaiting_id_check=True)
    act(desk_client, joined, "activate_paid")
    joined.refresh_from_db()
    assert joined.status == "pending_payment"
    act(desk_client, joined, "activate_paid", id_checked="on")
    joined.refresh_from_db()
    assert joined.status == "active" and not joined.paid_awaiting_id_check
    assert door_log("activate_after_id_check").exists()


@pytest.mark.parametrize("days_left,expected_from", [(10, "period_end"), (-3, "now")])
def test_renew_extends_from_the_later_of_today_or_period_end(
    days_left, expected_from, desk_staff, make_membership
):
    end = timezone.now() + timedelta(days=days_left)
    status = "active" if days_left > 0 else "grace"
    membership = make_membership(
        status=status, current_period_start=end - timedelta(days=30), current_period_end=end
    )
    before = timezone.now()
    desk.renew(desk_staff, membership, "cash", 2500)
    membership.refresh_from_db()
    base = end if expected_from == "period_end" else before
    assert membership.status == "active"
    assert abs(membership.current_period_end - (base + timedelta(days=30))) < timedelta(minutes=1)
    assert door_log("renew").exists()


def test_comp_needs_a_reason(desk_client, joined):
    act(desk_client, joined, "comp", reason="", id_checked="on")
    joined.refresh_from_db()
    assert joined.status == "pending_payment"
    act(desk_client, joined, "comp", reason="Volunteer of the month", id_checked="on")
    joined.refresh_from_db()
    assert joined.status == "active" and joined.source == "comp"
    assert joined.payments.get().method == "comp"
    assert door_log("comp").get().reason == "Volunteer of the month"


def test_suspend_and_reinstate_need_reasons(desk_staff, make_membership):
    membership = make_membership()
    with pytest.raises(desk.DeskError):
        desk.suspend(desk_staff, membership, "  ")
    desk.suspend(desk_staff, membership, "Asked to step back")
    membership.refresh_from_db()
    assert membership.status == "suspended"
    with pytest.raises(desk.DeskError):
        desk.reinstate(desk_staff, membership, "")
    desk.reinstate(desk_staff, membership, "Spoke with the board")
    membership.refresh_from_db()
    assert membership.status == "active"
    assert [e.action for e in AuditLog.objects.order_by("created_at")] == ["suspend", "reinstate"]


def test_refund_is_a_new_row(desk_client, desk_staff, make_membership):
    membership = make_membership()
    paid = Payment.objects.create(membership=membership, amount_cents=2500, method="cash")
    response = desk_client.post(
        desk_url(), {"action": "refund", "payment": paid.pk, "amount": "10.00", "q": "x"}
    )
    assert response.status_code == 302
    refund = Payment.objects.get(status="refunded")
    assert (
        refund.refund_of == paid
        and refund.amount_cents == 1000
        and refund.recorded_by == desk_staff
    )
    paid.refresh_from_db()
    assert paid.status == "succeeded" and paid.amount_cents == 2500
    with pytest.raises(desk.DeskError):
        desk.refund(desk_staff, paid, 1600)  # only 15.00 left
    assert door_log("refund").count() == 1


def test_online_refund_calls_the_provider(sandbox, desk_staff, make_membership, monkeypatch):
    from apps.memberships.providers.sandbox import SandboxProvider

    calls = []
    monkeypatch.setattr(
        SandboxProvider, "refund", lambda self, payment, cents: calls.append(cents) or "re_1"
    )
    membership = make_membership(source="provider", provider="sandbox")
    paid = Payment.objects.create(
        membership=membership, amount_cents=2500, method="online", provider_payment_ref="pay_1"
    )
    desk.refund(desk_staff, paid, 2500)
    assert calls == [2500]


def test_actions_refused_in_the_wrong_state(desk_staff, make_membership):
    active = make_membership()
    with pytest.raises(desk.DeskError):
        desk.record_payment_and_activate(desk_staff, active, "cash", 100, id_checked=True)
    with pytest.raises(desk.DeskError):
        desk.reinstate(desk_staff, active, "reason")
    with pytest.raises(desk.DeskError):
        desk.renew(desk_staff, active, "online", 100)


# Payment records are immutable


def test_payment_rows_cannot_change(make_membership):
    payment = Payment.objects.create(membership=make_membership(), amount_cents=2500, method="cash")
    payment.amount_cents = 1
    with pytest.raises(ValidationError):
        payment.save()
    with pytest.raises(ValidationError):
        payment.delete()
    with pytest.raises(ValidationError):
        Payment.objects.filter(pk=payment.pk).update(amount_cents=1)
    with pytest.raises(ValidationError):
        Payment.objects.all().delete()


def test_payment_admin_is_read_only(admin_client, make_membership):
    payment = Payment.objects.create(membership=make_membership(), amount_cents=2500, method="cash")
    base = "admin:memberships_payment"
    assert admin_client.get(reverse(f"{base}_changelist")).status_code == 200
    assert admin_client.get(reverse(f"{base}_add")).status_code == 403
    assert admin_client.get(reverse(f"{base}_delete", args=[payment.pk])).status_code == 403
    page = admin_client.get(reverse(f"{base}_change", args=[payment.pk])).content.decode()
    assert 'name="amount_cents"' not in page and "_save" not in page
    response = admin_client.post(reverse(f"{base}_change", args=[payment.pk]), {"amount_cents": 1})
    assert response.status_code == 403
    payment.refresh_from_db()
    assert payment.amount_cents == 2500


def test_audit_log_admin_is_read_only(admin_client, desk_staff, make_membership):
    desk.suspend(desk_staff, make_membership(), "reason")
    entry = AuditLog.objects.get()
    assert admin_client.get(reverse("admin:core_auditlog_add")).status_code == 403
    assert (
        admin_client.get(reverse("admin:core_auditlog_delete", args=[entry.pk])).status_code == 403
    )


def test_published_agreement_cannot_be_edited(admin_client, agreement):
    page = admin_client.get(
        reverse("admin:memberships_membershipagreement_change", args=[agreement.pk])
    ).content.decode()
    assert 'name="body"' not in page
    assert (
        admin_client.get(
            reverse("admin:memberships_membershipagreement_delete", args=[agreement.pk])
        ).status_code
        == 403
    )
