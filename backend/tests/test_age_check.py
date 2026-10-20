"""The member feed needs an in-person age check, whatever the entitlement came from.

Verification is the door desk's IdCheck: only that staff saw a valid photo ID showing 18+.
No ID data is ever stored. Staff and superusers need their own check like everyone else.
"""

import importlib
from io import StringIO
from pathlib import Path

import pytest
from django.apps import apps as django_apps
from django.conf import settings
from django.core import mail
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import AuditLog
from apps.feed import access
from apps.feed.models import FeedPost, Notification, Report
from apps.memberships import desk
from apps.memberships.access import MEMBERS_EVENTS, entitlements, is_age_verified
from apps.memberships.age import AgeCheckError, record_id_check, revoke_id_checks
from apps.memberships.models import IdCheck, Membership, Tier
from apps.memberships.providers.service import activate_or_extend
from apps.safety import roles

from .conftest import csrf_client_for, staff_login, verify_age
from .test_feed_access import METHODS, concrete, feed_routes

pytestmark = pytest.mark.django_db

SOURCES = ["paid", "free", "comp", "staff_grant", "is_staff", "superuser"]


def joined(user):
    """In the feed as far as their own choices go: opted in, guidelines accepted."""
    from apps.feed.models import Guidelines, GuidelinesAcceptance

    GuidelinesAcceptance.objects.get_or_create(user=user, guidelines=Guidelines.current())
    profile = user.profile
    profile.participates_in_feed = True
    profile.joined_feed_at = timezone.now()
    profile.save()
    return user


@pytest.fixture
def entitled(make_user, make_tier, make_membership, django_user_model):
    """A person entitled to the feed by `source`, opted in, with no ID check yet."""

    def make(source):
        if source == "superuser":
            user = django_user_model.objects.create_superuser(
                email="owner@example.org", display_name="the_owner", password="pw-0123456789"
            )
            user.mark_email_verified()
        else:
            user = make_user()
        if source in ("paid", "free", "comp"):
            tier = make_tier(price_cents=0 if source == "free" else 2500, grants_feed_access=True)
            membership = make_membership(user=user, tier=tier, id_check=False)
            if source == "comp":
                membership.source = Membership.Source.COMP
                membership.save()
        elif source == "staff_grant":
            user.profile.feed_access_granted = True
            user.profile.save()
        elif source == "is_staff":
            user.is_staff = True
            user.save()
        user.refresh_from_db()
        assert access.has_feed_entitlement(user), source
        return joined(user)

    return make


@pytest.fixture
def picture(make_member, make_post):
    author = make_member(display_name="feed_author")
    return make_post(author, images=1)


def client_for(user):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)
    return client


# One rule, everywhere


@pytest.mark.parametrize("source", SOURCES)
def test_unverified_gets_404_on_every_feed_url_and_media(source, entitled, picture):
    user = entitled(source)
    assert not is_age_verified(user)
    assert not access.can_join_feed(user) and not access.can_view_feed(user)
    assert not access.can_post(user) and access.awaiting_age_check(user)
    plain = client_for(user)
    with_csrf = csrf_client_for(client_for(user))
    image = picture.images.first()
    urls = [concrete(r, picture.public_id, "feed_author") for r in feed_routes()]
    urls.append(reverse("feed-media", args=[image.public_id]))
    for url in urls:
        for method in METHODS:
            for client in (plain, with_csrf):
                response = getattr(client, method)(url, {}, format="json")
                assert response.status_code == 404, f"{source} {method} {url}"


@pytest.mark.parametrize("source", SOURCES)
def test_verified_reaches_the_feed_and_its_pictures(source, entitled, picture, private_root):
    user = entitled(source)
    verify_age(user)
    assert access.can_view_feed(user) and access.can_post(user)
    client = client_for(user)
    assert client.get("/api/members/feed/").status_code == 200
    for path in (
        "/api/members/home/",
        "/api/members/stories/",
        "/api/members/notifications/",
        "/api/members/directory/?q=feed",
        "/api/members/u/feed_author/posts/",
    ):
        assert client.get(path).status_code == 200, path
    media = client.get(reverse("feed-media", args=[picture.images.first().public_id]))
    assert media.status_code in (200, 302)
    assert "no-store" in media["Cache-Control"]


def test_staff_need_their_own_check_for_reported_pictures(make_user, picture, private_root):
    moderator = make_user()
    roles.set_role(moderator, roles.MODERATOR)
    reporter = make_user()
    Report.objects.create(reporter=reporter, target_type="post", post=picture, reason="harassment")
    image = picture.images.first()
    api = staff_login(APIClient(), moderator)
    url = f"/api/staff/media/{image.public_id}/"
    assert api.get(url).status_code == 404
    report = Report.objects.get()
    detail = api.get(f"/api/staff/reports/{report.pk}/").json()
    assert detail["content"]["images"] == [] and detail["content"]["images_withheld"] == 1
    verify_age(moderator)
    assert api.get(url).status_code in (200, 302)
    detail = api.get(f"/api/staff/reports/{report.pk}/").json()
    assert detail["content"]["images"] == [url] and detail["content"]["images_withheld"] == 0


