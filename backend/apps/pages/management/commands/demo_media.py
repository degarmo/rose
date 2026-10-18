"""Generated placeholder artwork for demo content: gradients, no photography."""

from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

PALETTES = [
    ("#0d0a0b", "#7b1e2e", "#e8b068"),
    ("#0d0a0b", "#4a1019", "#e6bdb5"),
    ("#120c0d", "#922638", "#f2e8da"),
    ("#0b0809", "#3d1520", "#d4848f"),
    ("#100b0a", "#5a3a22", "#c29b62"),
]


def _glow(size, diameter, center):
    """A soft white disc on black, centred at `center`."""
    canvas = Image.new("L", (size, size), 0)
    radius = diameter // 4
    ImageDraw.Draw(canvas).ellipse(
        (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius),
        fill=255,
    )
    return canvas.filter(ImageFilter.GaussianBlur(diameter / 5))


def gradient_image(seed, size=1080):
    """A two-glow gradient in the site palette, as a JPEG ContentFile."""
    dark, mid, light = PALETTES[seed % len(PALETTES)]
    wide = _glow(
        size,
        int(size * (1.3 + (seed % 3) * 0.2)),
        (size * (2 + seed % 5) // 8, size * (3 + seed % 4) // 8),
    )
    tight = _glow(
        size,
        int(size * (0.45 + (seed % 4) * 0.1)),
        (size * (6 - seed % 4) // 8, size * (5 + seed % 3) // 8),
    )
    base = ImageOps.colorize(wide, black=dark, white=mid)
    flare = ImageOps.colorize(tight, black="#000000", white=light)
    combined = ImageChops.add(base, Image.blend(Image.new("RGB", flare.size), flare, 0.55))
    grain = Image.effect_noise((size, size), 18).convert("RGB")
    textured = Image.blend(combined, ImageChops.multiply(combined, grain), 0.12)
    buffer = BytesIO()
    textured.filter(ImageFilter.GaussianBlur(2)).save(buffer, "JPEG", quality=88)
    return ContentFile(buffer.getvalue(), name=f"demo-{seed}.jpg")
