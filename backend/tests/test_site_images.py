"""Page images: one slot per fixed picture on the public pages, edited in the admin."""

import re
from io import BytesIO
from pathlib import Path

import pillow_heif
import pytest
from django.contrib.messages import get_messages
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from PIL import Image

from apps.core.images import variant_name
from apps.core.models import AuditLog
from apps.pages.models import SiteImage
from apps.safety.roles import ADMIN, MODERATOR, STAFF, set_role
from tests.conftest import PASSWORD, staff_login

pytestmark = pytest.mark.django_db
FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src"
SLOTS = {
    "home.hero",
    "about.hero",
    "visit.hero",
    "guests.hero",
    "rentals.hero",
    "volunteer.hero",
    "donate.hero",
}


def picture(fmt="JPEG", size=(1800, 1200), name="photo.jpg"):
    if fmt == "HEIF":
        pillow_heif.register_heif_opener()
    buffer = BytesIO()
    Image.new("RGB", size, (190, 40, 80)).save(buffer, fmt)
    return SimpleUploadedFile(name, buffer.getvalue())


@pytest.fixture
def team(django_user_model):
    def sign_in(role):
        user = django_user_model.objects.create_user(
            email=f"{role}@example.org", display_name=f"team_{role}", password=PASSWORD
        )
        set_role(user, role)
        return staff_login(Client(), user), user

    return sign_in


@pytest.fixture
def staff(team):
    return team(STAFF)


def home():
    return SiteImage.objects.get(slot="home.hero")


def change(client, slot, image=None, **fields):
    data = {
        "image_alt": slot.image_alt,
        "image_faces_visible": "on" if slot.image_faces_visible else "",
        "image_consent_confirmed": "on" if slot.image_consent_confirmed else "",
        "credit": slot.credit,
        "focal_x": slot.focal_x,
        "focal_y": slot.focal_y,
        **fields,
    }
    data = {key: value for key, value in data.items() if value != ""}
    if image is not None:
        data["image"] = image
    return client.post(reverse("admin:pages_siteimage_change", args=[slot.pk]), data)


def api_images(client):
    return client.get("/api/site-images/").json()["images"]


# The slots


def test_every_fixed_picture_has_a_filled_slot(client):
    assert set(SiteImage.objects.values_list("slot", flat=True)) == SLOTS
    images = api_images(client)
    assert set(images) == SLOTS
    assert all(image["alt"] and image["width"] and image["srcset"] for image in images.values())
    assert images["home.hero"]["focal"] == {"x": 0.5, "y": 0.5}


def test_every_slot_is_what_the_site_asks_for():
    """The site names each slot once, through SiteImage or PageHero, and nothing else."""
    used = set()
    for path in FRONTEND.rglob("*.tsx"):
        if path.name.endswith(".test.tsx"):
            continue
        used |= set(re.findall(r'\bslot="([a-z]+\.[a-z_]+)"', path.read_text()))
    assert used == SLOTS


def test_the_api_is_public_and_checked_on_every_visit(client):
    response = client.get("/api/site-images/")
    assert response.status_code == 200
    assert response["Cache-Control"] == "public, no-cache"
    image = response.json()["images"]["about.hero"]
    assert set(image) == {"url", "alt", "width", "height", "srcset", "focal"}


# Uploading


@pytest.mark.parametrize(
    "fmt,name",
    [
        ("JPEG", "a.jpg"),
        ("PNG", "a.png"),
        ("WEBP", "a.webp"),
        ("AVIF", "a.avif"),
        ("HEIF", "a.heic"),
    ],
)
def test_every_photo_format_uploads(staff, fmt, name):
    client, _ = staff
    response = change(client, home(), picture(fmt, name=name), image_alt="New banner")
    assert response.status_code == 302
    slot = home()
    assert slot.image.name.startswith("site-images/") and slot.image.name.endswith(".webp")
    assert (slot.image_width, slot.image_height) == (1800, 1200)
    for width in (640, 1280):
        assert default_storage.exists(variant_name(slot.image.name, width))
    with default_storage.open(slot.image.name) as stored, Image.open(stored) as image:
        assert image.format == "WEBP" and not image.getexif()


def test_alt_text_is_required(staff):
    client, _ = staff
    before = home().image.name
    response = change(client, home(), picture(), image_alt="")
    assert response.status_code == 200
    assert "Describe the image for people using screen readers." in response.content.decode()
    assert home().image.name == before


def test_faces_need_confirmed_consent(staff):
    client, _ = staff
    response = change(client, home(), picture(), image_faces_visible="on")
    assert response.status_code == 200
    assert "cannot be published" in response.content.decode()
    response = change(
        client, home(), picture(), image_faces_visible="on", image_consent_confirmed="on"
    )
    assert response.status_code == 302
    assert home().image_consent_confirmed


def test_small_or_oddly_shaped_pictures_save_with_a_warning(staff):
    client, _ = staff
    response = change(client, home(), picture(size=(800, 640)))
    assert response.status_code == 302
    warnings = [str(m) for m in get_messages(response.wsgi_request)]
    assert any("smaller than the recommended 1600" in m for m in warnings)
    response = change(client, home(), picture(size=(3000, 800)))
    warnings = [str(m) for m in get_messages(response.wsgi_request)]
    assert any("far from 5/4" in m for m in warnings)
    assert home().image_width == 2400


# What the site shows


def test_an_empty_or_withheld_slot_shows_the_fallback(client):
    SiteImage.objects.filter(slot="about.hero").update(image_faces_visible=True)
    SiteImage.objects.filter(slot="visit.hero").update(image="")
    images = api_images(client)
    assert "about.hero" not in images and "visit.hero" not in images
    assert "home.hero" in images


