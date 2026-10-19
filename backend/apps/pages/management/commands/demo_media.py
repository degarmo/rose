"""Generated sample pictures for demo and test content.

Light, neutral, non-explicit scenes drawn locally with Pillow from gradients, shapes and
noise: soft daylight, flowers, linen, paper, a bright room and candles on a light table.
Nothing is downloaded, so no licence is involved. Every index gives a different
picture; the kinds and shapes cycle, and each one varies its palette and layout.
"""

import random
from dataclasses import dataclass
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFilter

# Width over height: square, 4:5 portrait and the 1.91:1 landscape the feed allows.
SHAPES = ((1, 1), (4, 5), (1.91, 1))

PALETTES = [
    {
        "light": "#fbf7f1",
        "mid": "#efe4d6",
        "accent": "#e9b9b0",
        "deep": "#b98f73",
        "cool": "#dbe7ee",
    },
    {
        "light": "#f6f6f2",
        "mid": "#e3e6dc",
        "accent": "#c9d7c0",
        "deep": "#8fa489",
        "cool": "#e6eef3",
    },
    {
        "light": "#fdf6f3",
        "mid": "#f3e2dc",
        "accent": "#f0c2c9",
        "deep": "#c08a8f",
        "cool": "#e9eef6",
    },
    {
        "light": "#f8f5ee",
        "mid": "#ece3cf",
        "accent": "#f2d39b",
        "deep": "#b8955f",
        "cool": "#e4ecef",
    },
]

ALT_TEXT = {
    "daylight": "Soft daylight over a pale horizon",
    "floral": "Pale flowers on a light background",
    "linen": "Close-up of natural linen",
    "paper": "Textured paper in soft light",
    "interior": "A bright room with a window and a plant",
    "candle": "Candles on a light table",
}


@dataclass(frozen=True)
class SampleImage:
    file: ContentFile
    width: int
    height: int
    alt: str


def _rgb(hex_colour):
    hex_colour = hex_colour.lstrip("#")
    return tuple(int(hex_colour[i : i + 2], 16) for i in (0, 2, 4))


def _mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b, strict=True))


def _vertical_gradient(size, top, bottom):
    width, height = size
    column = Image.new("RGB", (1, height))
    for y in range(height):
        column.putpixel((0, y), _mix(top, bottom, y / max(height - 1, 1)))
    return column.resize(size)


def _glow(size, centre, radius, colour, strength):
    """A soft round light, as an RGBA layer."""
    mask = Image.new("L", size, 0)
    x, y = centre
    ImageDraw.Draw(mask).ellipse((x - radius, y - radius, x + radius, y + radius), fill=strength)
    mask = mask.filter(ImageFilter.GaussianBlur(radius / 2))
    layer = Image.new("RGBA", size, (*colour, 0))
    layer.putalpha(mask)
    return layer


def _grain(image, amount, rng):
    noise = Image.effect_noise(image.size, 40 + rng.randint(0, 20)).convert("RGB")
    return Image.blend(image, Image.blend(image, noise, 0.5), amount)