def test_admin_moderation_pictures_need_the_check_too(admin_user, picture, private_root):
    client = staff_login(Client(), admin_user)
    image = picture.images.first()
    url = reverse("admin:feed_moderation_image", args=[image.public_id])
    assert client.get(url).status_code == 404
    page = client.get(reverse("admin:feed_moderation")).content.decode()
    assert "Pictures are hidden until your own ID check is recorded" in page
    verify_age(admin_user)
    assert client.get(url).status_code in (200, 302)


# Bypasses closed


def test_staff_grant_shows_as_awaiting_until_checked(admin_client, make_user):
    user = make_user(display_name="granted_one")
    admin_client.post(
        reverse("admin:accounts_profile_changelist"),
        {"action": "grant_feed_access", "_selected_action": [user.profile.pk]},
    )
    user.refresh_from_db()
    assert user.profile.feed_access_granted
    assert access.feed_access_label(user) == "Granted, awaiting ID check"
    assert not access.can_join_feed(user)
    page = admin_client.get(reverse("admin:accounts_profile_changelist")).content.decode()
    assert "Granted, awaiting ID check" in page
    verify_age(user)
    assert access.feed_access_label(user) == "Granted" and access.can_join_feed(user)


def test_staff_section_shows_the_check_and_the_grant(make_user):
    admin = make_user()
    roles.set_role(admin, roles.ADMIN)
    member = make_user(display_name="granted_two")
    member.profile.feed_access_granted = True
    member.profile.save()
    api = staff_login(APIClient(), admin)
    body = api.get("/api/staff/members/granted_two/").json()
    assert body["age_verified"] is False
    assert body["feed_access"] == "Granted, awaiting ID check"


def write_csv(tmp_path, rows):
    path = Path(tmp_path) / "members.csv"
    lines = ["email,display_name,tier_slug,period_end,id_checked", *rows]
    path.write_text("\n".join(lines) + "\n")
    return str(path)


def test_import_without_an_id_check_grants_nothing(tmp_path, make_tier):
    make_tier(slug="rose", grants_feed_access=True, grants_members_events=True)
    end = (timezone.localdate() + timezone.timedelta(days=60)).isoformat()
    csv_path = write_csv(
        tmp_path,
        [
            f"seen@example.org,seen_one,rose,{end},yes",
            f"unseen@example.org,unseen_one,rose,{end},no",
        ],
    )
    out = StringIO()
    call_command("import_members", csv_path, stdout=out)
    assert "ID checked: 1" in out.getvalue() and "Not ID checked: 1" in out.getvalue()
    call_command("import_members", csv_path, "--commit", stdout=StringIO())
    unseen = Membership.objects.get(user__display_name="unseen_one")
    assert unseen.status == Membership.Status.PENDING_PAYMENT and unseen.paid_awaiting_id_check
    assert entitlements(unseen.user) == set() and not is_age_verified(unseen.user)
    assert desk.card(unseen)["id_checked"] is False
    assert unseen in desk.needing_id_check()[0]
    seen = Membership.objects.get(user__display_name="seen_one")
    assert seen.status == Membership.Status.ACTIVE and is_age_verified(seen.user)


def test_comp_needs_an_id_check(desk_staff, make_membership):
    membership = make_membership(status="expired", id_check=False)
    with pytest.raises(desk.DeskError):
        desk.comp(desk_staff, membership, "Volunteer thank-you")
    membership.refresh_from_db()
    assert membership.status == "expired"
    desk.comp(desk_staff, membership, "Volunteer thank-you", id_checked=True)
    assert is_age_verified(membership.user)


def test_paid_online_waiting_for_the_check_grants_nothing(make_user, make_tier):
    user = make_user()
    tier = make_tier(grants_feed_access=True, grants_members_events=True)
    membership = Membership.objects.create(user=user, tier=tier)
    activate_or_extend(membership)
    membership.save()
    assert membership.status == Membership.Status.PENDING_PAYMENT
    assert membership.paid_awaiting_id_check
    assert entitlements(user) == set()
    assert not access.has_feed_entitlement(user) and not access.can_view_feed(user)


