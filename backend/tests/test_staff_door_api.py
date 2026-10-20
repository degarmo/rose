"""The staff section's door desk (/members/staff/door) and its API (/api/staff/door/).

It is the only door desk: it runs apps.memberships.desk, and every action that service
knows is tested here through the API.
"""

import pytest
from django.contrib.auth.models import Permission
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import AuditLog
from apps.events.models import RSVP
from apps.memberships import desk
from apps.memberships.models import AgreementSignature, IdCheck, Membership, Payment
from tests.conftest import PASSWORD, csrf_client_for, staff_login

pytestmark = pytest.mark.django_db
URL = "/api/staff/door/"
TYPED = "Morgan Legalname"


def api_for(user):
    client = APIClient(enforce_csrf_checks=True)
    client.default_format = "json"  # as the member app sends it
    staff_login(client, user)
    return csrf_client_for(client)


@pytest.fixture
def door(desk_staff):
    return api_for(desk_staff)


@pytest.fixture
def joining(make_user, make_tier, agreement):
    """Two people who signed up for the same tier and are waiting at the door."""
    tier = make_tier(price_cents=3000)

    def make(name):
        user = make_user(display_name=name)
        AgreementSignature.objects.create(user=user, agreement=agreement, typed_name=TYPED)
        return Membership.objects.create(user=user, tier=tier)

    return make


def door_log():
    return AuditLog.objects.filter(category=AuditLog.Category.DOOR_DESK)


# Who gets in: the same 404 as an unknown address for everyone else


def test_anonymous_and_members_get_404(client, make_user):
    assert APIClient().get(URL).status_code == 404
    member = APIClient()
    member.force_login(make_user())
    assert member.get(URL).status_code == 404
    assert member.post(URL, {"action": "show_signature"}).status_code == 404


def test_staff_without_the_desk_permission_get_404(django_user_model):
    staff = django_user_model.objects.create_user(
        email="s@example.org", display_name="plain_staff", password=PASSWORD, is_staff=True
    )
    assert api_for(staff).get(URL).status_code == 404


def test_desk_permission_without_staff_flag_gets_404(make_user):
    user = make_user()
    user.user_permissions.add(Permission.objects.get(codename="change_membership"))
    client = APIClient()
    client.force_login(user)
    assert client.get(URL).status_code == 404


def test_the_two_step_login_is_needed(desk_staff):
    desk_staff.refresh_from_db()
    client = APIClient()
    client.force_login(desk_staff)
    assert client.get(URL).status_code == 404


def test_writes_need_the_csrf_token(desk_staff, joining):
    membership = joining("quiet_heron")
    client = APIClient(enforce_csrf_checks=True)
    staff_login(client, desk_staff)
    response = client.post(URL, {"action": "show_signature", "membership": membership.pk})
    assert response.status_code == 403
    assert not door_log().exists()


# Search


def test_search_payload(door, joining):
    membership = joining("quiet_heron")
    data = door.get(URL, {"q": membership.reference_code.replace("-", "").lower()}).json()
    [card] = data["results"]
    assert card["reference_code"] == membership.reference_code
    assert card["display_name"] == "quiet_heron"
    assert card["status"] == "pending_payment" and card["id_checked"] is False
    assert card["tier"]["price"] == "30.00"
    assert "activate" in card["actions"] and "walk_in" not in card["actions"]
    assert card["do_not_admit"] is False and card["payments"] == []
    assert data["join_url"] is None
    assert [m["value"] for m in data["donation_methods"]] == [v for v, _ in desk.DONATION_METHODS]
    body = str(data)
    assert TYPED not in body and membership.user.email not in body


def test_search_by_display_name_and_nothing_found(door, joining):
    joining("quiet_heron")
    assert len(door.get(URL, {"q": "heron"}).json()["results"]) == 1
    data = door.get(URL, {"q": "nobody"}).json()
    assert data["results"] == [] and data["tonight_events"] == []


def test_signature_reveal_is_logged(door, joining, desk_staff):
    membership = joining("quiet_heron")
    response = door.post(URL, {"action": "show_signature", "membership": membership.pk})
    assert response.json() == {"signature": {"membership": membership.pk, "name": TYPED}}
    entry = door_log().get(action="show_signature_name")
    assert entry.actor == desk_staff and entry.target_ref == membership.reference_code
    assert TYPED not in entry.reason and TYPED not in entry.target_label


def test_refused_actions_answer_400_and_change_nothing(door, joining):
    membership = joining("quiet_heron")
    response = door.post(
        URL, {"action": "activate", "membership": membership.pk, "method": "cash", "amount": "30"}
    )
    assert response.status_code == 400 and response.json()["detail"]
    membership.refresh_from_db()
    assert membership.status == "pending_payment" and not membership.payments.exists()
    assert door.post(URL, {"action": "nonsense"}).status_code == 400
    assert not door_log().exists()


# Every door desk action, at the one door desk


