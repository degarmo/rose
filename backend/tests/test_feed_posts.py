import re
from datetime import timedelta
from io import BytesIO

import pytest
from django.utils import timezone
from PIL import ExifTags, Image

from apps.core.private_media import private_media
from apps.feed import services
from apps.feed.models import FeedImage, FeedPost

pytestmark = pytest.mark.django_db
RANDOM_NAME = re.compile(r"^feed/[0-9a-f]{32}\.webp$")


def create(client, images=(), **data):
    payload = {"caption": "A caption", "consent_attested": "true", **data}
    payload["images"] = list(images)
    return client.post("/api/members/feed/", payload, format="multipart")


def test_post_with_images_is_processed_and_stripped(
    member_client, image_upload, settings, private_root
):
    settings.FEED_PREMODERATION_POSTS = 0
    client, user = member_client()
    response = create(client, [image_upload("my-home.jpg"), image_upload()], alt=["Candles", ""])
    assert response.status_code == 201
    post = FeedPost.objects.get(author=user)
    assert post.status == FeedPost.Status.PUBLISHED
    assert post.is_processing is False
    assert post.consent_attested_at is not None
    images = list(post.images.all())
    assert [i.image_alt for i in images] == ["Candles", ""]
    media = private_media()
    for image in images:
        assert RANDOM_NAME.match(image.image.name)
        assert "my-home" not in image.image.name
        assert not image.incoming
        with Image.open(BytesIO(media.read(image.image.name))) as stored:
            assert stored.format == "WEBP"
            assert len(stored.getexif()) == 0
            assert len(stored.getexif().get_ifd(ExifTags.IFD.GPSInfo)) == 0
            assert not stored.info.get("icc_profile")
    assert list(private_root.glob("incoming/*")) == []


def test_processing_state_shown_only_to_author(make_member, make_post, monkeypatch):
    author = make_member()
    viewer = make_member()
    monkeypatch.setattr("apps.feed.tasks.process_post_images.delay", lambda post_id: None)
    post = make_post(author, images=1)
    assert post.is_processing
    from apps.feed.visibility import visible_posts

    assert visible_posts(author).filter(pk=post.pk).exists()
    assert not visible_posts(viewer).filter(pk=post.pk).exists()
    services.process_images(post.pk)
    post.refresh_from_db()
    assert not post.is_processing
    assert visible_posts(viewer).filter(pk=post.pk).exists()


def test_images_require_attestation(member_client, image_upload):
    client, user = member_client()
    response = create(client, [image_upload()], consent_attested="false")
    assert response.status_code == 400
    assert response.json()["code"] == "attestation"
    assert not FeedPost.objects.exists()


def test_text_only_posts_need_no_attestation(member_client):
    client, _ = member_client()
    assert create(client, consent_attested="false").status_code == 201


def test_empty_and_oversized_posts_rejected(member_client, image_upload):
    client, _ = member_client()
    assert create(client, caption="").json()["code"] == "empty"
    too_many = [image_upload() for _ in range(11)]
    assert create(client, too_many).status_code == 400


def test_non_images_rejected(member_client):
    from django.core.files.uploadedfile import SimpleUploadedFile

    client, _ = member_client()
    bogus = SimpleUploadedFile("x.jpg", b"not an image", content_type="image/jpeg")
    assert create(client, [bogus]).json()["code"] == "image_invalid"


def test_premoderation_threshold(member_client, settings, admin_user):
    settings.FEED_PREMODERATION_POSTS = 2
    client, user = member_client()
    for _ in range(3):
        create(client)
    statuses = list(
        FeedPost.objects.filter(author=user).order_by("created_at").values_list("status", flat=True)
    )
    assert statuses == ["pending", "pending", "pending"]

    for post in FeedPost.objects.filter(author=user).order_by("created_at")[:2]:
        services.moderate(admin_user, "approve", "post", post)
    create(client)
    assert FeedPost.objects.filter(author=user).latest("created_at").status == "published"


