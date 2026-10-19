"""The viewer watermark: sparse and faint by default, still there when contrast is raised."""

from io import BytesIO

import pytest
from PIL import Image, ImageChops, ImageStat

from apps.core.private_media import watermark_name
from apps.core.watermark import layout, watermark_bytes

LABEL = "velvet_fox  2026-10-19"


def grey_jpeg(width=1080, height=1350, shade=128):
    buffer = BytesIO()
    Image.new("RGB", (width, height), (shade, shade, shade)).save(buffer, "JPEG", quality=95)
    return buffer.getvalue()


def difference(original, marked):
    with Image.open(BytesIO(original)) as a, Image.open(BytesIO(marked)) as b:
        return ImageChops.difference(a.convert("L"), b.convert("L"))


@pytest.mark.parametrize("width", [720, 1080])
def test_default_spacing_gives_about_three_marks_across(width, settings):
    plan = layout(width, width, LABEL, settings.FEED_WATERMARK_SPACING)
    assert 2.8 <= width / plan.step_x <= 3.2
    assert plan.step_y >= plan.step_x * 0.8  # rows as sparse as the columns


def test_smaller_spacing_means_more_marks():
    assert layout(1080, 1080, LABEL, 0.2).step_x < layout(1080, 1080, LABEL, 0.34).step_x


def test_default_watermark_is_faint(settings):
    assert settings.FEED_WATERMARK_OPACITY == 0.06
    original = grey_jpeg()
    diff = difference(original, watermark_bytes(original, LABEL))
    # At 6% opacity no pixel moves far, and most do not move at all.
    assert diff.getextrema()[1] <= 40
    assert ImageStat.Stat(diff).mean[0] < 2


@pytest.mark.parametrize("shade", [40, 128, 225])
def test_marks_come_out_when_contrast_is_raised(shade):
    """On dark, mid and light images alike, the marks are there and spread across the width."""
    original = grey_jpeg(shade=shade)
    diff = difference(original, watermark_bytes(original, LABEL))
    boosted = diff.point(lambda value: 255 if value >= 6 else 0)
    width, height = boosted.size
    marked_share = sum(boosted.histogram()[255:]) / (width * height)
    assert 0.003 < marked_share < 0.2
    for third in range(3):
        column = boosted.crop((third * width // 3, 0, (third + 1) * width // 3, height))
        assert column.getextrema()[1] == 255, f"no mark in third {third + 1}"


def test_opacity_setting_controls_strength(settings):
    original = grey_jpeg()
    settings.FEED_WATERMARK_OPACITY = 0.06
    faint = ImageStat.Stat(difference(original, watermark_bytes(original, LABEL))).mean[0]
    settings.FEED_WATERMARK_OPACITY = 0.2
    strong = ImageStat.Stat(difference(original, watermark_bytes(original, LABEL))).mean[0]
    assert strong > faint * 2


def test_changing_the_style_renders_new_copies(settings):
    before = watermark_name("feed/a.webp", 1, LABEL)
    settings.FEED_WATERMARK_SPACING = 0.5
    after = watermark_name("feed/a.webp", 1, LABEL)
    assert before != after
    # Same image folder, so deleting the image still finds every copy.
    assert before.rsplit("/", 1)[0] == after.rsplit("/", 1)[0]
