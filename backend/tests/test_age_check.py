"""The member feed needs an in-person age check, whatever the entitlement came from, while
the club has the check switched on (SiteSettings.require_age_verification_for_feed).

Verification is the door desk's IdCheck: only that staff saw a valid photo ID showing 18+.
No ID data is ever stored. Staff and superusers need their own check like everyone else.
Every access rule is tested with the setting on and off; the rules that hold either way
are tested with it off.
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
SETTING = pytest.mark.parametrize("required", [True, False], ids=["check-on", "check-off"])


def switch(required):
    """Set the club's switch directly, as a test fixture would, and clear the cache."""
    from django.core.cache import cache

    from apps.memberships.access import AGE_CHECK_CACHE_KEY
    from apps.pages.models import SiteSettings

    site = SiteSettings.load()
    site.require_age_verification_for_feed = required
    site.save()
    cache.delete(AGE_CHECK_CACHE_KEY)


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


def status_of(client, url):
    """The status of a media response, closing the file it streams (closing the response
    itself would also close the test's database connection)."""
    response = client.get(url)
    stream = getattr(response, "file_to_stream", None)
    if stream is not None:
        stream.close()
    return response.status_code


def client_for(user):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)
    return client


# One rule, everywhere


@pytest.mark.parametrize("source", SOURCES)
def test_check_on_unverified_gets_404_on_every_feed_url_and_media(source, entitled, picture):
    switch(True)
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


@pytest.mark.parametrize(
    ("verified", "required"),
    [(True, True), (True, False), (False, False)],
    ids=["verified-check-on", "verified-check-off", "unverified-check-off"],
)
@pytest.mark.parametrize("source", SOURCES)
def test_the_feed_and_its_pictures_open(
    source, verified, required, entitled, picture, private_root
):
    """Verified people always; unverified ones only while the check is switched off (the
    fourth case is test_check_on_unverified_gets_404_on_every_feed_url_and_media)."""
    switch(required)
    user = entitled(source)
    if verified:
        verify_age(user)
    assert access.can_view_feed(user) and access.can_post(user)
    assert not access.awaiting_age_check(user)
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
    if getattr(media, "file_to_stream", None) is not None:
        media.file_to_stream.close()
    assert media.status_code in (200, 302)
    assert "no-store" in media["Cache-Control"]


@SETTING
def test_staff_need_their_own_check_for_reported_pictures(
    required, make_user, picture, private_root
):
    switch(required)
    moderator = make_user()
    roles.set_role(moderator, roles.MODERATOR)
    reporter = make_user()
    Report.objects.create(reporter=reporter, target_type="post", post=picture, reason="harassment")
    image = picture.images.first()
    api = staff_login(APIClient(), moderator)
    url = f"/api/staff/media/{image.public_id}/"
    report = Report.objects.get()
    if required:
        assert status_of(api, url) == 404
        detail = api.get(f"/api/staff/reports/{report.pk}/").json()
        assert detail["content"]["images"] == [] and detail["content"]["images_withheld"] == 1
        verify_age(moderator)
    assert status_of(api, url) in (200, 302)
    detail = api.get(f"/api/staff/reports/{report.pk}/").json()
    assert detail["content"]["images"] == [url] and detail["content"]["images_withheld"] == 0


@SETTING
def test_admin_moderation_pictures_need_the_check_too(required, admin_user, picture, private_root):
    switch(required)
    client = staff_login(Client(), admin_user)
    image = picture.images.first()
    url = reverse("admin:feed_moderation_image", args=[image.public_id])
    page = client.get(reverse("admin:feed_moderation")).content.decode()
    if required:
        assert status_of(client, url) == 404
        assert "Pictures are hidden until your own ID check is recorded" in page
        verify_age(admin_user)
    else:
        assert "Pictures are hidden" not in page
    assert status_of(client, url) in (200, 302)


# Bypasses closed


def test_staff_grant_shows_as_awaiting_until_checked(admin_client, make_user):
    switch(True)
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