def test_daily_post_limit(member_client, settings):
    settings.FEED_MAX_POSTS_PER_DAY = 2
    client, _ = member_client()
    statuses = [create(client).status_code for _ in range(3)]
    assert statuses == [201, 201, 429]


def test_hourly_comment_limit(member_client, make_post, settings):
    settings.FEED_MAX_COMMENTS_PER_HOUR = 2
    author_client, author = member_client()
    post = make_post(author)
    client, _ = member_client()
    statuses = [
        client.post(
            f"/api/members/posts/{post.public_id}/comments/", {"body": "Hi"}, format="json"
        ).status_code
        for _ in range(3)
    ]
    assert statuses == [201, 201, 429]


def test_edit_only_caption_and_toggles(member_client, make_post):
    client, author = member_client()
    post = make_post(author, images=1)
    response = client.patch(
        f"/api/members/posts/{post.public_id}/",
        {"caption": "New words", "is_sensitive": True, "comments_enabled": False, "images": []},
        format="json",
    )
    assert response.status_code == 200
    post.refresh_from_db()
    assert (post.caption, post.is_sensitive, post.comments_enabled) == ("New words", True, False)
    assert post.edited_at is not None
    assert post.images.count() == 1

    other, _ = member_client()
    assert (
        other.patch(
            f"/api/members/posts/{post.public_id}/", {"caption": "x"}, format="json"
        ).status_code
        == 404
    )


def test_delete_removes_files(member_client, make_post, private_root):
    client, author = member_client()
    post = make_post(author, images=2)
    names = [image.image.name for image in post.images.all()]
    assert all((private_root / name).exists() for name in names)
    assert client.delete(f"/api/members/posts/{post.public_id}/").status_code == 204
    assert not FeedPost.objects.filter(pk=post.pk).exists()
    assert not any((private_root / name).exists() for name in names)


def test_payload_shape_blur_and_dates(member_client, make_post, make_member):
    author = make_member()
    post = make_post(author, caption="Line one\nhttps://example.org/x", is_sensitive=True, images=1)
    old = make_post(author, caption="Older")
    FeedPost.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=40))
    client, viewer = member_client()

    data = client.get(f"/api/members/posts/{post.public_id}/").json()
    assert data["is_sensitive"] is True and data["blur"] is True
    assert data["caption"] is None
    assert data["like_count"] is None
    assert (
        '<a href="https://example.org/x" rel="noopener noreferrer nofollow">'
        in data["caption_html"]
    )
    assert data["posted"]["recent"] is True and data["posted"]["at"]
    assert data["images"][0]["url"] == f"/api/members/media/{post.images.first().public_id}/"
    assert "state" in data and data["state"] is None

    old_data = client.get(f"/api/members/posts/{old.public_id}/").json()
    assert old_data["posted"] == {"recent": False, "at": None, "month": old_data["posted"]["month"]}
    assert re.match(r"^\d{4}-\d{2}$", old_data["posted"]["month"])

    viewer.profile.always_show_sensitive = True
    viewer.profile.save()
    assert client.get(f"/api/members/posts/{post.public_id}/").json()["blur"] is False


def test_author_never_blurred_and_sees_state(member_client, make_post, settings):
    client, author = member_client()
    post = make_post(author, is_sensitive=True, premoderation=5)
    data = client.get(f"/api/members/posts/{post.public_id}/").json()
    assert data["blur"] is False
    assert data["state"] == "pending"
    assert data["caption"] == "Hello"


def test_failed_processing_drops_bad_image(make_member, make_post, monkeypatch):
    author = make_member()
    monkeypatch.setattr("apps.feed.tasks.process_post_images.delay", lambda post_id: None)
    post = make_post(author, caption="", images=1)
    image = post.images.get()
    media = private_media()
    with media.storage.open(image.incoming.name, "wb") as handle:
        handle.write(b"corrupted after upload")
    services.process_images(post.pk)
    post.refresh_from_db()
    assert not FeedImage.objects.filter(pk=image.pk).exists()
    assert post.status == FeedPost.Status.REMOVED
