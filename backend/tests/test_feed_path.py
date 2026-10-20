"""The way into the member community: make_feed_member (DEBUG only), the "What's missing"
checklist on Home, and the club-only preview shown to accounts without the feed."""

import json
from datetime import timedelta
from io import StringIO

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.core.models import AuditLog, SeedMarker
from apps.feed.access import can_view_feed
from apps.feed.models import Announcement, FeedPost, Guidelines, GuidelinesAcceptance
from apps.journal.models import Post as JournalPost
from apps.journal.models import PostImage as JournalImage
from apps.memberships.models import IdCheck, Membership, Payment
from apps.pages.models import SiteSettings
from tests.conftest import verify_age

pytestmark = pytest.mark.django_db


@pytest.fixture
def rose(make_tier):
    return make_tier(name="Rose", slug="rose", price_cents=4000)


@pytest.fixture
def dev(settings):
    settings.DEBUG = True
    settings.DJANGO_ENV = "development"
    return settings


def make_feed_member(*args):
    out = StringIO()
    call_command("make_feed_member", *args, stdout=out)
    return out.getvalue()


# make_feed_member


def test_make_feed_member_gives_a_new_account_the_whole_feed(dev, rose):
    out = make_feed_member("you@test.local")
    user = Membership.objects.get(tier=rose).user
    assert user.email == "you@test.local" and user.display_name == "you"
    assert user.email_verified and not user.has_usable_password()
    assert can_view_feed(user)

    membership = user.memberships.get()
    assert membership.status == Membership.Status.ACTIVE
    payment = membership.payments.get()
    assert (payment.method, payment.amount_cents) == (Payment.Method.CASH, 4000)
    assert payment.recorded_by.display_name == "system_dev"
    activation = AuditLog.objects.get(action="activate", target_ref=membership.reference_code)
    assert activation.category == AuditLog.Category.DOOR_DESK
    assert activation.actor.display_name == "system_dev" and not activation.actor.is_active
    check = IdCheck.valid().get(user=user)
    assert check.checked_by.display_name == "system_dev" and check.membership == membership
    assert GuidelinesAcceptance.objects.filter(user=user, guidelines=Guidelines.current()).exists()
    assert user.profile.participates_in_feed and user.profile.joined_feed_at
    assert SeedMarker.objects.exists()

    # The link to choose a password arrives by email (Mailpit, locally).
    assert any("/account/reset#uid=" in message.body for message in mail.outbox)
    for line in (
        "Account: created, display name you",
        "Email: confirmed",
        f"Membership: {membership.reference_code} activated on Rose at the door desk by "
        "system_dev (cash $40.00)",
        "ID check: recorded by system_dev with the activation",
        f"Guidelines: version {Guidelines.current().version} accepted",
        "Feed: joined",
        "Password: a link to choose one was sent to you@test.local",
    ):
        assert line in out, line


def test_make_feed_member_is_idempotent(dev, rose):
    make_feed_member("you@test.local")
    out = make_feed_member("you@test.local")
    for line in (
        "Account: already there",
        "Email: already confirmed",
        "Profile: already there",
        "already active on Rose",
        "ID check: already on file",
        "already accepted",
        "Feed: already joined",
    ):
        assert line in out, line
    assert Membership.objects.count() == 1
    assert Payment.objects.count() == 1
    assert IdCheck.objects.count() == 1


def test_make_feed_member_finishes_an_existing_account(dev, rose, make_user, make_membership):
    user = make_user(verified=False, email="half@test.local", display_name="half_way")
    user.profile.bio = "Here for the classes"
    user.profile.save()
    membership = make_membership(
        user=user, tier=rose, status="pending_payment", paid_awaiting_id_check=True
    )
    out = make_feed_member("half@test.local", "--tier", "rose")
    membership.refresh_from_db()
    assert membership.status == Membership.Status.ACTIVE
    assert "(already paid)" in out and "Password: unchanged" in out
    assert AuditLog.objects.filter(action="activate_after_id_check").exists()
    user.refresh_from_db()
    assert can_view_feed(user) and user.profile.bio == "Here for the classes"


