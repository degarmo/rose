"""Hiding a post: it leaves the hider's own feed and Explore, privately; nothing else changes."""

import json
import zipfile

import pytest

from apps.core.private_media import private_media
from apps.feed import services
from apps.feed.models import HiddenPost
from tests.test_feed_access import feed_routes

pytestmark = pytest.mark.django_db


def ids(response):
    return [item["id"] for item in response.json()["results"]]


def test_hiding_removes_a_post_from_your_feeds_only(member_client, make_member, make_post):
    client, hider = member_client(display_name="the_hider")
    other_client, _ = member_client(display_name="someone_else")
    author = make_member()
    post = make_post(author, images=1)
    keep = make_post(author, images=1)

    assert client.post(f"/api/members/posts/{post.public_id}/hide/").status_code == 200
    for path in ("/api/members/feed/?tab=everyone", "/api/members/home/?tab=everyone"):
        assert post.public_id not in ids(client.get(path)), path
        assert keep.public_id in ids(client.get(path)), path
        assert post.public_id in ids(other_client.get(path)), path
    # It can still be opened directly, and the author's profile still lists it.
    assert client.get(f"/api/members/posts/{post.public_id}/").status_code == 200
    assert post.public_id in ids(client.get(f"/api/members/u/{author.display_name}/posts/"))

    assert client.delete(f"/api/members/posts/{post.public_id}/hide/").status_code == 200
    assert post.public_id in ids(client.get("/api/members/feed/?tab=everyone"))


def test_hiding_is_private(member_client, make_member, make_post):
    author_client, author = member_client(display_name="the_author")
    _, hider = member_client(display_name="the_hider")
    post = make_post(author, images=1)
    services.hide_post(hider, post.public_id)
    payload = author_client.get(f"/api/members/posts/{post.public_id}/").json()
    assert not any("hid" in key for key in payload)
    for route in feed_routes():
        if "<" in route:
            continue
        body = author_client.get("/" + route).content.decode(errors="ignore")
        assert "the_hider" not in body, route


def test_cannot_hide_own_or_unseen_posts(member_client, make_member, make_post):
    client, viewer = member_client()
    own = make_post(viewer)
    assert client.post(f"/api/members/posts/{own.public_id}/hide/").status_code == 404
    author = make_member()
    blocked = make_post(author)
    services.block(author, viewer)
    assert client.post(f"/api/members/posts/{blocked.public_id}/hide/").status_code == 404
    assert not HiddenPost.objects.exists()


def test_hidden_posts_are_erased_and_exported(make_member, make_post, private_root):
    hider = make_member()
    post = make_post(make_member())
    services.hide_post(hider, post.public_id)

    export = services.request_export(hider)
    services.build_export(export)
    export.refresh_from_db()
    archive = zipfile.ZipFile(private_media().storage.open(export.file_name))
    data = json.loads(archive.read("data.json"))
    assert [row["post"] for row in data["hidden"]] == [post.public_id]

    services.erase_feed_data(hider)
    assert not HiddenPost.objects.filter(user=hider).exists()
