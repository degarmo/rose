"""Uploads: size, real format by magic bytes, pixel limits and decompression bombs."""

import struct
import zlib
from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.core import images

pytestmark = pytest.mark.django_db


def png_header_only(width, height):
    """A tiny file whose header claims huge dimensions: a decompression bomb's shape."""

    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    ihdr = struct.pack(">IIBBBBB", width, height, 1, 0, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(b"\x00" * 64))
        + chunk(b"IEND", b"")
    )


def encoded(fmt, size=(40, 30), **kwargs):
    buffer = BytesIO()
    Image.new("RGB", size, (120, 30, 40)).save(buffer, format=fmt, **kwargs)
    buffer.seek(0)
    return buffer


@pytest.mark.parametrize("fmt", ["JPEG", "PNG", "WEBP"])
def test_accepted_formats(fmt):
    cleaned = images.sanitize_image(encoded(fmt))
    assert cleaned.name.endswith(".webp")


def test_heic_from_phones_is_accepted():
    import pillow_heif

    buffer = BytesIO()
    pillow_heif.from_pillow(Image.new("RGB", (64, 48), (10, 20, 30))).save(buffer, quality=60)
    buffer.seek(0)
    assert images.sniff_format(buffer.getvalue()[:16]) == "heic"
    cleaned = images.sanitize_image(buffer)
    with Image.open(cleaned) as result:
        assert result.format == "WEBP" and result.size == (64, 48)


@pytest.mark.parametrize(
    "payload",
    [
        encoded("GIF").getvalue(),
        encoded("BMP").getvalue(),
        b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>",
        b"<!doctype html><html><body>hello</body></html>",
        b"%PDF-1.7\n...",
        b"",
    ],
    ids=["gif", "bmp", "svg", "html", "pdf", "empty"],
)
def test_other_formats_are_refused_whatever_the_name(payload):
    upload = SimpleUploadedFile("holiday.jpg", payload, content_type="image/jpeg")
    with pytest.raises(ValidationError, match="JPEG, PNG, WebP or HEIC"):
        images.validate_upload(upload)


def test_decompression_bomb_is_refused_without_decoding():
    bomb = SimpleUploadedFile("bomb.png", png_header_only(50_000, 50_000), content_type="image/png")
    assert bomb.size < 200
    with pytest.raises(ValidationError, match="too large"):
        images.validate_upload(bomb)
    with pytest.raises(ValidationError, match="too large"):
        images.sanitize_image(bomb)


@pytest.mark.parametrize("size", [(7000, 7000), (13_000, 10)])
def test_pixel_and_side_limits(size):
    with pytest.raises(ValidationError, match="too large"):
        images.validate_upload(BytesIO(png_header_only(*size)))


def test_byte_size_limit(settings):
    settings.UPLOAD_MAX_BYTES = 1000
    big = encoded("PNG", size=(400, 400))
    big.size = 5000
    with pytest.raises(ValidationError, match="too large"):
        images.validate_upload(big)


def test_pillow_refuses_bombs_globally():
    assert Image.MAX_IMAGE_PIXELS == 40_000_000


def test_feed_upload_rejects_a_bomb(member_client):
    client, _ = member_client()
    bomb = SimpleUploadedFile("bomb.png", png_header_only(50_000, 50_000), content_type="image/png")
    response = client.post(
        "/api/members/feed/",
        {"caption": "hello", "images": [bomb], "consent_attested": "true"},
        format="multipart",
    )
    assert response.status_code == 400
    assert response.json()["code"] == "image_too_large"


def test_feed_upload_rejects_a_disguised_file(member_client):
    client, _ = member_client()
    fake = SimpleUploadedFile("photo.jpg", b"<html>not a photo</html>", content_type="image/jpeg")
    response = client.post(
        "/api/members/feed/",
        {"caption": "hello", "images": [fake], "consent_attested": "true"},
        format="multipart",
    )
    assert response.status_code == 400
    assert response.json()["code"] == "image_invalid"


def test_avatar_upload_rejects_a_bomb(member_client):
    client, _ = member_client()
    bomb = SimpleUploadedFile("bomb.png", png_header_only(50_000, 50_000), content_type="image/png")
    response = client.post("/api/members/me/avatar/", {"image": bomb}, format="multipart")
    assert response.status_code == 400