def test_with_the_check_off_a_grant_is_simply_granted_and_nothing_mentions_the_check(
    make_user, desk_staff
):
    switch(False)
    user = make_user(display_name="granted_off")
    user.profile.feed_access_granted = True
    user.profile.save()
    assert access.feed_access_label(user) == "Granted"
    assert access.can_join_feed(user) and not access.awaiting_age_check(user)
    session = client_for(user).get("/api/account/session/").json()["user"]
    assert session["member_app"] == "join"
    assert session["age_check"] == {"verified": False, "needed": False, "notice": False}
    feed = client_for(user).get("/api/account/feed/").json()
    assert feed["awaiting_age_check"] is False and feed["can_join"] is True
    # The door desk still shows who is and is not checked, so staff can keep checking.
    card = desk.person_card(user)
    assert card["id_checked"] is False and card["actions"] == ["verify"]


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


@SETTING
def test_import_without_an_id_check_grants_nothing(required, tmp_path, make_tier):
    switch(required)
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


@SETTING
def test_comp_needs_an_id_check(required, desk_staff, make_membership):
    switch(required)
    membership = make_membership(status="expired", id_check=False)
    with pytest.raises(desk.DeskError):
        desk.comp(desk_staff, membership, "Volunteer thank-you")
    membership.refresh_from_db()
    assert membership.status == "expired"
    desk.comp(desk_staff, membership, "Volunteer thank-you", id_checked=True)
    assert is_age_verified(membership.user)


@SETTING
def test_paid_online_waiting_for_the_check_grants_nothing(required, make_user, make_tier):
    switch(required)
    user = make_user()
    tier = make_tier(grants_feed_access=True, grants_members_events=True)
    membership = Membership.objects.create(user=user, tier=tier)
    activate_or_extend(membership)
    membership.save()
    assert membership.status == Membership.Status.PENDING_PAYMENT
    assert membership.paid_awaiting_id_check
    assert entitlements(user) == set()
    assert not access.has_feed_entitlement(user) and not access.can_view_feed(user)


@SETTING
def test_renew_and_reinstate_need_a_check_on_file(required, desk_staff, make_membership):
    switch(required)
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


@SETTING
def test_members_only_events_and_classes_need_activation_which_needs_a_check(
    required, desk_staff, make_user, make_tier
):
    """Unchanged rules: no running membership, no members-only access; and nothing at the
    desk starts a membership without a valid check, whatever the setting."""
    switch(required)
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
    switch(True)
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
    switch(True)
    member = make_member()
    client = client_for(member)
    media = reverse("feed-media", args=[picture.images.first().public_id])
    assert status_of(client, media) in (200, 302)
    with pytest.raises(AgeCheckError):
        revoke_id_checks(desk_staff, member, "  ")
    revoke_id_checks(desk_staff, member, "The ID did not match")
    assert client.get("/api/members/feed/").status_code == 404
    assert status_of(client, media) == 404
    check = IdCheck.objects.get(user=member)
    assert check.revoked_by == desk_staff and check.revoke_reason == "The ID did not match"
    entry = AuditLog.objects.get(action="id_check_revoked")
    assert entry.reason == "The ID did not match" and entry.target_user == member


def test_signed_urls_expire_within_a_minute():
    assert 1 <= settings.S3_SIGNED_URL_SECONDS <= 60


# The migration only counts


def test_migration_prints_how_many_with_feed_access_have_no_check(entitled, make_member, make_user):
    import contextlib

    migration = importlib.import_module("apps.memberships.migrations.0007_feed_waits_for_age_check")
    waiting = [entitled(source) for source in ("paid", "staff_grant", "is_staff")]
    make_member()  # checked
    make_user()  # no feed access
    out = StringIO()
    with contextlib.redirect_stdout(out):
        migration.count(django_apps, None)
    assert "3 account(s) with feed access have no ID check" in out.getvalue()
    for user in waiting:
        user.profile.refresh_from_db()
        assert user.profile.age_check_notice_at is None
    assert not mail.outbox


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


@SETTING
def test_possibly_under_18_hides_at_once_and_goes_to_the_top(
    required, make_member, make_post, make_user
):
    switch(required)
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


# The club's switch


