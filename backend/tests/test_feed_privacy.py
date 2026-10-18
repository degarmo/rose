"""Nothing in the feed reveals who liked what, who follows whom, or any RSVP."""

import importlib
import inspect
import re

import pytest
from django.urls import get_resolver
from rest_framework import serializers

from apps.events.services import submit_rsvp
from apps.feed import services

pytestmark = pytest.mark.django_db

FORBIDDEN_FIELDS = re.compile(
    r"liker|liked_by(?!_me$)|likes$|follower|following_count|followers|follows|rsvp|attend|going|email|legal_name|phone"
)


def feed_serializers():
    module = importlib.import_module("apps.feed.serializers")
    return [
        obj
        for _, obj in inspect.getmembers(module, inspect.isclass)
        if issubclass(obj, serializers.BaseSerializer) and obj.__module__ == module.__name__
    ]


@pytest.mark.parametrize("serializer_class", feed_serializers(), ids=lambda c: c.__name__)
def test_no_serializer_field_reveals_likes_follows_or_rsvps(serializer_class):
    fields = serializer_class().fields
    for name in fields:
        assert not FORBIDDEN_FIELDS.search(name), f"{serializer_class.__name__}.{name}"


def feed_routes():
    def walk(patterns, prefix=""):
        for pattern in patterns:
            route = prefix + str(pattern.pattern)
            if hasattr(pattern, "url_patterns"):
                yield from walk(pattern.url_patterns, route)
            else:
                yield route, pattern.name

    return [
        r
        for r in walk(get_resolver().url_patterns)
        if r[0].startswith(("api/members/", "api/account/feed/"))
    ]


def test_no_endpoint_reveals_likers_followers_or_rsvps(
    member_client, make_post, make_member, make_event, image_upload
):
    author_client, author = member_client(display_name="post_author")
    post = make_post(author, images=1)
    liker = make_member(display_name="secret_liker")
    follower = make_member(display_name="secret_follower")
    services.like(liker, post.public_id)
    services.follow(follower, author)
    event = make_event(title="Very Private Evening")
    submit_rsvp(author, event, 1)
    secrets = ["secret_liker", "secret_follower", "Very Private Evening", event.slug, author.email]

    viewers = [("author", author_client)]
    other_client, _ = member_client()
    viewers.append(("other", other_client))
    for name, client in viewers:
        for route, route_name in feed_routes():
            url = "/" + re.sub(
                r"<(?:\w+:)?(\w+)>",
                lambda m: {
                    "public_id": post.public_id,
                    "handle": "post_author",
                    "kind": "follow",
                    "key": "x",
                }[m.group(1)],
                route,
            )
            if route_name in ("feed-member-relationship",):
                continue
            body = client.get(url).content.decode(errors="ignore")
            for secret in secrets:
                assert secret not in body, f"{name} saw {secret!r} at {url}"
        notes = client.get("/api/members/notifications/").content.decode()
        assert "secret_liker" not in notes