def test_make_feed_member_refuses_a_tier_without_the_feed(dev, make_tier):
    make_tier(name="Community", slug="community", grants_feed_access=False)
    with pytest.raises(CommandError, match="does not include the member feed"):
        make_feed_member("you@test.local", "--tier", "community")


@pytest.mark.parametrize(
    ("debug", "env"),
    [(False, "development"), (True, "production"), (True, "staging"), (False, "production")],
)
def test_make_feed_member_refuses_to_run_outside_development(settings, rose, debug, env):
    settings.DEBUG = debug
    settings.DJANGO_ENV = env
    with pytest.raises(CommandError, match="only with DEBUG on"):
        make_feed_member("you@test.local")
    assert not Membership.objects.exists() and not SeedMarker.objects.exists()


# The checklist on Home


def path_for(client):
    response = client.get("/api/account/feed/path/")
    assert response.status_code == 200
    return response.json()


def states(data):
    return {step["key"]: step["state"] for step in data["steps"]}


def step(data, key):
    return next(item for item in data["steps"] if item["key"] == key)


@pytest.fixture
def as_user(client):
    def login(user):
        client.force_login(user)
        return client

    return login


def test_the_checklist_follows_each_stage(as_user, make_user, make_membership, rose, make_tier):
    user = make_user(verified=False)
    client = as_user(user)
    data = path_for(client)
    assert states(data) == {
        "email": "current",
        "plan": "upcoming",
        "door": "upcoming",
        "age": "upcoming",
        "join": "upcoming",
    }
    assert data["complete"] is False

    user.mark_email_verified()
    assert states(path_for(client))["plan"] == "current"

    # A plan that leaves the community out still needs choosing.
    community = make_tier(name="Community", slug="community", grants_feed_access=False)
    other = make_membership(user=user, tier=community, status="active")
    data = path_for(client)
    assert step(data, "plan") == {
        "key": "plan",
        "state": "current",
        "included": False,
        "tier": "Community",
    }
    other.end(Membership.Status.CANCELLED)
    other.save()
    IdCheck.objects.filter(user=user).delete()

    # Chosen, and waiting at the door: to pay, or (paid online) for the ID check.
    membership = make_membership(user=user, tier=rose, status="pending_payment")
    data = path_for(client)
    assert states(data)["plan"] == "done"
    assert step(data, "door") == {
        "key": "door",
        "state": "current",
        "included": False,
        "reference_code": membership.reference_code,
        "waiting_for": "payment",
    }
    membership.paid_awaiting_id_check = True
    membership.save()
    assert step(path_for(client), "door")["waiting_for"] == "id_check"

    # Switched on without an ID check yet (the check was switched on later).
    membership.status = Membership.Status.ACTIVE
    membership.paid_awaiting_id_check = False
    membership.start_new_period()
    membership.save()
    data = path_for(client)
    assert states(data)["door"] == "done" and states(data)["age"] == "current"
    assert step(data, "door")["reference_code"] is None

    verify_age(user)
    data = path_for(client)
    assert states(data)["join"] == "current"
    assert step(data, "join")["can_join"] is True

    from apps.feed import services

    services.join_feed(user, Guidelines.current().version)
    data = path_for(client)
    assert set(states(data).values()) == {"done"}
    assert data["complete"] is True


def test_the_age_step_is_hidden_while_the_check_is_off(as_user, make_user):
    settings = SiteSettings.load()
    settings.require_age_verification_for_feed = False
    settings.save()
    data = path_for(as_user(make_user()))
    assert [item["key"] for item in data["steps"]] == ["email", "plan", "door", "join"]


def test_feed_access_from_the_account_counts_as_included(as_user, make_user):
    user = make_user()
    user.profile.feed_access_granted = True
    user.profile.save()
    data = path_for(as_user(user))
    assert step(data, "plan")["included"] and step(data, "door")["included"]
    assert states(data) == {
        "email": "done",
        "plan": "done",
        "door": "done",
        "age": "current",
        "join": "upcoming",
    }
    assert step(data, "join")["early"] is True


