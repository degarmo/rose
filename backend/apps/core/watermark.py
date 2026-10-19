"""Faint, tiled viewer watermark for member images.

This does not stop screenshots. It makes a leaked image traceable to the
account that viewed it, which deters leaking in the first place.

The marks are sparse (about three across the image by default) and faint
(FEED_WATERMARK_OPACITY, 0.06), so they stay out of the way when viewing. Each mark is
light text with a dark outline, so raising the contrast of a copy brings the
viewer's name out on light and dark photos alike.
"""

from dataclasses import dataclass
from io import BytesIO

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont

WEBP_QUALITY = 82
ANGLE = 28
# The label fills about this share of the gap between one mark and the next.
TEXT_SHARE = 0.85
REFERENCE_SIZE = 100


@dataclass(frozen=True)
class Layout:
    font_size: int
    step_x: int
    step_y: int


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _text_width(label, size):
    measure = ImageDraw.Draw(Image.new("L", (1, 1)))
    left, _, right, _ = measure.textbbox((0, 0), label, font=_font(size))
    return right - left


def layout(width, height, label, spacing):
    """Mark spacing and text size for an image: `spacing` is a share of its width."""
    step_x = max(int(width * spacing), 48)
    reference = max(_text_width(label, REFERENCE_SIZE), 1)
    font_size = int(REFERENCE_SIZE * step_x * TEXT_SHARE / reference)
    font_size = max(10, min(font_size, max(height // 12, 10)))
    return Layout(font_size=font_size, step_x=step_x, step_y=max(int(step_x * 0.85), font_size * 3))


def style_key():
    """Changes whenever the look changes, so stored copies are rendered again."""
    return f"{settings.FEED_WATERMARK_OPACITY:.3f}:{settings.FEED_WATERMARK_SPACING:.3f}"


def watermark_bytes(image_bytes, label):
    """Return WebP bytes with `label` tiled diagonally across the image."""
    with Image.open(BytesIO(image_bytes)) as source:
        base = source.convert("RGBA")
    width, height = base.size
    plan = layout(width, height, label, settings.FEED_WATERMARK_SPACING)
    alpha = max(1, round(255 * settings.FEED_WATERMARK_OPACITY))
    font = _font(plan.font_size)

    side = int((width**2 + height**2) ** 0.5) + plan.step_x * 2
    tile = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tile)
    for row, y in enumerate(range(0, side, plan.step_y)):
        offset = (row % 2) * plan.step_x // 2
        for x in range(-plan.step_x + offset, side, plan.step_x):
            draw.text(
                (x, y),
                label,
                font=font,
                fill=(255, 255, 255, alpha),
                stroke_width=max(1, plan.font_size // 14),
                stroke_fill=(0, 0, 0, alpha),
            )
    rotated = tile.rotate(ANGLE, resample=Image.Resampling.BICUBIC)
    crop_left = (rotated.width - width) // 2
    crop_top = (rotated.height - height) // 2
    overlay = rotated.crop((crop_left, crop_top, crop_left + width, crop_top + height))

    combined = Image.alpha_composite(base, overlay).convert("RGB")
    buffer = BytesIO()
    combined.save(buffer, format="WEBP", quality=WEBP_QUALITY, exif=b"", xmp=b"")
    return buffer.getvalue()