def test_the_focal_point_reaches_the_site(staff, client):
    staff_client, _ = staff
    change(staff_client, home(), focal_x="0.2", focal_y="0.85")
    assert api_images(client)["home.hero"]["focal"] == {"x": 0.2, "y": 0.85}


def test_a_change_shows_at_once(staff, client):
    staff_client, _ = staff
    before = api_images(client)["home.hero"]["url"]  # cached now
    change(staff_client, home(), picture())
    after = api_images(client)["home.hero"]["url"]
    assert after != before and home().image.name in after


# History


def test_history_keeps_five_and_deletes_the_rest(staff):
    client, _ = staff
    names = []
    for _ in range(7):
        change(client, home(), picture())
        names.append(home().image.name)
    slot = home()
    assert slot.versions.count() == 5
    # The seed and the first upload were dropped; only the upload's files were this
    # test's to delete.
    kept = set(slot.versions.values_list("image", flat=True))
    assert kept == set(names[1:6])
    assert not default_storage.exists(names[0])
    assert not default_storage.exists(variant_name(names[0], 640))
    assert all(default_storage.exists(name) for name in names[1:])


def test_restore_previous_brings_the_last_picture_back(staff):
    client, user = staff
    seed = home().image.name
    change(client, home(), picture(), image_alt="New banner")
    replaced = home().image.name
    client.post(reverse("admin:pages_siteimage_restore_previous", args=[home().pk]))
    slot = home()
    assert slot.image.name == seed
    assert slot.image_alt.startswith("Black-and-white photograph")
    assert slot.updated_by == user
    assert list(slot.versions.values_list("image", flat=True)) == [replaced]


def test_restore_a_chosen_version(staff):
    client, _ = staff
    change(client, home(), picture(), image_alt="First")
    first = home().image.name
    change(client, home(), picture(), image_alt="Second")
    version = home().versions.get(image=first)
    client.post(reverse("admin:pages_siteimage_restore", args=[home().pk, version.pk]))
    assert (home().image.name, home().image_alt) == (first, "First")


def test_remove_shows_the_fallback_and_can_be_undone(staff, client):
    staff_client, _ = staff
    seed = home().image.name
    staff_client.post(reverse("admin:pages_siteimage_remove", args=[home().pk]))
    assert not home().image
    assert "home.hero" not in api_images(client)
    staff_client.post(reverse("admin:pages_siteimage_restore_previous", args=[home().pk]))
    assert home().image.name == seed


# Who may, and the record


@pytest.mark.parametrize("role,allowed", [(MODERATOR, False), (STAFF, True), (ADMIN, True)])
def test_staff_and_admin_edit_moderators_do_not(team, role, allowed):
    client, _ = team(role)
    pages = [
        client.get(reverse("admin:pages_siteimage_changelist")),
        client.get(reverse("admin:pages_siteimage_change", args=[home().pk])),
        client.post(reverse("admin:pages_siteimage_remove", args=[home().pk])),
    ]
    if allowed:
        assert [page.status_code for page in pages] == [200, 200, 302]
    else:
        assert all(page.status_code == 403 for page in pages)
        assert home().image


def test_changes_removals_and_restores_are_audited(staff):
    client, user = staff
    change(client, home(), picture())
    client.post(reverse("admin:pages_siteimage_remove", args=[home().pk]))
    client.post(reverse("admin:pages_siteimage_restore_previous", args=[home().pk]))
    entries = AuditLog.objects.filter(category="content", target_type="site_image")
    assert list(entries.order_by("pk").values_list("action", flat=True)) == [
        "site_image_replaced",
        "site_image_removed",
        "site_image_restored",
    ]
    assert {entry.target_ref for entry in entries} == {"home.hero"}
    assert {entry.actor for entry in entries} == {user}


# The admin pages


def test_page_images_are_grouped_by_page(staff):
    from django.contrib.auth.models import Permission

    client, user = staff
    user.user_permissions.add(Permission.objects.get(codename="view_pagecontent"))
    client = staff_login(Client(), user)
    SiteImage.objects.filter(slot="visit.hero").update(image="")
    page = client.get(reverse("admin:pages_siteimage_changelist") + "?page=home").content.decode()
    for name in ("Home", "About", "Plan your visit", "Guests", "Rentals", "Volunteer", "Donate"):
        assert f'<h2 class="rose-section-title">{name}</h2>' in page
    assert '<details class="rose-card rose-page-group" id="page-home" open>' in page
    assert '<details class="rose-card rose-page-group" id="page-about">' in page
    assert "Empty, showing fallback" in page
    assert reverse("admin:pages_pagecontent_changelist") + "?page__exact=home" in page
    assert "Home: top banner" in page and "Last updated" in page


def test_the_change_page_has_the_picker_previews_and_a_link_to_the_site(staff, settings):
    client, _ = staff
    page = client.get(reverse("admin:pages_siteimage_change", args=[home().pk])).content.decode()
    assert "data-focal-stage" in page and "pages/focal-point.js" in page
    assert 'data-ratio="5/4"' in page and 'data-ratio="4/5"' in page
    assert f'href="{settings.SITE_URL}/"' in page
    about = SiteImage.objects.get(slot="about.hero")
    page = client.get(reverse("admin:pages_siteimage_change", args=[about.pk])).content.decode()
    assert "Phones do not show this picture." in page


def test_the_words_link_needs_page_copy_access(staff):
    client, _ = staff
    page = client.get(reverse("admin:pages_siteimage_changelist")).content.decode()
    assert "Edit this page's words" not in page
