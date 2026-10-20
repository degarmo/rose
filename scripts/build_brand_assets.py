"""Build the logo files from the owner's emblem (a transparent PNG with a neon glow).

    backend/.venv/bin/python scripts/build_brand_assets.py photos/<emblem>.png

The emblem itself stays out of the repository (photos/ is ignored): only what this script
makes is committed. Re-runnable; it replaces everything it wrote before.

Into frontend/public/brand/ (served by the site):
- emblem-{120,240,480,960}.webp/.png: the whole emblem, transparent edges trimmed to an
  even margin that keeps the glow. PNGs are 256-colour (dithered) fallbacks.
- rose-{64,128,256,512}.webp/.png: the rose alone, no lettering, on a transparent square.
  The leaves cross the neon line and the letters, so the mark is the rose head, eased
  into transparency at its edge.
- favicon-32.png (the rose), and the home-screen icons apple-touch-icon.png (180),
  icon-192.png and icon-512.png: the rose on a white tile, opaque, so their reduced
  colours keep a clean edge.
- og-image.jpg: 1200 x 630, the emblem centred on the site's softest blush.

And frontend/public/favicon.ico (16, 32, 48, the rose): at the root, where browsers and
crawlers look for it unasked.

Into backend/apps/core/static/core/brand/ (the admin, self-hosted): the emblem at 240 and
480 (WebP and PNG) and the rose favicons.
"""

import shutil
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "frontend" / "public" / "brand"
ADMIN = ROOT / "backend" / "apps" / "core" / "static" / "core" / "brand"

EMBLEM_WIDTHS = (120, 240, 480, 960)
MARK_WIDTHS = (64, 128, 256, 512)
GLOW_MARGIN = 18  # px at full size: the glow fades out within this
ALPHA_FLOOR = 8  # alpha at or below this counts as empty when trimming

# The rose head in the source (1774 x 887): its centre and radii, the edge softness (a
# share of the radius) and the line just above the letters where it is cut and faded.
ROSE_CENTRE = (1420, 272)
ROSE_RADII = (205, 190)
ROSE_SOFT_EDGE = 0.12
LETTERS_TOP, LETTERS_FADE = 442, 24

WHITE = (255, 255, 255, 255)
BLUSH = (252, 247, 248, 255)  # --ui-wash-rose-2, the softest blush on the site


def trim(emblem):
    alpha = emblem.getchannel("A").point(lambda value: 255 if value > ALPHA_FLOOR else 0)
    left, top, right, bottom = alpha.getbbox()
    return emblem.crop(
        (
            max(0, left - GLOW_MARGIN),
            max(0, top - GLOW_MARGIN),
            min(emblem.width, right + GLOW_MARGIN),
            min(emblem.height, bottom + GLOW_MARGIN),
        )
    )


def rose(emblem):
    """The rose head, eased into transparency at its edge and cut above the lettering."""
    cx, cy = ROSE_CENTRE
    rx, ry = ROSE_RADII
    box = (cx - rx, cy - ry, cx + rx, min(cy + ry, LETTERS_TOP))
    head = emblem.crop(box)
    pixels = head.load()
    inner = (1 - ROSE_SOFT_EDGE) ** 2
    for y in range(head.height):
        source_y = y + box[1]
        for x in range(head.width):
            red, green, blue, alpha = pixels[x, y]
            if not alpha:
                continue
            distance = ((x + box[0] - cx) / rx) ** 2 + ((source_y - cy) / ry) ** 2
            keep = 1.0 if distance <= inner else max(0.0, (1 - distance**0.5) / ROSE_SOFT_EDGE)
            if source_y > LETTERS_TOP - LETTERS_FADE:
                keep *= max(0.0, (LETTERS_TOP - source_y) / LETTERS_FADE)
            pixels[x, y] = (red, green, blue, int(alpha * keep))
    side = max(head.size)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.alpha_composite(head, ((side - head.width) // 2, (side - head.height) // 2))
    return square


def resized(image, width):
    height = round(image.height * width / image.width)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def on(background, image, size=None):
    canvas = Image.new("RGBA", size or image.size, background)
    canvas.alpha_composite(
        image, ((canvas.width - image.width) // 2, (canvas.height - image.height) // 2)
    )
    return canvas


def tile(mark, side):
    """A home-screen icon: the rose on white, with the margin the 180px Apple icon uses."""
    return on(WHITE, resized(mark, round(side * 156 / 180)), (side, side)).convert("RGB")


def save(image, path, written):
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix
    buffer = BytesIO()
    if suffix == ".webp":
        # Lossy alpha too: the glow's soft edge looks the same and the files are a third smaller.
        image.save(buffer, format="WEBP", quality=82, alpha_quality=60, method=6)
    elif suffix == ".png" and image.width >= 64:
        # Pillow's only quantizer with transparency is the octree; opaque tiles get median cut.
        method = Image.Quantize.FASTOCTREE if image.mode == "RGBA" else Image.Quantize.MEDIANCUT
        dithered = image.quantize(colors=256, method=method, dither=Image.Dither.FLOYDSTEINBERG)
        dithered.save(buffer, format="PNG", optimize=True)
    elif suffix == ".png":
        image.save(buffer, format="PNG", optimize=True)
    elif suffix == ".jpg":
        image.convert("RGB").save(
            buffer, format="JPEG", quality=86, optimize=True, progressive=True
        )
    else:
        raise ValueError(path)
    path.write_bytes(buffer.getvalue())
    written.append(path)


def build(source):
    emblem = trim(Image.open(source).convert("RGBA"))
    mark = rose(Image.open(source).convert("RGBA"))
    for folder in (SITE, ADMIN):
        shutil.rmtree(folder, ignore_errors=True)
    written = []

    for width in EMBLEM_WIDTHS:
        image = resized(emblem, width)
        for suffix in (".webp", ".png"):
            save(image, SITE / f"emblem-{width}{suffix}", written)
            if width in (240, 480):
                save(image, ADMIN / f"emblem-{width}{suffix}", written)
    for width in MARK_WIDTHS:
        image = resized(mark, width)
        for suffix in (".webp", ".png"):
            save(image, SITE / f"rose-{width}{suffix}", written)

    small = resized(mark, 32)
    for folder in (SITE, ADMIN):
        save(small, folder / "favicon-32.png", written)
    for icon in (SITE.parent / "favicon.ico", ADMIN / "favicon.ico"):
        resized(mark, 48).save(icon, format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
        written.append(icon)
    save(tile(mark, 180), SITE / "apple-touch-icon.png", written)
    save(tile(mark, 192), SITE / "icon-192.png", written)
    save(tile(mark, 512), SITE / "icon-512.png", written)
    save(on(BLUSH, resized(emblem, 960), (1200, 630)), SITE / "og-image.jpg", written)
    return written


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__.split("\n\n")[1])
    for path in build(Path(sys.argv[1])):
        print(f"{path.relative_to(ROOT)}  {path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
