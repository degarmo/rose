"""Every members-area URL returns 404 to anyone without feed access, whatever the method."""

from datetime import timedelta

import pytest
from django.urls import get_resolver
from django.utils import timezone
from rest_framework.test import APIClient

from apps.feed import access
from apps.feed.models import Guidelines

from .conftest import csrf_client_for

pytestmark = pytest.mark.django_db

METHODS = ["get", "post", "patch", "delete"]


def feed_routes():
    def walk(patterns, prefix=""):
        for pattern in patterns:
            route = prefix + str(pattern.pattern)
            if hasattr(pattern, "url_patterns"):
                yield from walk(pattern.url_patterns, route)
            else:
                yield route

    routes = [r for r in walk(get_resolver().url_patterns) if r.startswith("api/members/")]
    assert len(routes) >= 15
    return routes


def concrete(route, post_id, handle):
    import re

    values = {"public_id": post_id, "handle": handle, "kind": "follow", "key": "somekey"}
    return "/" + re.sub(r"<(?:\w+:)?(\w+)>", lambda m: values[m.group(1)], route)


@pytest.fixture
def world(make_member, make_post, make_user):
    author = make_member(display_name="feed_author")
    post = make_post(author, images=1)
    people = {
        "anonymous": None,
        "unverified": make_user(verified=False),
        "not_entitled": make_user(),
    }
    opted_out = make_member()
    opted_out.profile.set_feed_participation(False)
    people["opted_out"] = opted_out
    banned = make_member()
    banned.profile.feed_banned_at = timezone.now()
    banned.profile.save()
    people["banned"] = banned
    suspended = make_member()
    suspended.profile.feed_suspended_until = timezone.now() + timedelta(days=2)
    suspended.profile.save()
    people["suspended"] = suspended
    unverified_entitled = make_user(verified=False)
    unverified_entitled.profile.feed_access_granted = True
    unverified_entitled.profile.participates_in_feed = True
    unverified_entitled.profile.save()
    people["entitled_but_unverified"] = unverified_entitled
    return {"author": author, "post": post, "people": people}


@pytest.mark.parametrize(
    "person",
    [
        "anonymous",
        "unverified",
        "opted_out",
        "not_entitled",
        "banned",
        "suspended",
        "entitled_but_unverified",
    ],
)
def test_every_feed_url_is_404_without_access(world, person):
    user = world["people"][person]
    with_csrf = APIClient(enforce_csrf_checks=True)
    without_csrf = APIClient(enforce_csrf_checks=True)
    if user is not None:
        with_csrf.force_login(user)
        without_csrf.force_login(user)
    with_csrf = csrf_client_for(with_csrf)
    checked = 0
    for route in feed_routes():
        url = concrete(route, world["post"].public_id, "feed_author")
        for method in METHODS:
            for client in (with_csrf, without_csrf):
                response = getattr(client, method)(url, {}, format="json")
                assert response.status_code == 404, (
                    f"{person} {method.upper()} {url} -> {response.status_code}"
                )
                checked += 1
    assert checked >= len(feed_routes()) * 8


def test_member_can_reach_feed(member_client):
    client, _ = member_client()
    assert client.get("/api/members/feed/").status_code == 200
    assert client.get("/api/members/me/").status_code == 200


def test_404_body_is_identical_to_unknown_path(world):
    client = APIClient()
    feed = client.get("/api/members/feed/")
    unknown = client.get("/api/members/does-not-exist/")
    assert feed.status_code == unknown.status_code == 404


def test_access_functions(make_user, make_member, settings):
    plain = make_user()
    assert not access.can_view_feed(plain)
    assert not access.can_join_feed(plain)
    plain.profile.feed_access_granted = True
    plain.profile.save()
    assert access.can_join_feed(plain)
    assert not access.can_view_feed(plain)

    member = make_member()
    assert access.can_view_feed(member)
    assert access.can_post(member)

    member.profile.posting_cooldown_until = timezone.now() + timedelta(hours=1)
    member.profile.save()
    assert access.can_view_feed(member)
    assert access.post_block_reason(member) == access.COOLDOWN
    assert not access.can_post(member)


def test_staff_grant_gives_feed_entitlement(make_user):
    user = make_user()
    assert access.has_feed_entitlement(user) is False
    user.profile.feed_access_granted = True
    user.profile.save()
    assert access.has_feed_entitlement(user) is True


def test_account_feed_endpoints_hidden_without_entitlement(signed_in, make_user):
    client, user = signed_in()
    assert client.get("/api/account/feed/").status_code == 404
    assert client.post("/api/account/feed/join/", {}, format="json").status_code == 404
    user.profile.feed_access_granted = True
    user.profile.save()
    body = client.get("/api/account/feed/").json()
    assert body["can_join"] is True and body["participating"] is False
    assert body["guidelines"]["version"] == Guidelines.current().version


def test_admin_records_who_granted_access(admin_client, admin_user, make_user):
    user = make_user()
    profile = user.profile
    admin_client.post(
        "/admin/accounts/profile/",
        {"action": "grant_feed_access", "_selected_action": [profile.pk]},
    )
    profile.refresh_from_db()
    assert profile.feed_access_granted
    assert profile.feed_access_granted_by == admin_user
    assert profile.feed_access_granted_at is not None
    admin_client.post(
        "/admin/accounts/profile/",
        {"action": "revoke_feed_access", "_selected_action": [profile.pk]},
    )
    profile.refresh_from_db()
    assert not profile.feed_access_granted and profile.feed_access_granted_by is None


@pytest.mark.parametrize("method", ["get", "post"])
@pytest.mark.parametrize(
    "path", ["/api/account/feed/", "/api/account/feed/join/", "/api/account/feed/erase/"]
)
def test_account_feed_endpoints_are_404_when_signed_out(client, path, method):
    """Not 403: a signed-out visitor learns nothing about which endpoints exist."""
    response = getattr(client, method)(path)
    assert response.status_code == 404
