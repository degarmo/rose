"""Faint, tiled viewer watermark for member images.

This does not stop screenshots. It makes a leaked image traceable to the
account that viewed it, which deters leaking in the first place.
"""

from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

OPACITY = 34
WEBP_QUALITY = 82


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def watermark_bytes(image_bytes, label):
    """Return WebP bytes with `label` tiled diagonally across the image."""
    with Image.open(BytesIO(image_bytes)) as source:
        base = source.convert("RGBA")
    width, height = base.size
    font_size = max(14, min(width, height) // 28)
    font = _font(font_size)

    measure = ImageDraw.Draw(Image.new("L", (1, 1)))
    left, top, right, bottom = measure.textbbox((0, 0), label, font=font)
    text_w, text_h = right - left, bottom - top
    step_x, step_y = text_w + font_size * 4, text_h + font_size * 4

    side = int((width**2 + height**2) ** 0.5) + step_x
    tile = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tile)
    for row, y in enumerate(range(0, side, step_y)):
        offset = (row % 2) * step_x // 2
        for x in range(-step_x + offset, side, step_x):
            draw.text((x + 1, y + 1), label, font=font, fill=(0, 0, 0, OPACITY))
            draw.text((x, y), label, font=font, fill=(255, 255, 255, OPACITY))
    rotated = tile.rotate(28, resample=Image.Resampling.BICUBIC)
    crop_left = (rotated.width - width) // 2
    crop_top = (rotated.height - height) // 2
    overlay = rotated.crop((crop_left, crop_top, crop_left + width, crop_top + height))

    combined = Image.alpha_composite(base, overlay).convert("RGB")
    buffer = BytesIO()
    combined.save(buffer, format="WEBP", quality=WEBP_QUALITY, exif=b"", xmp=b"")
    return buffer.getvalue()
