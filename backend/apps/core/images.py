"""Image sanitising for every user or admin upload.

Uploads are decoded with Pillow, rotated according to their EXIF orientation,
copied pixel-for-pixel into a fresh image (which drops EXIF, GPS, XMP, IPTC
and ICC data), re-encoded as WebP and given a random filename.
"""

import uuid
from io import BytesIO
from pathlib import PurePosixPath

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.utils.deconstruct import deconstructible
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_DIMENSION = 2400
WEBP_QUALITY = 82
MAX_PIXELS = 40_000_000


def random_filename(extension="webp"):
    return f"{uuid.uuid4().hex}.{extension}"


def sanitize_image(source, max_dimension=MAX_DIMENSION):
    """Return a metadata-free WebP ContentFile with a random name."""
    try:
        source.seek(0)
        with Image.open(source) as original:
            if original.width * original.height > MAX_PIXELS:
                raise ValidationError("Image is too large.")
            original.load()
            oriented = ImageOps.exif_transpose(original)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValidationError("Upload a valid image file.") from exc

    has_alpha = oriented.mode in ("RGBA", "LA") or (
        oriented.mode == "P" and "transparency" in oriented.info
    )
    mode = "RGBA" if has_alpha else "RGB"
    converted = oriented.convert(mode)
    converted.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    clean = Image.new(mode, converted.size)
    clean.paste(converted)

    buffer = BytesIO()
    clean.save(buffer, format="WEBP", quality=WEBP_QUALITY, method=6, exif=b"", xmp=b"")
    return ContentFile(buffer.getvalue(), name=random_filename())


@deconstructible
class RandomizedUploadTo:
    """`upload_to` callable that discards the uploaded filename entirely."""

    def __init__(self, prefix):
        self.prefix = prefix.strip("/")

    def __call__(self, instance, filename):
        extension = PurePosixPath(filename).suffix.lstrip(".").lower() or "webp"
        return f"{self.prefix}/{random_filename(extension)}"


class SanitizedImageField(models.ImageField):
    """ImageField that strips metadata and re-encodes new uploads on save."""

    def pre_save(self, model_instance, add):
        file = getattr(model_instance, self.attname)
        if file and not file._committed:
            cleaned = sanitize_image(file.file)
            file.save(cleaned.name, cleaned, save=False)
        return super().pre_save(model_instance, add)
