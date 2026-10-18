from datetime import timedelta
from io import BytesIO

import pytest
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.core.private_media import private_media
from apps.feed import services
from apps.feed.models import FeedPost

pytestmark = pytest.mark.django_db


@pytest.fixture
def photo(make_member, make_post):
    author = make_member(display_name="photo_author")
    post = make_post(author, images=1)
    image = post.images.get()
    return {
        "author": author,
        "post": post,
        "url": f"/api/members/media/{image.public_id}/",
        "image": image,
    }


def test_member_gets_private_headers(member_client, photo, settings):
    settings.FEED_WATERMARK = False
    client, _ = member_client()
    response = client.get(photo["url"])
    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store, max-age=0"
    assert response["Content-Disposition"] == "inline"
    assert response["Content-Type"] == "image/webp"
    body = b"".join(response.streaming_content)
    assert body == private_media().read(photo["image"].image.name)


def test_private_storage_has_no_public_url(photo):
    with pytest.raises(RuntimeError):
        _ = photo["image"].image.url


@pytest.mark.parametrize(
    "case",
    [
        "anonymous",
        "unverified",
        "not_entitled",
        "opted_out",
        "banned",
        "suspended",
        "blocked",
        "removed",
        "hidden",
        "pending",
        "author_opted_out",
    ],
)
def test_media_denied(case, photo, member_client, make_user, make_member, admin_user):
    client = APIClient()
    if case in ("unverified", "not_entitled"):
        client.force_login(make_user(verified=case != "unverified"))
    elif case in ("opted_out", "banned", "suspended"):
        user = make_member()
        if case == "opted_out":
            user.profile.set_feed_participation(False)
        elif case == "banned":
            user.profile.feed_banned_at = timezone.now()
            user.profile.save()
        else:
            user.profile.feed_suspended_until = timezone.now() + timedelta(days=1)
            user.profile.save()
        client.force_login(user)
    elif case != "anonymous":
        client, viewer = member_client()
        post = photo["post"]
        if case == "blocked":
            services.block(photo["author"], viewer)
        elif case == "removed":
            services.moderate(admin_user, "remove", "post", post, reason="x")
        elif case == "hidden":
            FeedPost.objects.filter(pk=post.pk).update(status=FeedPost.Status.HIDDEN_BY_REPORT)
        elif case == "pending":
            FeedPost.objects.filter(pk=post.pk).update(status=FeedPost.Status.PENDING)
        elif case == "author_opted_out":
            photo["author"].profile.set_feed_participation(False)
    assert client.get(photo["url"]).status_code == 404


def test_author_sees_own_pending_image(photo, member_client):
    FeedPost.objects.filter(pk=photo["post"].pk).update(status=FeedPost.Status.PENDING)
    client, _ = member_client(user=photo["author"])
    assert client.get(photo["url"]).status_code == 200


def test_watermark_applied_when_enabled(member_client, photo, settings):
    settings.FEED_WATERMARK = True
    client, viewer = member_client(display_name="watching_one")
    response = client.get(photo["url"])
    assert response.status_code == 200
    marked = b"".join(response.streaming_content)
    original = private_media().read(photo["image"].image.name)
    assert marked != original
    with Image.open(BytesIO(marked)) as marked_image, Image.open(BytesIO(original)) as source:
        assert marked_image.size == source.size
        assert marked_image.format == "WEBP"
        assert len(marked_image.getexif()) == 0
    assert b"".join(client.get(photo["url"]).streaming_content) == marked

    other, _ = member_client(display_name="another_one")
    assert b"".join(other.get(photo["url"]).streaming_content) != marked


def test_avatar_media_rules(member_client, image_upload):
    owner_client, owner = member_client(display_name="avatar_owner")
    owner_client.post(
        "/api/members/me/avatar/",
        {"image": image_upload(), "shows_face": "false"},
        format="multipart",
    )
    owner.profile.refresh_from_db()
    url = f"/api/members/avatars/{owner.profile.avatar_key}/"
    viewer, viewer_user = member_client()
    assert viewer.get(url).status_code == 200
    services.block(owner, viewer_user)
    assert viewer.get(url).status_code == 404
    assert APIClient().get(url).status_code == 404
