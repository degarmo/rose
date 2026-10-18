import re
from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import ExifTags, Image

from apps.core.images import RandomizedUploadTo, random_filename, sanitize_image
from apps.education.models import Opportunity

RANDOM_NAME = re.compile(r"^[0-9a-f]{32}\.webp$")


def assert_no_metadata(image):
    exif = image.getexif()
    assert len(exif) == 0
    assert len(exif.get_ifd(ExifTags.IFD.GPSInfo)) == 0
    for key in ("exif", "xmp", "icc_profile", "XML:com.adobe.xmp"):
        assert not image.info.get(key)


def test_fixture_really_contains_gps(gps_image_path):
    with Image.open(gps_image_path) as image:
        gps = image.getexif().get_ifd(ExifTags.IFD.GPSInfo)
        assert gps[ExifTags.GPS.GPSLatitudeRef] == "N"
        assert image.getexif()[ExifTags.Base.Make] == "FixtureCam"


def test_sanitize_strips_gps_and_exif(gps_image_path):
    with open(gps_image_path, "rb") as handle:
        cleaned = sanitize_image(handle)

    assert RANDOM_NAME.match(cleaned.name)
    with Image.open(BytesIO(cleaned.read())) as image:
        assert image.format == "WEBP"
        assert image.size == (640, 480)
        assert_no_metadata(image)
    assert b"FixtureCam" not in cleaned.file.getvalue()


def test_sanitize_downscales_large_images():
    buffer = BytesIO()
    Image.new("RGB", (5000, 2500), "black").save(buffer, "PNG")
    cleaned = sanitize_image(buffer, max_dimension=1000)
    with Image.open(BytesIO(cleaned.read())) as image:
        assert image.size == (1000, 500)


def test_sanitize_keeps_transparency():
    buffer = BytesIO()
    Image.new("RGBA", (20, 20), (0, 0, 0, 0)).save(buffer, "PNG")
    cleaned = sanitize_image(buffer)
    with Image.open(BytesIO(cleaned.read())) as image:
        assert image.mode == "RGBA"


def test_sanitize_rejects_non_images():
    with pytest.raises(ValidationError):
        sanitize_image(BytesIO(b"definitely not an image"))


def test_random_filenames_are_unique():
    assert random_filename() != random_filename()


def test_upload_to_discards_original_filename():
    path = RandomizedUploadTo("education")(None, "IMG_0042 my-real-name.JPG")
    assert path.startswith("education/")
    assert "my-real-name" not in path
    assert path.endswith(".jpg")


@pytest.mark.django_db
def test_model_upload_is_sanitized_and_renamed(gps_image_path):
    upload = SimpleUploadedFile(
        "jordan-home-address.jpg", gps_image_path.read_bytes(), content_type="image/jpeg"
    )
    opportunity = Opportunity.objects.create(
        title="With image", slug="with-image", summary="s", body="b", hero_image=upload
    )
    name = opportunity.hero_image.name
    assert name.startswith("education/")
    assert "jordan" not in name
    assert RANDOM_NAME.match(name.split("/")[-1])
    with opportunity.hero_image.open("rb") as stored, Image.open(stored) as image:
        assert image.format == "WEBP"
        assert_no_metadata(image)