def test_a_paused_account_is_told_so(as_user, make_member):
    member = make_member()
    member.profile.feed_suspended_until = timezone.now() + timedelta(days=3)
    member.profile.save()
    data = path_for(as_user(member))
    assert step(data, "join")["state"] == "current" and step(data, "join")["paused"] is True
    assert data["complete"] is False


def test_the_way_in_needs_an_account_and_the_feed(client, as_user, make_user, settings):
    assert client.get("/api/account/feed/path/").status_code == 403
    assert client.get("/api/account/feed/teaser/").status_code == 403
    settings.FEED_ENABLED = False
    member_client = as_user(make_user())
    assert member_client.get("/api/account/feed/path/").status_code == 404
    assert member_client.get("/api/account/feed/teaser/").status_code == 404


# The preview for accounts without the feed


def journal_post(gps_image_path, slug, author=None, minutes=0):
    post = JournalPost.objects.create(
        slug=slug,
        caption=f"From the club: {slug}",
        is_published=True,
        published_at=timezone.now() - timedelta(minutes=minutes),
        author=author,
    )
    JournalImage.objects.create(
        post=post,
        image=SimpleUploadedFile("x.jpg", gps_image_path.read_bytes(), content_type="image/jpeg"),
        image_alt=f"Photo for {slug}",
    )
    return post


def test_the_preview_shows_only_the_clubs_own_posts(
    as_user, make_user, make_member, make_post, admin_user, gps_image_path, member_client
):
    # Plenty of member content, with names, avatars and captions.
    poster_client, poster = member_client(display_name="secret_poster")
    poster_client.post(
        "/api/members/me/avatar/",
        {
            "image": SimpleUploadedFile(
                "a.jpg", gps_image_path.read_bytes(), content_type="image/jpeg"
            ),
            "shows_face": "false",
        },
        format="multipart",
    )
    poster.profile.refresh_from_db()
    assert poster.profile.avatar_key
    for n in range(3):
        make_post(poster, caption=f"secret member caption {n}")
    assert FeedPost.objects.filter(author=poster).count() == 3
    admin_user.display_name = "journal_author_name"
    admin_user.save()

    # The club's own: journal posts (one by a named staff author) and announcements.
    for n in range(3):
        journal_post(gps_image_path, f"club-{n}", author=admin_user, minutes=n * 10)
    Announcement.objects.create(
        title="New class on Thursday",
        body="Members-only details that the preview never shows.",
        starts_at=timezone.now() - timedelta(minutes=5),
        ends_at=timezone.now() + timedelta(days=2),
        is_published=True,
    )
    Announcement.objects.create(
        title="Draft notice",
        body="Not published",
        starts_at=timezone.now() - timedelta(minutes=5),
        ends_at=timezone.now() + timedelta(days=2),
    )

    response = as_user(make_user(display_name="looking_in")).get("/api/account/feed/teaser/")
    assert response.status_code == 200
    data = response.json()
    raw = json.dumps(data)

    for secret in (
        "secret_poster",
        "secret member caption",
        poster.profile.avatar_key,
        "/api/members/",
        "journal_author_name",
        "looking_in",
        "Members-only details",
        "Draft notice",
    ):
        assert secret not in raw, secret

    # Every tile is a journal photo or an announcement title, nothing else.
    assert [tile["kind"] for tile in data["tiles"]] == ["photo", "note", "photo", "photo"]
    assert data["tiles"][1] == {"kind": "note", "title": "New class on Thursday"}
    journal_urls = {image.image.url for image in JournalImage.objects.all()}
    for tile in data["tiles"]:
        if tile["kind"] == "photo":
            assert set(tile["image"]) == {"url", "srcset", "alt", "width", "height"}
            assert any(tile["image"]["url"].endswith(url) for url in journal_urls)

    # The card is the club's latest journal post, posted by the club, with no counts.
    post = data["post"]
    assert post["author"] == {"handle": "Rose", "avatar": None}
    assert post["slug"] == "club-0"
    assert set(post) == {"kind", "id", "slug", "author", "caption_html", "posted", "images", "link"}


def test_the_preview_is_empty_without_club_posts(as_user, make_user):
    data = as_user(make_user()).get("/api/account/feed/teaser/").json()
    assert data == {"tiles": [], "post": None}
