"""Settings in the member app: the old /account addresses, preferences that change what is
sent, where you are signed in, the member two-step login, mutes, pronouns and the data
export for every account. A plain account never reaches anything in the feed."""

import json
import time
import zipfile
from datetime import timedelta
from io import BytesIO

import pytest
from django.core import mail
from django.utils import timezone
from django_otp.oath import totp
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.test import APIClient

from apps.accounts.models import AccountSession
from apps.events.models import RSVP
from apps.events.services import submit_rsvp
from apps.events.tasks import send_due_reminders
from apps.feed import services
from apps.feed import tasks as feed_tasks
from apps.feed.models import Notification
from apps.memberships import lifecycle
from tests.conftest import PASSWORD, csrf_client_for

pytestmark = pytest.mark.django_db


def login(user, agent="Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Safari/604.1"):
    client = csrf_client_for(APIClient(enforce_csrf_checks=True, HTTP_USER_AGENT=agent))
    response = client.post(
        "/api/account/login/", {"email": user.email, "password": PASSWORD}, format="json"
    )
    assert response.status_code == 200
    return csrf_client_for(client), response.json()


def code_for(device, offset=0):
    value = totp(device.bin_key, device.step, device.t0, device.digits, device.drift + offset)
    return f"{value:06d}"


# The old account addresses


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("/account", "/members/settings"),
        ("/account/", "/members/settings"),
        ("/account/notices", "/members/settings/guidelines"),
        ("/account/export", "/members/settings/privacy/export"),
        ("/account/receipts/41", "/members/settings/membership/receipts/41"),
    ],
)
def test_every_old_account_address_moves_for_good(client, old, new):
    response = client.get(old)
    assert (response.status_code, response["Location"]) == (301, new)


@pytest.mark.parametrize(
    "path", ["/account/login", "/account/register", "/account/forgot", "/account/verify"]
)
def test_the_sign_in_pages_stay_put(client, path):
    assert client.get(path).status_code == 200


# Preferences