def test_renew_and_reinstate_need_a_check_on_file(desk_staff, make_membership):
    lapsed = make_membership(status="expired", id_check=False)
    with pytest.raises(desk.DeskError):
        desk.renew(desk_staff, lapsed, "cash", 2500)
    desk.renew(desk_staff, lapsed, "cash", 2500, id_checked=True)
    lapsed.refresh_from_db()
    assert lapsed.status == "active" and is_age_verified(lapsed.user)
    paused = make_membership(status="suspended")
    revoke_id_checks(desk_staff, paused.user, "Checked the wrong person")
    with pytest.raises(desk.DeskError):
        desk.reinstate(desk_staff, paused, "Talked it through")


def test_members_only_events_and_classes_need_activation_which_needs_a_check(
    desk_staff, make_user, make_tier
):
    """Unchanged rules: no running membership, no members-only access; and nothing at the
    desk starts a membership without a valid check."""
    tier = make_tier(grants_members_events=True, grants_members_education=True)
    user = make_user()
    pending = Membership.objects.create(user=user, tier=tier)
    assert MEMBERS_EVENTS not in entitlements(user)
    for start in (
        lambda: desk.record_payment_and_activate(desk_staff, pending, "cash", 2500),
        lambda: desk.comp(desk_staff, pending, "Thanks"),
    ):
        with pytest.raises(desk.DeskError):
            start()
    assert not Membership.objects.filter(user=user, status__in=Membership.ENTITLED).exists()
    desk.record_payment_and_activate(desk_staff, pending, "cash", 2500, id_checked=True)
    assert MEMBERS_EVENTS in entitlements(user) and is_age_verified(user)


# Team accounts: two people


def test_a_team_members_own_check_needs_a_witness_and_logs_both(desk_staff, make_user):
    with pytest.raises(AgeCheckError):
        record_id_check(desk_staff, desk_staff)
    with pytest.raises(AgeCheckError):
        record_id_check(desk_staff, desk_staff, witness=make_user())  # not on the team
    witness = make_user(display_name="team_witness")
    witness.is_staff = True
    witness.save()
    check = record_id_check(desk_staff, desk_staff, witness=witness)
    assert check.checked_by == desk_staff and check.witnessed_by == witness
    logged = AuditLog.objects.filter(category=AuditLog.Category.DOOR_DESK)
    assert logged.get(action="id_check").actor == desk_staff
    assert logged.get(action="id_check_witnessed").actor == witness


def test_another_team_member_can_check_a_superuser(desk_staff, admin_user):
    record_id_check(desk_staff, admin_user)
    assert is_age_verified(admin_user)


def test_door_api_verifies_a_person_without_a_membership(desk_staff, make_user):
    granted = make_user(display_name="granted_three")
    granted.profile.feed_access_granted = True
    granted.profile.save()
    api = csrf_client_for(staff_login(APIClient(enforce_csrf_checks=True), desk_staff))
    api.default_format = "json"
    search = api.get("/api/staff/door/", {"q": "granted_th"}).json()
    [person] = search["people"]
    assert person["display_name"] == "granted_three" and person["actions"] == ["verify"]
    waiting = api.get("/api/staff/door/", {"needs_id": "1"}).json()
    assert [p["display_name"] for p in waiting["people"]] == ["door_volunteer", "granted_three"]
    refused = api.post("/api/staff/door/", {"action": "verify", "person": granted.pk})
    assert refused.status_code == 400
    done = api.post(
        "/api/staff/door/", {"action": "verify", "person": granted.pk, "id_checked": True}
    )
    assert done.json() == {"message": "granted_three: ID check recorded."}
    assert is_age_verified(granted)
    mine = api.get("/api/staff/door/", {"q": "door_vol"}).json()
    assert mine["people"][0]["is_you"] is True and mine["witnesses"] == []


# Verifying unlocks at once; revoking closes at once


def test_verifying_unlocks_without_logging_out_and_tells_them(
    entitled, desk_staff, django_capture_on_commit_callbacks
):
    user = entitled("staff_grant")
    client = client_for(user)
    assert client.get("/api/members/me/").status_code == 404
    assert client.get("/api/account/session/").json()["user"]["member_app"] == "verify"
    with django_capture_on_commit_callbacks(execute=True):
        record_id_check(desk_staff, user)
    assert client.get("/api/members/me/").status_code == 200
    assert client.get("/api/account/session/").json()["user"]["member_app"] == "open"
    note = Notification.objects.get(recipient=user)
    assert note.kind == Notification.Kind.AGE_VERIFIED
    [email] = mail.outbox
    assert email.subject == "You're all set" and email.to == [user.email]
    assert "ID" not in email.body and "18" not in email.body


