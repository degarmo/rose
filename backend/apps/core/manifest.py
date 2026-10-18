"""Read and write docs/image-manifest.json, the record of every site image."""

import json
from pathlib import Path

from django.conf import settings

SHOWN = "shown"
HIDDEN = "hidden"
MISSING = "missing"

STATUS_LABELS = {
    SHOWN: "Shown on the site",
    HIDDEN: "Hidden: faces visible without confirmed consent",
    MISSING: "Hidden: file missing from the images folder",
}


def manifest_path():
    return Path(settings.IMAGE_MANIFEST_PATH)


def load_manifest():
    path = manifest_path()
    if not path.exists():
        return {"images": []}
    return json.loads(path.read_text())


def save_manifest(manifest):
    manifest_path().write_text(json.dumps(manifest, indent=2) + "\n")


def is_hidden(entry):
    return bool(entry.get("faces_visible", True)) and not entry.get("consent_confirmed", False)


def image_file(entry):
    return Path(settings.SITE_IMAGES_DIR) / entry["filename"]


def entry_status(entry):
    if is_hidden(entry):
        return HIDDEN
    if not image_file(entry).exists():
        return MISSING
    return SHOWN


def find_entry(manifest, filename):
    return next((img for img in manifest["images"] if img["filename"] == filename), None)
