import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client

ENTRIES = [
    {
        "filename": "home-hero.webp",
        "faces_visible": True,
        "consent_confirmed": False,
        "source": "unsplash",
        "credit": "Ana",
    },
    {
        "filename": "week-weekend.webp",
        "faces_visible": True,
        "consent_confirmed": False,
        "source": "pexels",
    },
    {"filename": "join-hero.webp", "faces_visible": True, "consent_confirmed": False},
    {"filename": "about-hero.webp", "faces_visible": False, "consent_confirmed": False},
]


@pytest.fixture
def manifest(settings):
    settings.SITE_IMAGES_DIR.mkdir(parents=True)
    (settings.SITE_IMAGES_DIR / "home-hero.webp").write_bytes(b"RIFF....WEBP")
    (settings.SITE_IMAGES_DIR / "about-hero.webp").write_bytes(b"RIFF....WEBP")
    settings.IMAGE_MANIFEST_PATH.write_text(json.dumps({"images": ENTRIES}))

    def read():
        data = json.loads(settings.IMAGE_MANIFEST_PATH.read_text())
        return {img["filename"]: img for img in data["images"]}

    return read


def test_list_shows_only_hidden(manifest, capsys):
    call_command("review_images", "--list")
    out = capsys.readouterr().out
    assert "3 hidden image(s)" in out
    assert "home-hero.webp" in out and "about-hero.webp" not in out
    assert manifest()["home-hero.webp"]["consent_confirmed"] is False


def test_interactive_review_writes_decisions(manifest, monkeypatch, capsys):
    answers = iter(["x", "n", "c", "k"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    call_command("review_images")
    data = manifest()
    assert data["home-hero.webp"]["faces_visible"] is False
    assert data["week-weekend.webp"]["faces_visible"] is True
    assert data["week-weekend.webp"]["consent_confirmed"] is True
    assert data["join-hero.webp"]["consent_confirmed"] is False
    out = capsys.readouterr().out
    assert "Please type n, c, k or q." in out
    assert "2 image(s) updated" in out


def test_quit_saves_progress(manifest, monkeypatch):
    answers = iter(["n", "q"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    call_command("review_images")
    data = manifest()
    assert data["home-hero.webp"]["faces_visible"] is False
    assert data["week-weekend.webp"]["consent_confirmed"] is False


def test_scripted_set(manifest):
    call_command("review_images", "--set", "join-hero.webp=consent")
    assert manifest()["join-hero.webp"]["consent_confirmed"] is True
    with pytest.raises(CommandError):
        call_command("review_images", "--set", "missing.webp=no-faces")
    with pytest.raises(CommandError):
        call_command("review_images", "--set", "join-hero.webp=maybe")


def test_nothing_to_review(settings, capsys):
    settings.IMAGE_MANIFEST_PATH.write_text(json.dumps({"images": [ENTRIES[3]]}))
    call_command("review_images")
    assert "Nothing to review" in capsys.readouterr().out


@pytest.mark.django_db
def test_admin_image_review_page(admin_client, manifest, make_event, gps_image_path):
    from django.core.files.uploadedfile import SimpleUploadedFile

    upload = SimpleUploadedFile("x.jpg", gps_image_path.read_bytes(), content_type="image/jpeg")
    make_event(
        title="Faces night",
        hero_image=upload,
        hero_image_alt="Crowd",
        hero_image_faces_visible=True,
        is_published=False,
    )

    response = admin_client.get("/admin/image-review/")
    content = response.content.decode()
    assert response.status_code == 200
    assert "Hidden: faces visible without confirmed consent" in content
    assert "/admin/image-review/file/home-hero.webp" in content
    assert "Faces night" in content
    assert "faces visible without confirmed consent" in content.lower()
    assert "4 images hidden right now" in content

    index = admin_client.get("/admin/").content.decode()
    assert "/admin/image-review/" in index


@pytest.mark.django_db
def test_admin_image_files_are_staff_only(admin_client, manifest):
    assert admin_client.get("/admin/image-review/file/home-hero.webp").status_code == 200
    assert admin_client.get("/admin/image-review/file/not-listed.webp").status_code == 404
    assert admin_client.get("/admin/image-review/file/join-hero.webp").status_code == 404
    anonymous = Client().get("/admin/image-review/file/home-hero.webp")
    assert anonymous.status_code == 302
    assert "/login/" in anonymous["Location"]
