"""Object storage against a real S3 API (MinIO): signed delivery, watermarks, erasure,
account deletion, the media migration and backups."""

import hashlib
import urllib.error
import urllib.request
from io import StringIO
from urllib.parse import parse_qs, urlsplit

import pyrage
import pytest
from django.core.files.storage import storages
from django.core.management import CommandError, call_command
from PIL import Image

from tests.conftest import PASSWORD

pytestmark = pytest.mark.django_db


@pytest.fixture
def photo(s3, make_member, make_post):
    author = make_member(display_name="photo_author")
    post = make_post(author, images=1)
    image = post.images.get()
    return {
        "author": author,
        "post": post,
        "image": image,
        "url": f"/api/members/media/{image.public_id}/",
    }


def fetch(url):
    with urllib.request.urlopen(url, timeout=5) as reply:
        return reply.status, dict(reply.headers), reply.read()


def test_uploads_land_in_the_private_bucket(s3, photo):
    keys = s3.keys(s3.private)
    assert photo["image"].image.name in keys
    assert not any(key.startswith("incoming/") for key in keys)  # raw upload discarded
    assert s3.keys(s3.public) == []


def test_private_media_redirects_to_a_60_second_signed_url(s3, photo, member_client, settings):
    settings.FEED_WATERMARK = False
    client, _ = member_client()
    response = client.get(photo["url"])
    assert response.status_code == 302
    assert response["Cache-Control"] == "private, no-store, max-age=0"
    location = response["Location"]
    query = parse_qs(urlsplit(location).query)
    assert query["X-Amz-Expires"] == ["60"]
    assert query["response-cache-control"] == ["private, no-store, max-age=0"]
    status, headers, body = fetch(location)
    assert status == 200 and headers["Cache-Control"] == "private, no-store, max-age=0"
    assert body[:4] == b"RIFF"


def test_private_objects_are_not_public(s3, photo):
    url = f"{settings_endpoint()}/{s3.private}/{photo['image'].image.name}"
    with pytest.raises(urllib.error.HTTPError) as error:
        fetch(url)
    assert error.value.code == 403
    with pytest.raises(urllib.error.HTTPError) as listing:
        fetch(f"{settings_endpoint()}/{s3.private}/")
    assert listing.value.code == 403


def settings_endpoint():
    from tests.conftest import S3_TEST_ENDPOINT

    return S3_TEST_ENDPOINT


def test_access_is_checked_before_any_url_is_signed(s3, photo, signed_in):
    client, _ = signed_in()  # not a feed member
    response = client.get(photo["url"])
    assert response.status_code == 404
    assert "Location" not in response


def test_watermarked_copy_is_made_once_per_viewer(s3, photo, member_client, settings):
    settings.FEED_WATERMARK = True
    viewer, _ = member_client(display_name="watching_one")
    first = viewer.get(photo["url"])
    second = viewer.get(photo["url"])
    marks = s3.keys(s3.private, "watermarks/")
    assert len(marks) == 1
    assert urlsplit(first["Location"]).path.endswith(marks[0])
    assert urlsplit(second["Location"]).path.endswith(marks[0])
    _, _, body = fetch(first["Location"])
    original = storages["private"].open(photo["image"].image.name).read()
    assert body != original
    other, _ = member_client(display_name="another_one")
    other.get(photo["url"])
    assert len(s3.keys(s3.private, "watermarks/")) == 2


def test_leave_and_erase_deletes_objects(
    s3, photo, member_client, settings, run_on_commit_immediately
):
    settings.FEED_WATERMARK = True
    viewer, viewer_user = member_client(display_name="watching_one")
    viewer.get(photo["url"])
    author_client, author = member_client(user=photo["author"])
    assert s3.keys(s3.private, "feed/") and s3.keys(s3.private, "watermarks/")
    response = author_client.post(
        "/api/account/feed/erase/", {"display_name": author.display_name}, format="json"
    )
    assert response.status_code == 202
    assert s3.keys(s3.private, "feed/") == []
    assert s3.keys(s3.private, "watermarks/") == []  # every viewer's copy of the photo


def test_account_deletion_deletes_objects(s3, photo, member_client, settings):
    settings.FEED_WATERMARK = True
    client, author = member_client(user=photo["author"])
    client.get(photo["url"])  # the author's own watermarked copy
    assert s3.keys(s3.private)
    response = client.post("/api/account/delete/", {"password": PASSWORD}, format="json")
    assert response.status_code == 200
    assert s3.keys(s3.private) == []


