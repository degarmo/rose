"""Prompt 07 backend pieces: saved posts, appearance, stories and the home feed."""

import json
import zipfile
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.feed import club, services
from apps.feed.models import Announcement, FeedPost, SavedPost, StorySeen
from apps.journal.models import Post as JournalPost
from tests.test_feed_access import feed_routes

pytestmark = pytest.mark.django_db


@pytest.fixture
def make_journal():
    counter = {"n": 0}

    def make(minutes_ago=0, **kwargs):
        counter["n"] += 1
        defaults = {
            "slug": f"club-news-{counter['n']}",
            "caption": f"Club news {counter['n']}",
            "is_published": True,
            "published_at": timezone.now() - timedelta(minutes=minutes_ago),
        }
        defaults.update(kwargs)
        return JournalPost.objects.create(**defaults)

    return make


# Saved posts


def test_save_and_unsave_round_trip(member_client, make_member, make_post):
    client, saver = member_client()
    post = make_post(make_member(), images=1)
    saved = client.post(f"/api/members/posts/{post.public_id}/save/")
    assert saved.status_code == 200 and saved.json()["saved_by_me"] is True
    listing = client.get("/api/members/saved/").json()
    assert [item["id"] for item in listing["results"]] == [post.public_id]
    removed = client.delete(f"/api/members/posts/{post.public_id}/save/")
    assert removed.json()["saved_by_me"] is False
    assert client.get("/api/members/saved/").json()["results"] == []


def test_saves_are_private_to_the_saver(member_client, make_member, make_post):
    author_client, author = member_client(display_name="the_author")
    saver_client, saver = member_client(display_name="the_saver")
    other_client, _ = member_client(display_name="someone_else")
    post = make_post(author, images=1)
    services.save_post(saver, post.public_id)

    # Nobody else sees the bookmark, counts it, or gets the saver's list.
    for client in (author_client, other_client):
        assert client.get(f"/api/members/posts/{post.public_id}/").json()["saved_by_me"] is False
        assert client.get("/api/members/saved/").json()["results"] == []
    # No feed endpoint mentions who saved what.
    for route in feed_routes():
        if "<" in route:
            continue
        body = author_client.get("/" + route).content.decode(errors="ignore")
        assert "the_saver" not in body, route
    payload = author_client.get(f"/api/members/posts/{post.public_id}/").json()
    assert not any("save" in key and key != "saved_by_me" for key in payload)


def test_cannot_save_a_post_you_cannot_see(member_client, make_member, make_post):
    client, viewer = member_client()
    author = make_member()
    post = make_post(author)
    services.block(author, viewer)
    assert client.post(f"/api/members/posts/{post.public_id}/save/").status_code == 404
    pending = make_post(make_member(), premoderation=5)
    assert client.post(f"/api/members/posts/{pending.public_id}/save/").status_code == 404
    assert not SavedPost.objects.exists()


def test_hidden_or_removed_posts_leave_saved_lists(make_member, make_post, admin_user):
    saver = make_member()
    reported = make_post(make_member())
    removed = make_post(make_member())
    for post in (reported, removed):
        services.save_post(saver, post.public_id)
    services.report(make_member(), "post", reported, "no_consent")
    services.moderate(admin_user, "remove", "post", removed, reason="Off topic")
    assert not SavedPost.objects.filter(user=saver).exists()


def test_erasure_deletes_saves_and_seen_stories(make_member, make_post):
    saver = make_member()
    services.save_post(saver, make_post(make_member()).public_id)
    services.mark_stories_seen(saver, ["journal:x"])
    services.erase_feed_data(saver)
    assert not SavedPost.objects.filter(user=saver).exists()
    assert not StorySeen.objects.filter(user=saver).exists()


def test_erasing_the_author_removes_their_post_from_saved_lists(make_member, make_post):
    saver, author = make_member(), make_member()
    services.save_post(saver, make_post(author).public_id)
    services.erase_feed_data(author)
    assert not SavedPost.objects.exists()


