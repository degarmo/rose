"""The staff section's door desk (/members/staff/door) and its API (/api/staff/door/).

It runs the admin door desk's own code (apps.memberships.desk), so every action here is
also checked against the same action taken through the admin.
"""

import pytest
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import AuditLog
from apps.events.models import RSVP
from apps.memberships import desk
from apps.memberships.models import AgreementSignature, IdCheck, Membership
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
def admin_desk(desk_staff):
    return staff_login(Client(), desk_staff)


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


def log_shape(membership):
    return [
        (entry.action, entry.reason, entry.target_type)
        for entry in door_log().filter(target_ref=membership.reference_code).order_by("pk")
    ]


def admin_post(client, membership, action, **data):
    return client.post(
        reverse("admin:memberships_door_desk"),
        {"action": action, "membership": membership.pk, "q": membership.reference_code, **data},
    )


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


# Same results as the admin's door desk


def test_activate_matches_the_admin(door, admin_desk, joining, desk_staff):
    by_api, by_admin = joining("api_heron"), joining("admin_heron")
    fields = {"method": "cash", "amount": "30.00", "id_checked": "on", "note": "At the door"}
    response = door.post(URL, {"action": "activate", "membership": by_api.pk, **fields})
    assert response.json() == {"message": f"{by_api.reference_code} is active."}
    admin_post(admin_desk, by_admin, "activate", **fields)
    for membership in (by_api, by_admin):
        membership.refresh_from_db()
    assert by_api.status == by_admin.status == "active"
    assert by_api.current_period_end.date() == by_admin.current_period_end.date()
    payments = [m.payments.get() for m in (by_api, by_admin)]
    assert {(p.amount_cents, p.method, p.recorded_by_id, p.note) for p in payments} == {
        (3000, "cash", desk_staff.pk, "At the door")
    }
    checks = IdCheck.objects.filter(membership__in=[by_api, by_admin])
    assert checks.count() == 2 and all(c.checked_by == desk_staff for c in checks)
    assert log_shape(by_api) == log_shape(by_admin) != []


def test_comp_suspend_reinstate_and_renew_match_the_admin(
    door, admin_desk, make_membership, desk_staff
):
    by_api, by_admin = make_membership(), make_membership()
    for action, extra in (
        ("suspend", {"reason": "Asked to step back"}),
        ("reinstate", {"reason": "Talked it through"}),
        ("renew", {"method": "cash", "amount": "25.00"}),
    ):
        assert (
            door.post(URL, {"action": action, "membership": by_api.pk, **extra}).status_code == 200
        )
        admin_post(admin_desk, by_admin, action, **extra)
        by_api.refresh_from_db()
        by_admin.refresh_from_db()
        assert by_api.status == by_admin.status, action
    assert by_api.current_period_end.date() == by_admin.current_period_end.date()
    assert by_api.payments.count() == by_admin.payments.count() == 1
    assert log_shape(by_api) == log_shape(by_admin)
    assert [action for action, _reason, _type in log_shape(by_api)] == [
        "suspend",
        "reinstate",
        "renew",
    ]


def test_check_in_tonight_matches_the_admin(door, admin_desk, make_membership, make_event):
    event = make_event(audience="members", starts_at=timezone.now())
    by_api, by_admin = make_membership(), make_membership()
    data = door.get(URL, {"q": by_api.reference_code}).json()
    assert [e["id"] for e in data["tonight_events"]] == [event.pk]
    assert "walk_in" in data["results"][0]["actions"]
    response = door.post(
        URL, {"action": "walk_in", "membership": by_api.pk, "event": event.pk, "party_size": 1}
    )
    assert response.json() == {"message": f"{by_api.reference_code} is checked in."}
    admin_post(admin_desk, by_admin, "walk_in", event=event.pk, party_size=1)
    rsvps = RSVP.objects.filter(event=event)
    assert {(r.user_id, r.status, r.party_size, r.checked_in) for r in rsvps} == {
        (by_api.user_id, "going", 1, True),
        (by_admin.user_id, "going", 1, True),
    }
    assert log_shape(by_api) == log_shape(by_admin) != []
    assert event.title not in str(log_shape(by_api))


def test_donation_and_refund_through_the_api(door, make_membership, desk_staff):
    from apps.donations.models import Donation

    response = door.post(URL, {"action": "record_donation", "method": "cash", "amount": "12.50"})
    assert response.status_code == 200
    assert Donation.objects.get().amount_cents == 1250
    membership = make_membership()
    door.post(
        URL, {"action": "renew", "membership": membership.pk, "method": "cash", "amount": "25"}
    )
    payment = membership.payments.get()
    card = door.get(URL, {"q": membership.reference_code}).json()["results"][0]
    assert card["payments"][0] == {
        **card["payments"][0],
        "id": payment.pk,
        "amount": "25.00",
        "refundable": True,
    }
    response = door.post(URL, {"action": "refund", "payment": payment.pk, "amount": "5.00"})
    assert response.json() == {"message": "Refund recorded."}
    assert membership.payments.filter(refund_of=payment).get().amount_cents == 500


# The session and the page


def test_session_tells_the_app_about_door_volunteers(desk_staff, settings):
    client = staff_login(APIClient(), desk_staff)
    staff = client.get("/api/account/session/").json()["user"]["staff"]
    assert staff["role"] is None and staff["door_desk"] is True and staff["verified"] is True
    assert staff["door_desk_url"].endswith(reverse("admin:memberships_door_desk"))


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
    assert staff["door_desk_url"] is None
    owner = (
        staff_login(APIClient(), admin_user).get("/api/account/session/").json()["user"]["staff"]
    )
    assert owner["door_desk"] is True


def test_camera_is_allowed_only_on_the_door_pages(client):
    for path in ("/members/staff/door", "/members/staff/door/"):
        assert "camera=(self)" in client.get(path)["Permissions-Policy"]
    for path in ("/members/staff", "/members/staff/reports", URL, "/members/feed"):
        assert "camera=()" in client.get(path)["Permissions-Policy"]


def test_admin_door_desk_links_to_the_tablet_version(admin_desk):
    html = admin_desk.get(reverse("admin:memberships_door_desk")).content.decode()
    assert "/members/staff/door" in html and "Open the tablet door desk" in html