def fresh_code(user):
    """The current code from this person's authenticator (staff_login made the device)."""
    import time

    from django_otp.oath import TOTP
    from django_otp.plugins.otp_totp.models import TOTPDevice

    device = TOTPDevice.objects.get(user=user, confirmed=True)
    totp = TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift)
    totp.time = time.time()
    return f"{totp.token():0{device.digits}d}"


def next_window(user):
    """As if the next 30-second code window had come: the last code used no longer blocks
    the current one (django-otp refuses a code it has already accepted)."""
    from django_otp.plugins.otp_totp.models import TOTPDevice

    TOTPDevice.objects.filter(user=user).update(last_t=-1)


def staff_api(user):
    api = csrf_client_for(staff_login(APIClient(enforce_csrf_checks=True), user))
    api.default_format = "json"
    return api


@pytest.fixture
def team_member(make_user):
    def make(role):
        user = make_user(display_name=f"team_{role}")
        roles.set_role(user, role)
        return user

    return make


def test_the_check_is_on_by_default_for_a_new_database():
    from apps.memberships.access import age_check_required
    from apps.pages.models import SiteSettings

    assert SiteSettings.load().require_age_verification_for_feed is True
    assert age_check_required() is True


def test_only_admins_change_it_with_a_reason_and_a_fresh_code_and_it_is_logged(
    team_member, django_capture_on_commit_callbacks
):
    for role in (roles.MODERATOR, roles.STAFF):
        user = team_member(role)
        api = staff_api(user)
        seen = api.get("/api/staff/settings/age-verification/").json()
        assert seen["required"] is True and seen["can_change"] is False
        refused = api.post(
            "/api/staff/settings/age-verification/",
            {"required": False, "reason": "Trying", "code": fresh_code(user)},
        )
        assert refused.status_code == 403
    admin = team_member(roles.ADMIN)
    api = staff_api(admin)
    assert api.get("/api/staff/settings/age-verification/").json()["can_change"] is True
    no_reason = api.post(
        "/api/staff/settings/age-verification/",
        {"required": False, "reason": " ", "code": fresh_code(admin)},
    )
    assert no_reason.status_code == 400
    wrong = api.post(
        "/api/staff/settings/age-verification/",
        {"required": False, "reason": "Soft launch", "code": "000000"},
    )
    assert wrong.status_code == 400
    code = fresh_code(admin)
    done = api.post(
        "/api/staff/settings/age-verification/",
        {"required": False, "reason": "Soft launch", "code": code},
    )
    assert done.status_code == 200 and done.json()["required"] is False
    # The same code twice is not fresh.
    with django_capture_on_commit_callbacks(execute=True):
        reused = api.post(
            "/api/staff/settings/age-verification/",
            {"required": True, "reason": "Back on", "code": code},
        )
    assert reused.status_code == 400
    entry = AuditLog.objects.get(category=AuditLog.Category.SETTINGS)
    assert entry.action == "age_verification_off" and entry.actor == admin
    assert entry.target_label == "Age verification for the member feed"
    assert entry.reason == "Changed from On to Off. Reason: Soft launch"
    assert entry.created_at is not None
    assert AuditLog.objects.filter(category=AuditLog.Category.SETTINGS).count() == 1


def test_a_superuser_changes_it_in_the_admin_and_others_only_see_it(admin_user, team_member):
    staff = team_member(roles.STAFF)
    viewer = staff_login(Client(), staff)
    url = reverse("admin:pages_sitesettings_age_verification")
    page = viewer.get(url).content.decode()
    assert "Only an admin can change this setting." in page and 'name="code"' not in page
    assert viewer.post(url, {"required": "off", "reason": "x", "code": "1"}).status_code == 403
    owner = staff_login(Client(), admin_user)
    page = owner.get(url).content.decode()
    assert 'name="reason"' in page and 'name="code"' in page
    assert "Turning it off opens the member feed at once" in page
    response = owner.post(
        url, {"required": "off", "reason": "Event weekend", "code": fresh_code(admin_user)}
    )
    assert response.status_code == 302
    from apps.memberships.access import age_check_required

    assert age_check_required() is False
    settings_page = owner.get(reverse("admin:pages_sitesettings_change", args=[1])).content.decode()
    assert "Age verification for the member feed" in settings_page
    assert AuditLog.objects.get(category=AuditLog.Category.SETTINGS).actor == admin_user