def test_export_includes_saved_posts_and_seen_stories(make_member, make_post, private_root):
    saver = make_member()
    post = make_post(make_member())
    services.save_post(saver, post.public_id)
    services.mark_stories_seen(saver, ["journal:spring"])
    export = services.request_export(saver)
    services.build_export(export)
    export.refresh_from_db()
    from apps.core.private_media import private_media

    archive = zipfile.ZipFile(private_media().storage.open(export.file_name))
    data = json.loads(archive.read("data.json"))
    assert [row["post"] for row in data["saved"]] == [post.public_id]
    assert [row["story"] for row in data["stories_seen"]] == ["journal:spring"]


# Image sizes and profile counts


def test_processed_images_record_their_size(member_client, make_post):
    client, author = member_client()
    post = make_post(author, images=1)
    image = client.get(f"/api/members/posts/{post.public_id}/").json()["images"][0]
    assert image["width"] > 0 and image["height"] > 0


def test_profile_counts_posts_only(member_client, make_member, make_post):
    client, _ = member_client()
    author = make_member(display_name="counted")
    make_post(author)
    make_post(author)
    profile = client.get("/api/members/u/counted/").json()
    assert profile["post_count"] == 2
    assert not {"followers", "following", "follower_count", "following_count"} & set(profile)


def test_recent_comments_are_the_two_newest(member_client, make_member, make_post):
    client, viewer = member_client()
    post = make_post(make_member())
    for body in ("one", "two", "three"):
        services.add_comment(viewer, post.public_id, body)
    data = client.get(f"/api/members/posts/{post.public_id}/").json()
    assert [c["body_html"] for c in data["recent_comments"]] == ["two", "three"]
    assert data["comment_count"] == 3


# Appearance and the session


def test_appearance_defaults_to_light_and_persists(signed_in):
    csrf_client, user = signed_in()
    assert csrf_client.get("/api/account/session/").json()["user"]["appearance"] == "light"
    response = csrf_client.patch("/api/account/session/", {"appearance": "dark"}, format="json")
    assert response.status_code == 200
    assert response.json()["user"]["appearance"] == "dark"
    user.refresh_from_db()
    assert user.appearance == "dark"


def test_appearance_rejects_unknown_values_and_empty_changes(signed_in):
    csrf_client, _ = signed_in()
    bad = csrf_client.patch("/api/account/session/", {"appearance": "sepia"}, format="json")
    assert bad.status_code == 400
    assert csrf_client.patch("/api/account/session/", {}, format="json").status_code == 400


def test_display_name_change_still_works_alone(signed_in):
    csrf_client, user = signed_in()
    response = csrf_client.patch(
        "/api/account/session/", {"display_name": "new_name"}, format="json"
    )
    assert response.json()["user"]["display_name"] == "new_name"
    user.refresh_from_db()
    assert user.appearance == "light"


def test_session_reports_feed_access(make_member, make_user, client):
    client.force_login(make_member())
    assert client.get("/api/account/session/").json()["user"]["feed_access"] is True
    client.force_login(make_user())
    assert client.get("/api/account/session/").json()["user"]["feed_access"] is False


# Stories


def test_stories_group_events_journal_and_news(member_client, make_event, make_journal):
    client, _ = member_client()
    now = timezone.now()
    local_now = timezone.localtime(now)
    tonight_start = local_now.replace(hour=23, minute=0, second=0, microsecond=0)
    if tonight_start <= local_now:
        tonight_start = local_now + timedelta(minutes=1)
    make_event(title="Later tonight", slug="later-tonight", starts_at=tonight_start)
    make_event(title="In three days", slug="in-three-days", starts_at=now + timedelta(days=3))
    make_event(title="Too far", slug="too-far", starts_at=now + timedelta(days=20))
    make_journal(caption="A short club note")
    Announcement.objects.create(
        title="Coat check", body="Bring a bag.", ends_at=now + timedelta(days=1), is_published=True
    )
    Announcement.objects.create(
        title="Expired",
        body="Gone.",
        ends_at=now - timedelta(minutes=1),
        is_published=True,
        starts_at=now - timedelta(days=1),
    )
    groups = {g["id"]: g for g in client.get("/api/members/stories/").json()["results"]}
    assert [i["title"] for i in groups["tonight"]["items"]] == ["Later tonight"]
    assert [i["title"] for i in groups["this-week"]["items"]] == ["In three days"]
    assert groups["journal"]["items"][0]["text"] == "A short club note"
    assert [i["title"] for i in groups["news"]["items"]] == ["Coat check"]
    assert groups["this-week"]["items"][0]["link"] == {
        "label": "RSVP",
        "url": "/events/in-three-days",
    }
    assert all(group["seen"] is False for group in groups.values())


