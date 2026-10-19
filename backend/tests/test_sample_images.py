"""Generated sample pictures for demo and test content: light, varied, three shapes."""

import hashlib
from io import BytesIO

from PIL import Image, ImageStat

from apps.pages.management.commands.demo_media import sample_image


def test_twelve_or_more_distinct_light_pictures_in_three_shapes():
    samples = [sample_image(index, width=360) for index in range(18)]
    digests = {hashlib.sha256(sample.file.read()).hexdigest() for sample in samples}
    assert len(digests) == 18
    ratios = set()
    for sample in samples:
        sample.file.seek(0)
        with Image.open(BytesIO(sample.file.read())) as picture:
            assert picture.size == (sample.width, sample.height)
            assert ImageStat.Stat(picture.convert("L")).mean[0] > 170, "samples are light"
        ratios.add(round(sample.width / sample.height, 2))
        assert sample.alt
    assert ratios == {1.0, 0.8, 1.91}


def test_the_same_index_gives_the_same_picture():
    assert sample_image(4, width=200).file.read() == sample_image(4, width=200).file.read()