def test_viewer_deletion_removes_copies_bearing_their_name(s3, photo, member_client, settings):
    settings.FEED_WATERMARK = True
    viewer, viewer_user = member_client(display_name="watching_one")
    viewer.get(photo["url"])
    assert len(s3.keys(s3.private, "watermarks/")) == 1
    viewer.post("/api/account/delete/", {"password": PASSWORD}, format="json")
    assert s3.keys(s3.private, "watermarks/") == []
    assert photo["image"].image.name in s3.keys(s3.private)


def test_public_images_are_served_from_the_public_bucket_with_a_long_cache(s3):
    from django.core.files.base import ContentFile

    from apps.education.models import Opportunity

    item = Opportunity(title="Class", slug="class", summary="s", body="b", is_published=True)
    buffer = __import__("io").BytesIO()
    Image.new("RGB", (32, 32), (90, 20, 30)).save(buffer, format="PNG")
    # Assigned like an admin upload, so the field sanitises it on save.
    item.hero_image = ContentFile(buffer.getvalue(), name="hero.png")
    item.hero_image_alt = "A red square"
    item.hero_image_faces_visible = False
    item.save()
    url = item.hero_image.url
    assert url.startswith(f"{settings_endpoint()}/{s3.public}/")
    status, headers, body = fetch(url)
    assert status == 200
    assert headers["Cache-Control"] == "public, max-age=31536000, immutable"
    assert body[:4] == b"RIFF"


# migrate_media_to_storage


@pytest.fixture
def local_media(settings, tmp_path):
    public = tmp_path / "media"
    private = tmp_path / "private"
    (public / "journal").mkdir(parents=True)
    (private / "feed").mkdir(parents=True)
    (private / "watermark-cache").mkdir(parents=True)
    (public / "journal" / "a.webp").write_bytes(b"public-image" * 100)
    (private / "feed" / "b.webp").write_bytes(b"private-image" * 100)
    (private / "watermark-cache" / "old.djcache").write_bytes(b"cache")
    return public, private


def run_migrate(s3, settings, local_media, *args):
    public, private = local_media
    settings.MEDIA_ROOT = public
    out = StringIO()
    # The fixture's PRIVATE_MEDIA_ROOT points at an unused folder; aim it at the files.
    settings.PRIVATE_MEDIA_ROOT = private
    settings.STORAGES = {**settings.STORAGES}  # keep S3 storages after the root change
    call_command("migrate_media_to_storage", *args, stdout=out)
    return out.getvalue()


def test_dry_run_copies_nothing(s3, settings, local_media):
    output = run_migrate(s3, settings, local_media)
    assert "1 to copy" in output and "Dry run" in output
    assert s3.keys(s3.public) == [] and s3.keys(s3.private) == []


def test_commit_copies_verifies_and_is_idempotent(s3, settings, local_media):
    output = run_migrate(s3, settings, local_media, "--commit")
    assert output.count("copied and verified") == 2
    assert s3.keys(s3.public) == ["journal/a.webp"]
    assert s3.keys(s3.private) == ["feed/b.webp"]
    body = s3.client.get_object(Bucket=s3.private, Key="feed/b.webp")["Body"].read()
    assert hashlib.md5(body).hexdigest() == hashlib.md5(b"private-image" * 100).hexdigest()
    copied = s3.client.head_object(Bucket=s3.public, Key="journal/a.webp")
    assert copied["CacheControl"] == "public, max-age=31536000, immutable"

    again = run_migrate(s3, settings, local_media, "--commit")
    assert "1 files, 1 already there, 0 copied" in again


def test_changed_local_file_replaces_the_object(s3, settings, local_media):
    run_migrate(s3, settings, local_media, "--commit")
    (local_media[1] / "feed" / "b.webp").write_bytes(b"edited" * 50)
    output = run_migrate(s3, settings, local_media, "--commit")
    assert "1 replaced" in output
    body = s3.client.get_object(Bucket=s3.private, Key="feed/b.webp")["Body"].read()
    assert body == b"edited" * 50


def test_migration_needs_s3(settings):
    with pytest.raises(CommandError, match="STORAGE_BACKEND=s3"):
        call_command("migrate_media_to_storage")


# Backups to the bucket


@pytest.mark.django_db(transaction=True)
def test_backup_goes_to_the_private_bucket_encrypted(s3, settings):
    from apps.core import backups
    from tests.test_ops import pg_dump_available

    if not pg_dump_available():
        pytest.skip("pg_dump is not installed here")
    identity = pyrage.x25519.Identity.generate()
    settings.BACKUP_AGE_RECIPIENT = str(identity.to_public())
    name = backups.run_backup()
    assert s3.keys(s3.private, "backups/") == [name]
    sealed = s3.client.get_object(Bucket=s3.private, Key=name)["Body"].read()
    assert pyrage.decrypt(sealed, [identity]).startswith(b"PGDMP")