def test_revoking_closes_the_feed_and_its_pictures_at_once(
    make_member, picture, desk_staff, private_root
):
    member = make_member()
    client = client_for(member)
    media = reverse("feed-media", args=[picture.images.first().public_id])
    assert client.get(media).status_code in (200, 302)
    with pytest.raises(AgeCheckError):
        revoke_id_checks(desk_staff, member, "  ")
    revoke_id_checks(desk_staff, member, "The ID did not match")
    assert client.get("/api/members/feed/").status_code == 404
    assert client.get(media).status_code == 404
    check = IdCheck.objects.get(user=member)
    assert check.revoked_by == desk_staff and check.revoke_reason == "The ID did not match"
    entry = AuditLog.objects.get(action="id_check_revoked")
    assert entry.reason == "The ID did not match" and entry.target_user == member


def test_signed_urls_expire_within_a_minute():
    assert 1 <= settings.S3_SIGNED_URL_SECONDS <= 60


# The data migration


def test_migration_finds_feed_access_without_a_check_and_the_email_goes_once(
    entitled, make_member, make_user
):
    migration = importlib.import_module("apps.memberships.migrations.0007_feed_waits_for_age_check")
    waiting = [entitled(source) for source in ("paid", "staff_grant", "is_staff")]
    checked = make_member()
    plain = make_user()
    out = StringIO()
    import contextlib

    with contextlib.redirect_stdout(out):
        migration.stamp(django_apps, None)
    assert "waits for an ID check for 3 account(s)" in out.getvalue()
    for user in waiting:
        user.profile.refresh_from_db()
        assert user.profile.age_check_notice_at is not None
        assert not access.can_view_feed(user)
        session = client_for(user).get("/api/account/session/").json()["user"]
        assert session["age_check"] == {"verified": False, "needed": True, "notice": True}
    for user in (checked, plain):
        user.profile.refresh_from_db()
        assert user.profile.age_check_notice_at is None
    from apps.memberships.tasks import send_age_check_notices

    assert send_age_check_notices() == 3
    assert send_age_check_notices() == 0
    assert {m.to[0] for m in mail.outbox} == {u.email for u in waiting}
    assert all(m.subject == "A note about your account" for m in mail.outbox)


# Nothing about the ID is stored or shown


def test_an_id_check_stores_nothing_about_the_id(desk_staff, make_membership):
    names = {field.name for field in IdCheck._meta.get_fields()}
    assert names == {
        "id",
        "user",
        "membership",
        "checked_by",
        "witnessed_by",
        "checked_at",
        "verified_18_plus",
        "revoked_at",
        "revoked_by",
        "revoke_reason",
    }
    assert not any(
        field.get_internal_type() in ("FileField", "ImageField", "BinaryField")
        for field in IdCheck._meta.concrete_fields
    )
    membership = make_membership(status="pending_payment", id_check=False)
    api = csrf_client_for(staff_login(APIClient(enforce_csrf_checks=True), desk_staff))
    api.default_format = "json"
    api.post(
        "/api/staff/door/",
        {"action": "verify", "membership": membership.pk, "id_checked": True},
    )
    entry = AuditLog.objects.get(action="id_check")
    assert entry.reason == "" and "18" not in entry.target_label


def test_no_id_upload_paths_exist():
    from django.urls import get_resolver

    def walk(patterns, prefix=""):
        for pattern in patterns:
            route = prefix + str(pattern.pattern)
            if hasattr(pattern, "url_patterns"):
                yield from walk(pattern.url_patterns, route)
            else:
                yield route

    routes = " ".join(walk(get_resolver().url_patterns)).lower()
    for word in ("selfie", "id-upload", "id_upload", "identity", "document"):
        assert word not in routes


# Reports and uploads


def test_possibly_under_18_hides_at_once_and_goes_to_the_top(make_member, make_post, make_user):
    from apps.feed import services as feed_services

    reporter = make_member()
    older = make_post(make_member(), caption="Older")
    newer = make_post(make_member(), caption="Newer")
    feed_services.report(reporter, "post", older, Report.Reason.UNDER_18, "")
    feed_services.report(reporter, "post", newer, Report.Reason.HARASSMENT, "")
    older.refresh_from_db()
    assert older.status == FeedPost.Status.HIDDEN_BY_REPORT
    moderator = make_user()
    roles.set_role(moderator, roles.MODERATOR)
    inbox = staff_login(APIClient(), moderator).get("/api/staff/reports/").json()
    assert inbox[0]["reason"] == Report.Reason.UNDER_18


def test_tier_feed_flag_still_needs_the_check(make_user, make_tier, make_membership):
    tier = make_tier(grants_feed_access=True)
    assert Tier.objects.filter(pk=tier.pk, grants_feed_access=True).exists()
    member = make_membership(user=make_user(), tier=tier, id_check=False)
    assert access.has_feed_entitlement(member.user) and not access.can_join_feed(member.user)
