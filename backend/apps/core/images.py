"""Image sanitising for every user or admin upload.

Uploads are decoded with Pillow, rotated according to their EXIF orientation,
copied pixel-for-pixel into a fresh image (which drops EXIF, GPS, XMP, IPTC
and ICC data), re-encoded as WebP and given a random filename.
"""

import uuid
import warnings
from io import BytesIO
from pathlib import PurePosixPath

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.utils.deconstruct import deconstructible
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_DIMENSION = 2400
WEBP_QUALITY = 82

INVALID = "Upload a JPEG, PNG, WebP or HEIC photo."
TOO_BIG = "That photo is too large. Try one under 15 MB and 40 megapixels."
HEIF_BRANDS = {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1"}


def random_filename(extension="webp"):
    return f"{uuid.uuid4().hex}.{extension}"


def sniff_format(head):
    """The real format from the first bytes, whatever the file name or content type says."""
    if head.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if head[4:8] == b"ftyp" and head[8:12] in HEIF_BRANDS:
        return "heic"
    return None


def _size(source):
    size = getattr(source, "size", None)
    if size is None:
        position = source.tell()
        source.seek(0, 2)
        size = source.tell()
        source.seek(position)
    return size


def validate_upload(source):
    """Reject anything that is not a reasonably sized JPEG, PNG, WebP or HEIC.

    Checks the byte size, the magic bytes and the pixel dimensions from the
    header, before any pixels are decoded, so a decompression bomb is refused
    without being expanded.
    """
    if _size(source) > settings.UPLOAD_MAX_BYTES:
        raise ValidationError(TOO_BIG)
    source.seek(0)
    head = source.read(16)
    source.seek(0)
    if sniff_format(head) is None:
        raise ValidationError(INVALID)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(source) as header:
                width, height = header.size
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ValidationError(TOO_BIG) from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise ValidationError(INVALID) from exc
    finally:
        source.seek(0)
    if width * height > settings.UPLOAD_MAX_PIXELS or max(width, height) > settings.UPLOAD_MAX_SIDE:
        raise ValidationError(TOO_BIG)


def open_clean(source):
    """Decode an image and return an oriented, metadata-free pixel copy."""
    validate_upload(source)
    try:
        with warnings.catch_warnings():
            # Anything over MAX_IMAGE_PIXELS is refused, not merely warned about.
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(source) as original:
                original.load()
                oriented = ImageOps.exif_transpose(original)
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ValidationError(TOO_BIG) from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise ValidationError(INVALID) from exc

    has_alpha = oriented.mode in ("RGBA", "LA") or (
        oriented.mode == "P" and "transparency" in oriented.info
    )
    mode = "RGBA" if has_alpha else "RGB"
    converted = oriented.convert(mode)
    clean = Image.new(mode, converted.size)
    clean.paste(converted)
    return clean


def encode_webp(image, max_dimension=MAX_DIMENSION, max_width=None):
    """Resize (never upscale) and encode as WebP with no metadata attached."""
    resized = image.copy()
    resized.thumbnail((max_width or max_dimension, max_dimension), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    resized.save(buffer, format="WEBP", quality=WEBP_QUALITY, method=6, exif=b"", xmp=b"")
    return buffer.getvalue(), resized.size


def sanitize_image(source, max_dimension=MAX_DIMENSION):
    """Return a metadata-free WebP ContentFile with a random name."""
    data, _ = encode_webp(open_clean(source), max_dimension=max_dimension)
    return ContentFile(data, name=random_filename())


def variant_name(name, width):
    """`events/abc.webp` -> `events/abc-640w.webp`: the smaller copies sit beside the original."""
    stem = name.rsplit(".", 1)[0]
    return f"{stem}-{width}w.webp"


def save_variants(storage, name, clean, widths, missing_only=False):
    """Store a narrower WebP copy of an image beside it for each width below its own.
    `missing_only` skips copies already there (for images stored before a width existed)."""
    for width in widths:
        if width >= clean.width:
            continue
        target = variant_name(name, width)
        if missing_only and storage.exists(target):
            continue
        copy, _ = encode_webp(clean, max_width=width)
        storage.save(target, ContentFile(copy))


@deconstructible
class RandomizedUploadTo:
    """`upload_to` callable that discards the uploaded filename entirely."""

    def __init__(self, prefix):
        self.prefix = prefix.strip("/")

    def __call__(self, instance, filename):
        extension = PurePosixPath(filename).suffix.lstrip(".").lower() or "webp"
        return f"{self.prefix}/{random_filename(extension)}"


class SanitizedImageField(models.ImageField):
    """ImageField that strips metadata and re-encodes new uploads on save.

    With `variant_widths` (public images), it also stores narrower copies beside
    the original for srcset, and records the original's size in
    `<name>_width` / `<name>_height` so pages can reserve the space.
    """

    def __init__(self, *args, variant_widths=(), **kwargs):
        self.variant_widths = tuple(variant_widths)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.variant_widths:
            kwargs["variant_widths"] = self.variant_widths
        return name, path, args, kwargs

    def pre_save(self, model_instance, add):
        file = getattr(model_instance, self.attname)
        if file and not file._committed:
            clean = open_clean(file.file)
            data, (width, height) = encode_webp(clean)
            file.save(random_filename(), ContentFile(data), save=False)
            if self.variant_widths:
                setattr(model_instance, f"{self.name}_width", width)
                setattr(model_instance, f"{self.name}_height", height)
                save_variants(file.storage, file.name, clean, self.variant_widths)
        return super().pre_save(model_instance, add)