def test_the_banner_shows_on_every_staff_page_while_it_is_off(admin_user, team_member):
    owner = staff_login(Client(), admin_user)
    staff = staff_login(Client(), team_member(roles.STAFF))
    banner = "Age verification for the member feed is off"
    for client in (owner, staff):
        assert banner not in client.get(reverse("admin:index")).content.decode()
    switch(False)
    for path in (reverse("admin:index"), reverse("admin:events_event_changelist")):
        page = owner.get(path).content.decode()
        assert banner in page
        assert reverse("admin:pages_sitesettings_age_verification") in page
    staff_page = staff.get(reverse("admin:index")).content.decode()
    assert banner in staff_page
    assert f'href="{reverse("admin:pages_sitesettings_age_verification")}"' not in staff_page
    session = staff_api(admin_user).get("/api/account/session/").json()["user"]["staff"]
    assert session["age_check_required"] is False and session["can_change_age_check"] is True


def test_the_setting_is_cached_for_seconds_only():
    from django.core.cache import cache

    from apps.memberships.access import (
        AGE_CHECK_CACHE_KEY,
        AGE_CHECK_CACHE_SECONDS,
        age_check_required,
    )
    from apps.pages.models import SiteSettings

    assert AGE_CHECK_CACHE_SECONDS <= 10
    assert age_check_required() is True
    SiteSettings.objects.update(require_age_verification_for_feed=False)
    assert age_check_required() is True  # still cached
    cache.delete(AGE_CHECK_CACHE_KEY)  # what the expiry does
    assert age_check_required() is False


def test_switching_on_closes_the_feed_and_its_pictures_at_once(
    entitled, admin_user, picture, private_root
):
    from apps.memberships.age import set_age_check_required

    switch(False)
    member = entitled("staff_grant")
    client = client_for(member)
    media = reverse("feed-media", args=[picture.images.first().public_id])
    assert status_of(client, media) in (200, 302)
    staff_login(APIClient(), admin_user)
    set_age_check_required(admin_user, True, "Opening night", fresh_code(admin_user))
    assert status_of(client, media) == 404
    assert client.get("/api/members/feed/").status_code == 404


def test_each_person_is_told_once_per_switch_on(
    entitled, make_member, admin_user, django_capture_on_commit_callbacks
):
    from apps.memberships.age import notify_switched_on, set_age_check_required
    from apps.pages.models import SiteSettings

    staff_login(APIClient(), admin_user)
    verify_age(admin_user)
    switch(False)
    unchecked = [entitled("paid"), entitled("staff_grant")]
    make_member()  # checked: never told
    with django_capture_on_commit_callbacks(execute=True):
        set_age_check_required(admin_user, True, "Back on", fresh_code(admin_user))
    assert sorted(m.to[0] for m in mail.outbox) == sorted(u.email for u in unchecked)
    assert all(m.subject == "A note about your account" for m in mail.outbox)
    switched_on_at = SiteSettings.load().age_verification_switched_on_at
    assert notify_switched_on(switched_on_at) == 0  # a second run tells nobody again
    session = client_for(unchecked[0]).get("/api/account/session/").json()["user"]
    assert session["age_check"] == {"verified": False, "needed": True, "notice": True}
    mail.outbox.clear()
    next_window(admin_user)
    set_age_check_required(admin_user, False, "Off again", fresh_code(admin_user))
    next_window(admin_user)
    with django_capture_on_commit_callbacks(execute=True):
        set_age_check_required(admin_user, True, "On again", fresh_code(admin_user))
    assert sorted(m.to[0] for m in mail.outbox) == sorted(u.email for u in unchecked)


@SETTING
def test_the_upload_promise_is_needed_either_way(required, make_member, image_upload):
    from apps.feed import services as feed_services

    switch(required)
    author = make_member()
    with pytest.raises(feed_services.FeedError) as refused:
        feed_services.create_post(author, "Hello", [image_upload()], attested=False)
    assert refused.value.code == "attestation"
