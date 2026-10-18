import importlib.util
import json
from io import BytesIO
from pathlib import Path

import pytest
from PIL import ExifTags, Image

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "fetch_images.py"
spec = importlib.util.spec_from_file_location("fetch_images", SCRIPT)
fetch_images = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch_images)


def test_parse_sources_skips_comments_and_defaults_to_hidden():
    entries = fetch_images.parse_sources(
        "# comment\n\nhttps://x.example/a.jpg | home-hero | unsplash | Unsplash License | Ana\n"
        "https://x.example/b.jpg | week-weekend | pexels | | | faces=no | consent=no\n"
    )
    assert [e.name for e in entries] == ["home-hero", "week-weekend"]
    assert entries[0].faces_visible is True
    assert entries[0].consent_confirmed is False
    assert entries[0].credit == "Ana"
    assert entries[1].faces_visible is False


@pytest.mark.parametrize(
    "line",
    [
        "ftp://x.example/a.jpg | name | unsplash",
        "https://x.example/a.jpg | Bad Name | unsplash",
        "https://x.example/a.jpg | ok-name",
        "https://x.example/a.jpg | ok-name | unsplash | | | faces=maybe",
    ],
)
def test_parse_sources_rejects_bad_lines(line):
    with pytest.raises(ValueError):
        fetch_images.parse_sources(line)


def test_run_writes_clean_variants_and_manifest(tmp_path, gps_image_path):
    big = BytesIO()
    with Image.open(gps_image_path) as source:
        exif = source.getexif()
        source.resize((2560, 1920)).save(big, "JPEG", exif=exif)
    payload = big.getvalue()

    sources = tmp_path / "sources.txt"
    sources.write_text(
        "https://x.example/a.jpg | home-hero | unsplash | Unsplash License | Ana | faces=no\n"
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"images": [{"filename": "old.webp"}]}))
    output = tmp_path / "images"

    status = fetch_images.run(sources, manifest_path, output, fetch=lambda url: payload)
    assert status == 0

    files = sorted(p.name for p in output.iterdir())
    assert files == [
        "home-hero-1280.webp",
        "home-hero-1920.webp",
        "home-hero-640.webp",
        "home-hero.webp",
    ]
    for path in output.iterdir():
        with Image.open(path) as image:
            assert image.format == "WEBP"
            assert len(image.getexif()) == 0
            assert len(image.getexif().get_ifd(ExifTags.IFD.GPSInfo)) == 0

    manifest = json.loads(manifest_path.read_text())
    names = [img["filename"] for img in manifest["images"]]
    assert names == ["home-hero.webp", "old.webp"]
    entry = manifest["images"][0]
    assert entry["width"] == 1920 and entry["height"] == 1440
    assert [v["width"] for v in entry["variants"]] == [640, 1280, 1920]
    assert entry["faces_visible"] is False
    assert entry["consent_confirmed"] is False
    assert entry["original_url"] == "https://x.example/a.jpg"

    fetch_images.run(sources, manifest_path, output, fetch=lambda url: payload)
    manifest = json.loads(manifest_path.read_text())
    assert [img["filename"] for img in manifest["images"]] == ["home-hero.webp", "old.webp"]


def test_small_images_are_not_upscaled(tmp_path, gps_image_path):
    sources = tmp_path / "sources.txt"
    sources.write_text("https://x.example/a.jpg | small | pexels\n")
    manifest_path = tmp_path / "manifest.json"
    output = tmp_path / "images"
    fetch_images.run(sources, manifest_path, output, fetch=lambda url: gps_image_path.read_bytes())
    entry = json.loads(manifest_path.read_text())["images"][0]
    assert [v["width"] for v in entry["variants"]] == [640]
    assert entry["width"] == 640


def test_failures_are_reported_and_exit_nonzero(tmp_path, capsys):
    sources = tmp_path / "sources.txt"
    sources.write_text("https://x.example/a.jpg | broken | pexels\n")
    manifest_path = tmp_path / "manifest.json"

    status = fetch_images.run(
        sources, manifest_path, tmp_path / "images", fetch=lambda url: b"not an image"
    )
    assert status == 1
    assert "fail  broken" in capsys.readouterr().err
    assert json.loads(manifest_path.read_text()) == {"images": []}