@pytest.fixture
def scenario(joining, make_membership, make_tier, make_event, make_user):
    """For each desk action: what to send, and how to tell it worked."""

    def build(action):
        from apps.donations.models import Donation

        if action == "record_donation":
            payload = {"method": "cash", "amount": "12.50"}
            return payload, lambda: Donation.objects.get().amount_cents == 1250
        if action == "refund":
            membership = make_membership()
            paid = Payment.objects.create(membership=membership, amount_cents=2500, method="cash")
            payload = {"payment": paid.pk, "amount": "10.00"}
            return payload, lambda: Payment.objects.filter(refund_of=paid).exists()
        if action == "guest_visit":
            guest = make_membership(
                tier=make_tier(is_guest_pass=True, price_cents=1500),
                status="pending_payment",
                id_check=False,
            )
            payload = {"membership": guest.pk, "method": "cash", "amount": "15", "id_checked": True}
            return payload, lambda: Membership.objects.get(pk=guest.pk).status == "active"
        if action in ("activate", "activate_paid", "show_signature", "verify", "comp"):
            membership = joining(f"to_{action}")
            if action == "activate_paid":
                membership.paid_awaiting_id_check = True
                membership.save()
            extra = {
                "activate": {"method": "cash", "amount": "30", "id_checked": True},
                "activate_paid": {"id_checked": True},
                "show_signature": {},
                "verify": {"id_checked": True},
                "comp": {"reason": "Volunteer thanks", "id_checked": True},
            }[action]

            def worked():
                fresh = Membership.objects.get(pk=membership.pk)
                if action == "show_signature":
                    return door_log().filter(action="show_signature_name").exists()
                if action == "verify":
                    return IdCheck.valid().filter(user=fresh.user).exists()
                return fresh.status == "active"

            return {"membership": membership.pk, **extra}, worked
        if action == "walk_in":
            event = make_event(audience="members", starts_at=timezone.now())
            membership = make_membership()
            payload = {"membership": membership.pk, "event": event.pk, "party_size": 1}
            return payload, lambda: RSVP.objects.filter(event=event, checked_in=True).exists()
        status = "suspended" if action == "reinstate" else "active"
        membership = make_membership(status=status)
        extra = {
            "renew": {"method": "cash", "amount": "25"},
            "suspend": {"reason": "Asked to step back"},
            "reinstate": {"reason": "Talked it through"},
            "revoke": {"reason": "Checked the wrong person"},
        }[action]
        expected = {
            "renew": lambda m: m.payments.count() == 1,
            "suspend": lambda m: m.status == "suspended",
            "reinstate": lambda m: m.status == "active",
            "revoke": lambda m: not IdCheck.valid().filter(user=m.user).exists(),
        }[action]
        return (
            {"membership": membership.pk, **extra},
            lambda: expected(Membership.objects.get(pk=membership.pk)),
        )

    return build


@pytest.mark.parametrize("action", desk.ACTIONS)
def test_the_staff_door_desk_does_every_desk_action(action, door, scenario):
    """Everything the admin's door desk did is here, through the same service and log."""
    payload, worked = scenario(action)
    before = door_log().count()
    response = door.post(URL, {"action": action, **payload})
    assert response.status_code == 200, (action, response.json())
    assert worked(), action
    assert door_log().count() > before or action == "record_donation", action


def test_the_staff_door_desk_offers_every_action_in_its_cards(door, joining):
    """Every action the service knows is reachable from a card or the page itself."""
    from pathlib import Path

    page = (
        Path(__file__).resolve().parents[2] / "frontend/src/pages/members/staff/StaffDoorPage.tsx"
    ).read_text()
    for action in desk.ACTIONS:
        assert f"'{action}'" in page or f"{action}:" in page, action


# The session and the page


def test_session_tells_the_app_about_door_volunteers(desk_staff, settings):
    client = staff_login(APIClient(), desk_staff)
    staff = client.get("/api/account/session/").json()["user"]["staff"]
    assert staff["role"] is None and staff["door_desk"] is True and staff["verified"] is True
    assert "door_desk_url" not in staff


def test_unverified_volunteer_comes_back_to_the_door_after_signing_in(desk_staff, settings):
    desk_staff.refresh_from_db()  # the current session epoch
    client = APIClient()
    client.force_login(desk_staff)
    staff = client.get("/api/account/session/").json()["user"]["staff"]
    assert staff["verified"] is False
    assert "members%2Fstaff%2Fdoor" in staff["verify_url"]


def test_team_without_the_desk_permission_has_no_door_desk(admin_user, django_user_model):
    from apps.safety import roles

    moderator = django_user_model.objects.create_user(
        email="m@example.org", display_name="mod", password=PASSWORD
    )
    roles.set_role(moderator, roles.MODERATOR)
    staff = staff_login(APIClient(), moderator).get("/api/account/session/").json()["user"]["staff"]
    assert staff["role"] == "moderator" and staff["door_desk"] is False
    owner = (
        staff_login(APIClient(), admin_user).get("/api/account/session/").json()["user"]["staff"]
    )
    assert owner["door_desk"] is True


def test_camera_is_allowed_only_on_the_door_pages(client):
    for path in ("/members/staff/door", "/members/staff/door/"):
        assert "camera=(self)" in client.get(path)["Permissions-Policy"]
    for path in ("/members/staff", "/members/staff/reports", URL, "/members/feed"):
        assert "camera=()" in client.get(path)["Permissions-Policy"]