def test_preferences_are_your_own_and_discreet_subjects_stay_on(signed_in):
    client, user = signed_in()
    data = client.get("/api/account/preferences/").json()
    assert data == {
        "pronouns": "",
        "calendar_details": False,
        "email_event_reminders": True,
        "email_membership_reminders": True,
        "notify_likes": True,
        "notify_comments": True,
        "discreet_subjects": True,
    }
    response = client.patch(
        "/api/account/preferences/",
        {"pronouns": "  they /  them ", "calendar_details": True, "discreet_subjects": False},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["pronouns"] == "they / them"
    assert response.json()["discreet_subjects"] is True
    user.profile.refresh_from_db()
    assert user.profile.calendar_details
    assert client.get("/api/account/session/").json()["user"]["calendar_details"] is True


def test_preferences_need_a_sign_in(csrf_client):
    assert csrf_client.get("/api/account/preferences/").status_code == 403


def test_event_reminders_follow_the_switch(make_event, make_user):
    soon = make_event(starts_at=timezone.now() + timedelta(hours=20))
    quiet = make_user(email="quiet@example.org")
    quiet.profile.email_event_reminders = False
    quiet.profile.save()
    rsvps = [
        submit_rsvp(user, soon, 1).rsvp for user in (quiet, make_user(email="loud@example.org"))
    ]
    RSVP.objects.filter(pk__in=[r.pk for r in rsvps]).update(
        created_at=timezone.now() - timedelta(days=2)
    )
    mail.outbox.clear()
    assert send_due_reminders() == 2
    assert [m.to for m in mail.outbox] == [["loud@example.org"]]
    # Handled, so it is not sent later either.
    assert send_due_reminders() == 0


def test_membership_reminders_follow_the_switch(make_membership, make_user):
    end = timezone.now() + timedelta(days=13)
    quiet = make_user()
    quiet.profile.email_membership_reminders = False
    quiet.profile.save()
    make_membership(
        user=quiet, current_period_start=end - timedelta(days=30), current_period_end=end
    )
    mail.outbox.clear()
    lifecycle.run()
    assert mail.outbox == []
    make_membership(current_period_start=end - timedelta(days=30), current_period_end=end)
    lifecycle.run()
    assert len(mail.outbox) == 1


def test_like_and_comment_notifications_follow_the_switches(make_member, make_post):
    author, fan = make_member(), make_member()
    post = make_post(author)
    author.profile.notify_likes = False
    author.profile.save()
    services.like(fan, post.public_id)
    services.add_comment(fan, post.public_id, "lovely")
    assert list(Notification.objects.filter(recipient=author).values_list("kind", flat=True)) == [
        Notification.Kind.COMMENT
    ]
    author.profile.notify_comments = False
    author.profile.save()
    services.add_comment(fan, post.public_id, "again")
    assert Notification.objects.filter(recipient=author).count() == 1


# Where you are signed in


def test_sessions_list_marks_this_device_and_logout_removes_it(make_user):
    user = make_user()
    phone, _ = login(user)
    laptop, _ = login(user, agent="Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko Firefox/131.0")
    rows = phone.get("/api/account/sessions/").json()
    assert len(rows) == 2
    assert {row["device"] for row in rows} == {"Safari on iPhone", "Firefox on Linux"}
    assert [row["current"] for row in rows].count(True) == 1
    assert next(row for row in rows if row["current"])["device"] == "Safari on iPhone"
    # Nothing in the list identifies the browser beyond that label.
    assert set(rows[0]) == {"device", "signed_in_at", "last_seen_at", "current", "active_now"}
    laptop.post("/api/account/logout/")
    assert len(phone.get("/api/account/sessions/").json()) == 1


def test_password_change_and_sign_out_everywhere_clear_other_sessions(make_user):
    user = make_user()
    phone, _ = login(user)
    login(user, agent="Firefox")
    response = phone.post(
        "/api/account/password/",
        {"current_password": PASSWORD, "new_password": "another-long-password-456"},
        format="json",
    )
    assert response.status_code == 200
    assert AccountSession.objects.filter(user=user).count() == 1
    phone = csrf_client_for(phone)
    phone.post("/api/account/sign-out-everywhere/")
    assert not AccountSession.objects.filter(user=user).exists()


def test_old_sign_ins_are_forgotten_daily(make_user, settings):
    from apps.accounts.tasks import purge_stale_sessions

    user = make_user()
    login(user)
    login(user, agent="Firefox")
    old = timezone.now() - timedelta(seconds=settings.SESSION_COOKIE_AGE + 60)
    AccountSession.objects.exclude(device="Safari on iPhone").update(last_seen_at=old)
    assert purge_stale_sessions() == 1
    assert AccountSession.objects.filter(user=user).count() == 1
    assert "purge-stale-sessions" in settings.CELERY_BEAT_SCHEDULE


# Two-step login for members


def enrol(client):
    assert client.post("/api/account/two-step/setup/").status_code == 200
    device = TOTPDevice.objects.get(confirmed=False)
    response = client.post(
        "/api/account/two-step/confirm/", {"code": code_for(device)}, format="json"
    )
    assert response.status_code == 200
    return device, response.json()["backup_codes"]


def test_members_can_turn_on_two_step_login_and_then_need_the_code(make_user, settings):
    settings.OTP_TOTP_THROTTLE_FACTOR = 0
    user = make_user()
    client, _ = login(user)
    assert client.get("/api/account/two-step/").json() == {
        "enabled": False,
        "backup_codes_left": 0,
        "required": False,
    }
    setup = client.post("/api/account/two-step/setup/").json()
    assert setup["qr"].startswith("data:image/") and len(setup["secret"].replace(" ", "")) >= 16
    device = TOTPDevice.objects.get(user=user, confirmed=False)
    bad = client.post("/api/account/two-step/confirm/", {"code": "000000"}, format="json")
    assert bad.status_code == 400
    good = client.post("/api/account/two-step/confirm/", {"code": code_for(device)}, format="json")
    assert good.json()["enabled"] and len(good.json()["backup_codes"]) == 10

    # Signing in now stops after the password; nobody is signed in yet.
    fresh = csrf_client_for(APIClient(enforce_csrf_checks=True))
    first = fresh.post(
        "/api/account/login/", {"email": user.email, "password": PASSWORD}, format="json"
    ).json()
    assert first["two_step"] is True and first["user"] is None
    fresh = csrf_client_for(fresh)
    assert fresh.get("/api/account/preferences/").status_code == 403
    wrong = fresh.post("/api/account/login/two-step/", {"code": "123"}, format="json")
    assert wrong.status_code == 400
    right = fresh.post(
        "/api/account/login/two-step/", {"code": code_for(device, offset=1)}, format="json"
    )
    assert right.status_code == 200 and right.json()["user"]["display_name"] == user.display_name


def test_a_backup_code_signs_in_once(make_user):
    user = make_user()
    client, _ = login(user)
    _, codes = enrol(client)
    for expected in (200, 400):
        fresh = csrf_client_for(APIClient(enforce_csrf_checks=True))
        fresh.post(
            "/api/account/login/", {"email": user.email, "password": PASSWORD}, format="json"
        )
        fresh = csrf_client_for(fresh)
        response = fresh.post("/api/account/login/two-step/", {"code": codes[0]}, format="json")
        assert response.status_code == expected


def test_the_code_step_times_out(make_user, monkeypatch):
    user = make_user()
    client, _ = login(user)
    device, _ = enrol(client)
    fresh = csrf_client_for(APIClient(enforce_csrf_checks=True))
    fresh.post("/api/account/login/", {"email": user.email, "password": PASSWORD}, format="json")
    fresh = csrf_client_for(fresh)
    later = time.time() + 301
    monkeypatch.setattr("apps.accounts.views.time.time", lambda: later)
    response = fresh.post(
        "/api/account/login/two-step/", {"code": code_for(device, offset=1)}, format="json"
    )
    assert response.status_code == 400 and "timed out" in response.json()["detail"]


def test_turning_it_off_needs_the_password_and_staff_keep_it(make_user):
    user = make_user()
    client, _ = login(user)
    enrol(client)
    wrong = client.post("/api/account/two-step/disable/", {"password": "nope"}, format="json")
    assert wrong.status_code == 400
    right = client.post("/api/account/two-step/disable/", {"password": PASSWORD}, format="json")
    assert right.json()["enabled"] is False
    assert not TOTPDevice.objects.filter(user=user).exists()
    assert not StaticDevice.objects.filter(user=user).exists()

    staff = make_user(is_staff=True)
    TOTPDevice.objects.create(user=staff, name="app", confirmed=True)
    staff_client = APIClient(enforce_csrf_checks=True)
    staff_client.force_login(staff)
    staff_client = csrf_client_for(staff_client)
    assert staff_client.get("/api/account/two-step/").json()["required"] is True
    refused = staff_client.post(
        "/api/account/two-step/disable/", {"password": PASSWORD}, format="json"
    )
    assert refused.status_code == 400
    assert TOTPDevice.objects.filter(user=staff).exists()


def test_a_staff_login_with_the_code_is_the_second_step(make_user, settings):
    settings.DEV_SKIP_STAFF_2FA = False
    owner = make_user(is_staff=True, is_superuser=True)
    device = TOTPDevice.objects.create(user=owner, name="app", confirmed=True)
    client = csrf_client_for(APIClient(enforce_csrf_checks=True))
    client.post("/api/account/login/", {"email": owner.email, "password": PASSWORD}, format="json")
    client = csrf_client_for(client)
    reply = client.post("/api/account/login/two-step/", {"code": code_for(device)}, format="json")
    assert reply.json()["user"]["staff"]["verified"] is True
    assert client.get("/api/staff/overview/").status_code == 200


# Feed settings that moved here


def test_mutes_list_only_your_own(member_client, make_member):
    client, viewer = member_client()
    muted, other = make_member(display_name="quiet_hours"), make_member()
    services.mute(viewer, muted)
    services.mute(other, viewer)
    assert client.get("/api/members/me/mutes/").json() == {"muted": ["quiet_hours"]}


def test_pronouns_show_on_the_profile_only_when_filled(member_client, make_member):
    client, _ = member_client()
    other = make_member(display_name="soft_focus")
    assert client.get("/api/members/u/soft_focus/").json()["pronouns"] == ""
    other.profile.pronouns = "she/her"
    other.profile.save()
    assert client.get("/api/members/u/soft_focus/").json()["pronouns"] == "she/her"


# The data export, for every account


def test_a_plain_account_exports_its_data_and_never_reaches_the_feed(
    signed_in, make_event, api_client
):
    client, user = signed_in()
    submit_rsvp(user, make_event(), 1)
    assert client.get("/api/account/export/").json() == {"export": None}
    assert client.post("/api/account/export/").status_code == 202
    assert client.get("/api/account/export/").json()["export"]["ready"] is True
    email = next(m for m in mail.outbox if m.subject == feed_tasks.EXPORT_SUBJECT)
    assert "/members/settings/privacy/export#token=" in email.body
    token = email.body.split("#token=")[1].split()[0]
    download = api_client.post("/api/account/export/download/", {"token": token}, format="json")
    assert download.status_code == 200
    archive = zipfile.ZipFile(BytesIO(b"".join(download.streaming_content)))
    text = archive.read("data.json").decode()
    data = json.loads(text)
    assert data["account"]["display_name"] == user.display_name
    assert len(data["account"]["rsvps"]) == 1
    assert data["posts"] == []
    assert user.email not in text

    for path in (
        "/api/account/feed/",
        "/api/members/me/",
        "/api/members/feed/",
        "/api/members/home/",
        "/api/members/stories/",
        "/api/members/directory/",
        "/api/members/me/mutes/",
    ):
        assert client.get(path).status_code == 404, path


def test_only_one_export_is_prepared_at_a_time(signed_in, monkeypatch):
    client, _ = signed_in()
    monkeypatch.setattr("apps.feed.tasks.build_member_export.delay", lambda *args: None)
    assert client.post("/api/account/export/").status_code == 202
    assert client.post("/api/account/export/").status_code == 409