def _daylight(size, palette, rng):
    width, height = size
    sky = _vertical_gradient(size, _rgb(palette["cool"]), _rgb(palette["light"]))
    horizon = int(height * rng.uniform(0.55, 0.72))
    draw = ImageDraw.Draw(sky)
    hill = _mix(_rgb(palette["mid"]), _rgb(palette["accent"]), 0.35)
    for _ in range(3):
        cx, span = rng.randint(0, width), int(width * rng.uniform(0.4, 0.8))
        draw.ellipse((cx - span, horizon - span // 5, cx + span, horizon + span // 5), fill=hill)
    draw.rectangle((0, horizon, width, height), fill=_rgb(palette["mid"]))
    sun = (int(width * rng.uniform(0.2, 0.8)), int(horizon * rng.uniform(0.35, 0.75)))
    image = Image.alpha_composite(
        sky.convert("RGBA"), _glow(size, sun, int(min(size) * 0.22), (255, 248, 232), 230)
    )
    return image.convert("RGB").filter(ImageFilter.GaussianBlur(6))


def _floral(size, palette, rng):
    width, height = size
    image = Image.new("RGB", size, _rgb(palette["light"])).convert("RGBA")
    leaf = _mix((140, 170, 128), _rgb(palette["deep"]), 0.2)
    for _ in range(rng.randint(6, 10)):
        cx, cy = rng.randint(0, width), rng.randint(0, height)
        radius = int(min(size) * rng.uniform(0.07, 0.14))
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        draw.ellipse((cx + radius, cy, cx + radius * 3, cy + radius), fill=(*leaf, 120))
        petal = _mix(_rgb(palette["accent"]), (255, 255, 255), rng.uniform(0, 0.4))
        for petal_index in range(6):
            angle = petal_index * 60 + rng.randint(0, 20)
            petal_layer = Image.new("RGBA", (radius * 2, radius * 2), (0, 0, 0, 0))
            ImageDraw.Draw(petal_layer).ellipse(
                (radius // 2, 0, radius * 3 // 2, radius), fill=(*petal, 215)
            )
            rotated = petal_layer.rotate(angle, resample=Image.Resampling.BICUBIC)
            layer.alpha_composite(rotated, (cx - radius, cy - radius))
        heart = radius // 4
        draw.ellipse((cx - heart, cy - heart, cx + heart, cy + heart), fill=(240, 205, 120, 235))
        image = Image.alpha_composite(image, layer)
    return image.convert("RGB").filter(ImageFilter.GaussianBlur(2))


def _linen(size, palette, rng):
    width, height = size
    image = Image.new("RGB", size, _rgb(palette["mid"]))
    draw = ImageDraw.Draw(image)
    thread = _mix(_rgb(palette["mid"]), _rgb(palette["deep"]), 0.25)
    light = _mix(_rgb(palette["mid"]), (255, 255, 255), 0.5)
    for y in range(0, height, rng.randint(5, 7)):
        draw.line((0, y, width, y + rng.randint(-2, 2)), fill=thread if y % 3 else light, width=1)
    for x in range(0, width, rng.randint(5, 7)):
        draw.line((x, 0, x + rng.randint(-2, 2), height), fill=light if x % 2 else thread, width=1)
    image = _grain(image, 0.18, rng).filter(ImageFilter.GaussianBlur(0.8))
    fold = _glow(
        size, (int(width * rng.uniform(0.3, 0.7)), height // 2), width // 3, (255, 255, 255), 90
    )
    return Image.alpha_composite(image.convert("RGBA"), fold).convert("RGB")


def _paper(size, palette, rng):
    width, height = size
    image = _vertical_gradient(size, _rgb(palette["light"]), _rgb(palette["mid"]))
    image = _grain(image, 0.12, rng).filter(ImageFilter.GaussianBlur(1.2))
    draw = ImageDraw.Draw(image)
    fibre = _mix(_rgb(palette["mid"]), _rgb(palette["deep"]), 0.2)
    for _ in range(width // 6):
        x, y = rng.randint(0, width), rng.randint(0, height)
        draw.line((x, y, x + rng.randint(-40, 40), y + rng.randint(-8, 8)), fill=fibre, width=1)
    shadow = Image.new("L", size, 0)
    shade_draw = ImageDraw.Draw(shadow)
    stem_x, stem_y = int(width * rng.uniform(0.2, 0.5)), int(height * rng.uniform(0.2, 0.4))
    for leaf_index in range(6):
        lx, ly = stem_x + leaf_index * width // 14, stem_y + leaf_index * height // 12
        shade_draw.ellipse((lx, ly, lx + width // 9, ly + height // 22), fill=70)
    shadow = shadow.filter(ImageFilter.GaussianBlur(width / 60))
    image = Image.composite(
        Image.new("RGB", size, _mix(_rgb(palette["deep"]), (0, 0, 0), 0.1)), image, shadow
    )
    draw = ImageDraw.Draw(image)
    crease = int(width * rng.uniform(0.35, 0.65))
    shade = _mix(_rgb(palette["mid"]), _rgb(palette["deep"]), 0.15)
    draw.line((crease, 0, crease + rng.randint(-30, 30), height), fill=shade, width=3)
    return image.filter(ImageFilter.GaussianBlur(0.6))


def _interior(size, palette, rng):
    width, height = size
    wall = _rgb(palette["light"])
    image = Image.new("RGB", size, wall)
    draw = ImageDraw.Draw(image)
    floor = int(height * 0.72)
    draw.rectangle((0, floor, width, height), fill=_rgb(palette["mid"]))
    window_w, window_h = int(width * 0.32), int(height * 0.42)
    wx, wy = int(width * rng.uniform(0.1, 0.55)), int(height * 0.12)
    draw.rectangle((wx, wy, wx + window_w, wy + window_h), fill=_rgb(palette["cool"]))
    frame = _mix(wall, _rgb(palette["deep"]), 0.35)
    draw.rectangle((wx, wy, wx + window_w, wy + window_h), outline=frame, width=8)
    draw.line((wx + window_w // 2, wy, wx + window_w // 2, wy + window_h), fill=frame, width=6)
    table_x = int(width * rng.uniform(0.05, 0.5))
    draw.rectangle(
        (
            table_x,
            floor - int(height * 0.12),
            table_x + int(width * 0.4),
            floor - int(height * 0.1),
        ),
        fill=_mix(_rgb(palette["deep"]), wall, 0.3),
    )
    pot_x = int(width * rng.uniform(0.65, 0.85))
    draw.rectangle(
        (pot_x, floor - 60, pot_x + 50, floor), fill=_mix(_rgb(palette["accent"]), wall, 0.2)
    )
    for leaf in range(5):
        draw.ellipse(
            (
                pot_x - 30 + leaf * 18,
                floor - 160 - leaf % 2 * 30,
                pot_x + 10 + leaf * 18,
                floor - 60,
            ),
            fill=(150, 175, 140),
        )
    light = _glow(size, (wx + window_w // 2, floor), window_w, (255, 250, 236), 110)
    return (
        Image.alpha_composite(image.convert("RGBA"), light)
        .convert("RGB")
        .filter(ImageFilter.GaussianBlur(3))
    )


def _candle(size, palette, rng):
    width, height = size
    image = _vertical_gradient(size, _rgb(palette["light"]), _rgb(palette["mid"])).convert("RGBA")
    table = int(height * 0.74)
    ImageDraw.Draw(image).rectangle((0, table, width, height), fill=(*_rgb(palette["mid"]), 255))
    count = rng.randint(2, 4)
    candle_w = int(width * 0.09)
    start = int(width * rng.uniform(0.2, 0.4))
    for index in range(count):
        x = start + index * int(candle_w * 1.6)
        candle_h = int(height * rng.uniform(0.18, 0.36))
        top = table - candle_h
        ImageDraw.Draw(image).rounded_rectangle(
            (x, top, x + candle_w, table),
            radius=6,
            fill=(250, 246, 236, 255),
            outline=(232, 222, 205, 255),
        )
        flame = (x + candle_w // 2, top - candle_w // 3)
        image = Image.alpha_composite(image, _glow(size, flame, candle_w, (255, 214, 140), 150))
        ImageDraw.Draw(image).ellipse(
            (flame[0] - 6, flame[1] - 16, flame[0] + 6, flame[1] + 6), fill=(255, 190, 90, 255)
        )
    return image.convert("RGB").filter(ImageFilter.GaussianBlur(1.5))


KINDS = (
    ("daylight", _daylight),
    ("floral", _floral),
    ("linen", _linen),
    ("paper", _paper),
    ("interior", _interior),
    ("candle", _candle),
)


def sample_image(index, width=1080):
    """A light sample picture as a JPEG. Kinds, shapes and palettes all vary with `index`."""
    kind, draw = KINDS[index % len(KINDS)]
    ratio_w, ratio_h = SHAPES[(index // len(KINDS) + index) % len(SHAPES)]
    size = (width, round(width * ratio_h / ratio_w))
    palette = PALETTES[(index * 7 + index // len(KINDS)) % len(PALETTES)]
    picture = draw(size, palette, random.Random(index))
    buffer = BytesIO()
    picture.save(buffer, "JPEG", quality=86)
    return SampleImage(
        file=ContentFile(buffer.getvalue(), name=f"sample-{index}.jpg"),
        width=size[0],
        height=size[1],
        alt=ALT_TEXT[kind],
    )
