"""Download site imagery, strip all metadata, and record it in the manifest.

Usage (from the repository root, using the backend virtualenv):

    backend/.venv/bin/python scripts/fetch_images.py
    backend/.venv/bin/python scripts/fetch_images.py --sources docs/image-sources.txt

Each non-comment line of the sources file has pipe-separated fields:

    url | name | source | license | credit | faces=yes|no | consent=yes|no

`name` becomes the output filename (`name.webp` plus width variants such as
`name-640.webp`). Faces default to "yes" and consent to "no", so an image
stays hidden on the site until someone has looked at it and marked it safe.
"""

import argparse
import json
import re
import sys
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from apps.core.images import encode_webp, open_clean  # noqa: E402

DEFAULT_SOURCES = ROOT / "docs" / "image-sources.txt"
DEFAULT_MANIFEST = ROOT / "docs" / "image-manifest.json"
DEFAULT_OUTPUT = ROOT / "frontend" / "public" / "images"
WIDTHS = (640, 1280, 1920)
MAX_DOWNLOAD_BYTES = 30 * 1024 * 1024
ALLOWED_SCHEMES = ("https://", "http://", "file://")
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
USER_AGENT = "Mozilla/5.0 (compatible; image-fetch/1.0)"


@dataclass
class SourceLine:
    url: str
    name: str
    source: str
    license: str
    credit: str
    faces_visible: bool
    consent_confirmed: bool


def parse_flag(value, key, default):
    value = value.strip().lower()
    if not value:
        return default
    prefix = f"{key}="
    if not value.startswith(prefix):
        raise ValueError(f"expected {key}=yes or {key}=no, got {value!r}")
    answer = value[len(prefix) :]
    if answer not in ("yes", "no"):
        raise ValueError(f"expected {key}=yes or {key}=no, got {value!r}")
    return answer == "yes"


def parse_sources(text):
    entries = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 3:
            raise ValueError(f"line {number}: need at least url | name | source")
        parts += [""] * (7 - len(parts))
        url, name, source, license_, credit, faces, consent = parts[:7]
        if not url.startswith(ALLOWED_SCHEMES):
            raise ValueError(f"line {number}: unsupported URL {url!r}")
        if not NAME_PATTERN.match(name):
            raise ValueError(f"line {number}: name must be lowercase letters, digits and dashes")
        try:
            entries.append(
                SourceLine(
                    url=url,
                    name=name,
                    source=source,
                    license=license_,
                    credit=credit,
                    faces_visible=parse_flag(faces, "faces", default=True),
                    consent_confirmed=parse_flag(consent, "consent", default=False),
                )
            )
        except ValueError as exc:
            raise ValueError(f"line {number}: {exc}") from exc
    return entries


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(MAX_DOWNLOAD_BYTES + 1)
    if len(data) > MAX_DOWNLOAD_BYTES:
        raise ValueError(f"{url} is larger than {MAX_DOWNLOAD_BYTES} bytes")
    return data


def process(entry, data, output_dir):
    """Write the WebP variants for one image and return its manifest entry."""
    clean = open_clean(BytesIO(data))
    output_dir.mkdir(parents=True, exist_ok=True)

    variants = []
    for width in WIDTHS:
        if width > clean.width and variants:
            break
        encoded, size = encode_webp(clean, max_dimension=width)
        filename = f"{entry.name}-{size[0]}.webp"
        (output_dir / filename).write_bytes(encoded)
        variants.append({"width": size[0], "height": size[1], "filename": filename})

    largest, size = encode_webp(clean, max_dimension=WIDTHS[-1])
    filename = f"{entry.name}.webp"
    (output_dir / filename).write_bytes(largest)

    return {
        "filename": filename,
        "width": size[0],
        "height": size[1],
        "variants": variants,
        "source": entry.source,
        "original_url": entry.url,
        "license": entry.license,
        "credit": entry.credit,
        "faces_visible": entry.faces_visible,
        "consent_confirmed": entry.consent_confirmed,
        "added_at": datetime.now(UTC).strftime("%Y-%m-%d"),
    }


def load_manifest(path):
    if not path.exists():
        return {"images": []}
    return json.loads(path.read_text())


def merge(manifest, entry):
    """Append a new entry, or replace the existing one with the same filename."""
    images = [img for img in manifest["images"] if img["filename"] != entry["filename"]]
    images.append(entry)
    images.sort(key=lambda img: img["filename"])
    return {**manifest, "images": images}


def run(sources_path, manifest_path, output_dir, fetch=download):
    entries = parse_sources(sources_path.read_text())
    manifest = load_manifest(manifest_path)
    failures = []
    for entry in entries:
        try:
            manifest = merge(manifest, process(entry, fetch(entry.url), output_dir))
            print(f"ok    {entry.name}.webp")
        except Exception as exc:  # report every bad line, then exit non-zero
            failures.append(entry.name)
            print(f"fail  {entry.name}: {exc}", file=sys.stderr)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{len(entries) - len(failures)} processed, {len(failures)} failed")
    return 1 if failures else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    return run(args.sources, args.manifest, args.output)


if __name__ == "__main__":
    sys.exit(main())