def test_stories_seen_state_is_per_member(member_client, make_event):
    first, _ = member_client()
    second, _ = member_client()
    make_event(slug="soon", starts_at=timezone.now() + timedelta(days=2))
    group = first.get("/api/members/stories/").json()["results"][0]
    key = group["items"][0]["key"]
    assert (
        first.post("/api/members/stories/seen/", {"keys": [key]}, format="json").status_code == 200
    )
    first.post("/api/members/stories/seen/", {"keys": [key]}, format="json")  # idempotent
    assert first.get("/api/members/stories/").json()["results"][0]["seen"] is True
    assert second.get("/api/members/stories/").json()["results"][0]["seen"] is False


@pytest.mark.parametrize("keys", [None, [], "event:x", [1], ["x" * 81], ["k"] * 51])
def test_story_keys_are_validated(member_client, keys):
    client, _ = member_client()
    response = client.post("/api/members/stories/seen/", {"keys": keys}, format="json")
    assert response.status_code == 400


def test_announcement_needs_both_link_parts_and_a_later_end():
    from django.core.exceptions import ValidationError

    now = timezone.now()
    with pytest.raises(ValidationError):
        Announcement(
            title="x", body="y", link_label="Go", starts_at=now, ends_at=now + timedelta(hours=1)
        ).full_clean()
    with pytest.raises(ValidationError):
        Announcement(title="x", body="y", starts_at=now, ends_at=now).full_clean()


# The home feed


def test_home_interleaves_club_posts_by_date(member_client, make_member, make_post, make_journal):
    client, _ = member_client()
    author = make_member(display_name="poster")
    older = make_post(author, caption="older")
    FeedPost.objects.filter(pk=older.pk).update(created_at=timezone.now() - timedelta(hours=3))
    make_journal(minutes_ago=60, caption="Club note")
    make_post(author, caption="newest")
    results = client.get("/api/members/home/").json()["results"]
    assert [(r["kind"], r["author"]["handle"]) for r in results] == [
        ("member", "poster"),
        ("club", club.CLUB_HANDLE),
        ("member", "poster"),
    ]
    club_post = results[1]
    assert club_post["link"]["url"].startswith("/journal/")
    assert "like_count" not in club_post and "liked_by_me" not in club_post


def test_home_pages_without_repeats(member_client, make_member, make_post, make_journal):
    client, _ = member_client()
    author = make_member()
    for index in range(8):
        make_post(author, caption=f"m{index}")
        make_journal(minutes_ago=index, caption=f"c{index}")
    seen, url = [], "/api/members/home/"
    while url:
        page = client.get(url).json()
        seen += [item["id"] for item in page["results"]]
        url = page["next"]
    assert len(seen) == 16 and len(set(seen)) == 16


def test_home_cursor_holds_no_database_ids(member_client, make_member, make_post, settings):
    settings.FEED_MAX_POSTS_PER_DAY = 20
    client, _ = member_client()
    author = make_member()
    posts = [make_post(author) for _ in range(12)]
    page = client.get("/api/members/home/").json()
    raw = page["next"].split("cursor=")[1]
    from urllib.parse import unquote

    decoded = json.dumps(club.decode_cursor(unquote(raw)), default=str)
    assert all(str(post.pk) not in decoded.split('"') for post in posts)
    assert client.get("/api/members/home/?cursor=not-a-cursor").status_code == 400


def test_home_following_tab_keeps_club_posts(member_client, make_member, make_post, make_journal):
    client, _ = member_client()
    make_post(make_member(), caption="stranger")
    make_journal()
    kinds = [r["kind"] for r in client.get("/api/members/home/?tab=following").json()["results"]]
    assert kinds == ["club"]
