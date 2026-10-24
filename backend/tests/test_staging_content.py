"""Staging content: the committed site copy, and sample content with no people in it."""

import hashlib
import os
import re
from io import StringIO
from pathlib import Path

import pytest
import yaml
from django.core.files.storage import default_storage
from django.core.management import CommandError, call_command
from django.test import Client
from django.urls import reverse
from django.utils.timezone import localtime

from apps.accounts.models import User
from apps.core import checks
from apps.core.images import variant_name
from apps.core.models import SampleRecord
from apps.core.samples import is_sample, register
from apps.education.models import Opportunity
from apps.events.models import RSVP, Event
from apps.feed.models import Announcement, FeedComment, FeedPost, Report
from apps.journal.models import Post, PostImage
from apps.memberships.models import Membership, Payment
from apps.pages import samples
from apps.pages.models import FAQItem, PageContent, StaffProfile
from apps.pages.site_content import SITE_COPY_DIR
from tests.conftest import staff_login

pytestmark = pytest.mark.django_db

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
# The club's name, as a SHA-256 digest of its distinctive words (lowercase, single spaces)
# and their length, so this check runs everywhere without the name itself being committed.
CLUB_NAME_DIGEST = ("b71d4ef26df1aff976a2db8a4e671829b1ead8eba8f541436e1ca47881bb01ea", 12)
BADGE = re.compile(r">\s*Sample\s*<")
EMAIL = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
STREET = re.compile(
    r"\b\d{1,5}\s+(?:[NSEW]\.?\s+)?(?:[A-Z][a-z]+\s+){1,3}"
    r"(?:St|Street|Ave|Avenue|Blvd|Boulevard|Rd|Road|Dr|Drive|Ln|Lane|Pl|Place|Ct|Court|"
    r"Way|Pkwy|Parkway)\b\.?"
)


@pytest.fixture
def no_club_content(settings, tmp_path):
    """Only the committed copy: the club's own /content folder is not here."""
    settings.SITE_CONTENT_DIR = tmp_path / "no-content"
    return settings


@pytest.fixture
def small_pictures(monkeypatch):
    monkeypatch.setattr(samples, "PICTURE_WIDTH", 480)


def run(*args):
    out = StringIO()
    call_command(*args, stdout=out)
    return out.getvalue()


# The committed site copy


def test_the_site_copy_loads_by_default(no_club_content):
    out = run("load_site_content", "--commit")
    pages = set(PageContent.objects.values_list("page", flat=True))
    assert pages == {path.stem for path in SITE_COPY_DIR.glob("*.yaml")}
    assert {"home", "faq", "staff", "journal", "values", "privacy"} <= pages
    assert "home.yaml:" in out
    # Copy only: no people, and the club's name stays a placeholder.
    assert not StaffProfile.objects.exists()
    assert PageContent.objects.filter(value__contains="{display_name}").exists()


def test_every_committed_copy_file_is_a_draft(no_club_content):
    for path in SITE_COPY_DIR.glob("*.yaml"):
        data = yaml.safe_load(path.read_text())
        assert data["status"] == "draft - needs club approval", path.name
        assert "staff" not in data, f"{path.name} names people"


def test_the_clubs_own_files_load_after_the_copy(settings, tmp_path):
    folder = tmp_path / "content"
    folder.mkdir()
    (folder / "home.yaml").write_text(
        "status: approved\nsource_url: []\npage: home\ncopy:\n  hero:\n    title: Our words\n"
    )
    settings.SITE_CONTENT_DIR = folder
    run("load_site_content", "--commit")
    assert PageContent.objects.get(page="home", key="hero.title").value == "Our words"
    assert PageContent.objects.filter(page="about").exists()


def test_production_refuses_the_draft_copy_unless_allowed(no_club_content):
    no_club_content.DJANGO_ENV = "production"
    with pytest.raises(CommandError, match="still drafts"):
        run("load_site_content", "--commit")
    assert not PageContent.objects.exists()
    run("load_site_content", "--commit", "--allow-draft")
    assert PageContent.objects.filter(page="home").exists()


def test_copy_edited_in_the_admin_is_kept_unless_overwritten(no_club_content, admin_user):
    run("load_site_content", "--commit")
    entry = PageContent.objects.get(page="home", key="hero.lede")
    client = staff_login(Client(), admin_user)
    response = client.post(
        reverse("admin:pages_pagecontent_change", args=[entry.pk]),
        {"page": "home", "key": "hero.lede", "format": "plain", "value": "Written by staff."},
    )
    assert response.status_code == 302
    entry.refresh_from_db()
    assert entry.edited_in_admin and entry.value == "Written by staff."

    out = run("load_site_content", "--commit")
    entry.refresh_from_db()
    assert entry.value == "Written by staff."
    assert "home.yaml: 0 new, 0 changed" in out and "1 kept as edited in the admin" in out
    assert "Kept as edited in the admin (overwrite to replace them): home: hero.lede" in out

    run("load_site_content", "--commit", "--overwrite")
    entry.refresh_from_db()
    assert entry.value != "Written by staff." and not entry.edited_in_admin


# No names, addresses or emails in anything committed


def _local_values():
    """The club's real name and address, where this machine has them (never committed):
    the environment or backend/.env, and the club's own /content/site.yaml."""
    found = []
    env_file = BACKEND / ".env"
    lines = env_file.read_text().splitlines() if env_file.is_file() else []
    for key in ("SITE_DISPLAY_NAME", "SITE_SHORT_NAME"):
        values = [os.environ.get(key, "")]
        values += [line.split("=", 1)[1] for line in lines if line.startswith(f"{key}=")]
        found += [value.strip().strip("\"'") for value in values]
    site = REPO / "content" / "site.yaml"
    if site.is_file():
        settings_section = (yaml.safe_load(site.read_text()) or {}).get("site_settings") or {}
        for key in (
            "address_text",
            "phone_text",
            "mailing_address",
            "legal_name",
            "contact_email",
        ):
            found += str(settings_section.get(key) or "").splitlines()
    return {value.strip() for value in found if len(value.strip()) >= 6 and value != "Rose"}


def _committed_texts():
    texts = {path.name: path.read_text() for path in SITE_COPY_DIR.glob("*.yaml")}
    texts["samples.py"] = (BACKEND / "apps" / "pages" / "samples.py").read_text()
    return texts


def _names_the_club(text, digest_and_length=CLUB_NAME_DIGEST):
    digest, length = digest_and_length
    words = " ".join(text.lower().split())
    return any(
        hashlib.sha256(words[start : start + length].encode()).hexdigest() == digest
        for start in range(len(words) - length + 1)
    )


def test_no_committed_copy_names_the_club_an_address_or_an_email():
    forbidden = _local_values()
    for name, text in _committed_texts().items():
        assert not _names_the_club(text), f"{name} names the club; write {{display_name}}"
        assert not EMAIL.search(text), f"{name} has an email address"
        assert not STREET.search(text), f"{name} has a street address"
        for value in forbidden:
            assert value.lower() not in text.lower(), f"{name} has the club's own details"


def test_the_name_check_catches_what_it_looks_for():
    phrase = "quiet parlor"
    stand_in = (hashlib.sha256(phrase.encode()).hexdigest(), len(phrase))
    assert _names_the_club("Meet in the Quiet\n  Parlor tonight.", stand_in)
    assert not _names_the_club("Meet in the quiet room tonight.", stand_in)
    assert not _names_the_club("A members' club run by its members: {display_name}.")
    assert EMAIL.search("write to hello@club.example")
    assert STREET.search("Find us at 1234 N Milwaukee Ave.")
    assert not STREET.search("Doors open at 7 pm on Thursday")


# Sample content


@pytest.mark.parametrize(
    "env,debug", [("production", True), ("production", False), ("test", False)]
)
def test_samples_refuse_outside_staging_and_debug(settings, env, debug):
    settings.DJANGO_ENV, settings.DEBUG = env, debug
    with pytest.raises(CommandError, match="runs on staging or with DEBUG on"):
        run("load_staging_samples", "--commit")
    with pytest.raises(CommandError):
        run("load_staging_samples", "--purge")
    assert not SampleRecord.objects.exists()


def test_a_dry_run_writes_nothing(settings, small_pictures):
    settings.DEBUG = True
    out = run("load_staging_samples")
    assert "Events: 20 new" in out and "Dry run" in out
    assert not Event.objects.exists() and not SampleRecord.objects.exists()


def test_samples_follow_the_clubs_pattern_and_name_no_one(settings, small_pictures):
    settings.DJANGO_ENV = "staging"
    people = User.objects.count()
    run("load_staging_samples", "--commit")

    events = Event.objects.all()
    assert events.count() == 20
    thursdays = events.filter(category="education")
    assert thursdays.count() == 6

    def local_hours(event):
        return localtime(event.starts_at).hour, localtime(event.ends_at).hour

    # Thursdays 7 pm to midnight, alcohol-free; Fridays and Saturdays 9 pm to 2 am, BYOB.
    assert {(localtime(e.starts_at).weekday(), *local_hours(e)) for e in thursdays} == {(3, 19, 0)}
    assert all("alcohol-free" in event.body for event in thursdays)
    socials = events.filter(category="social")
    assert {local_hours(event) for event in socials} == {(21, 2)}
    assert sorted({localtime(e.starts_at).weekday() for e in socials}) == [4, 5]
    assert socials.count() == 12 and all("BYOB" in event.body for event in socials)
    assert events.filter(category="workshop").count() == 1
    assert events.filter(audience="members").count() == 1
    assert list(Event.objects.featured().values_list("category", flat=True)) == ["workshop"]
    assert all(event.hero_image and event.hero_image_alt for event in events)
    assert Opportunity.objects.count() == 6
    assert set(Opportunity.objects.values_list("level", flat=True)) == {
        "all",
        "beginner",
        "intermediate",
        "advanced",
    }
    assert FAQItem.objects.count() == len(samples.FAQS)
    assert Post.objects.count() == 3 and not Post.objects.exclude(author=None).exists()
    assert Announcement.objects.count() == 1

    # No people, and nothing that belongs to people.
    assert User.objects.count() == people
    for model in (StaffProfile, RSVP, Membership, Payment, Report, FeedPost, FeedComment):
        assert not model.objects.exists(), model.__name__
    # Every row is registered as a sample.
    for obj in [*events, *Opportunity.objects.all(), *FAQItem.objects.all(), *Post.objects.all()]:
        assert is_sample(obj)


def test_running_again_repairs_pictures_and_leaves_staff_rows_alone(settings, small_pictures):
    settings.DEBUG = True
    staff_faq = FAQItem.objects.create(slug="dress-code", question="Ours", answer="Ours.")
    run("load_staging_samples", "--commit")
    event = Event.objects.get(category="workshop")
    lost = event.hero_image.name
    default_storage.delete(lost)

    out = run("load_staging_samples", "--commit")
    event.refresh_from_db()
    assert event.hero_image.name != lost and default_storage.exists(event.hero_image.name)
    assert "Pictures drawn and stored (new or missing from storage): 1" in out
    assert "Events: 0 new, 20 already there (updated)" in out
    assert "FAQ questions dress-code exists and was not made here; left alone" in out
    staff_faq.refresh_from_db()
    assert staff_faq.question == "Ours" and not is_sample(staff_faq)


def test_samples_never_take_the_feature_from_staff(settings, small_pictures, make_event):
    settings.DEBUG = True
    ours = make_event(title="Our gala", is_featured=True)
    out = run("load_staging_samples", "--commit")
    assert list(Event.objects.featured()) == [ours]
    assert f"{ours.slug} is featured by staff; left as it is" in out


def test_purge_removes_only_samples_and_their_pictures(settings, small_pictures, make_event):
    settings.DEBUG = True
    ours = make_event(title="Our evening")
    our_faq = FAQItem.objects.create(slug="ours", question="Ours?", answer="Yes.")
    run("load_staging_samples", "--commit")
    files = []
    for event in Event.objects.exclude(pk=ours.pk):
        files += [event.hero_image.name, variant_name(event.hero_image.name, 400)]
    files += [image.image.name for image in PostImage.objects.all()]
    files += [o.hero_image.name for o in Opportunity.objects.all()]
    assert all(default_storage.exists(name) for name in files)

    out = run("load_staging_samples", "--purge")
    assert "Removed 20 events" in out
    assert list(Event.objects.all()) == [ours]
    assert list(FAQItem.objects.all()) == [our_faq]
    for model in (Opportunity, Post, PostImage, Announcement, SampleRecord):
        assert not model.objects.exists(), model.__name__
    assert not any(default_storage.exists(name) for name in files)


def test_the_public_site_never_shows_the_sample_badge(settings, small_pictures, api_client):
    settings.DEBUG = True
    run("load_staging_samples", "--commit")
    event = Event.objects.filter(category="education").first()
    for url in (
        "/api/events/",
        f"/api/events/{event.slug}/",
        "/api/events/featured/",
        "/api/education/opportunities/",
        "/api/faqs/",
        "/api/journal/posts/",
    ):
        response = api_client.get(url)
        assert response.status_code == 200, url
        body = response.content.decode()
        assert "is_sample" not in body and "Sample" not in body, url


def test_the_admin_lists_badge_samples(settings, small_pictures, admin_user, make_event):
    settings.DEBUG = True
    make_event(title="Our evening")
    run("load_staging_samples", "--commit")
    client = staff_login(Client(), admin_user)
    for name in (
        "events_event",
        "education_opportunity",
        "pages_faqitem",
        "journal_post",
        "feed_announcement",
    ):
        page = client.get(reverse(f"admin:{name}_changelist")).content.decode()
        # The column's heading, then one badge per sample row.
        assert len(BADGE.findall(page)) >= 2, name
    events = client.get(reverse("admin:events_event_changelist")).content.decode()
    assert len(BADGE.findall(events)) == 1 + 20


def test_production_refuses_to_start_with_samples(safe_production, make_event):
    event = make_event()
    assert "rose.E014" not in {m.id for m in checks.no_demo_seed(databases=["default"])}
    register(event)
    assert "rose.E014" in {m.id for m in checks.no_demo_seed(databases=["default"])}
    safe_production.DJANGO_ENV = "staging"
    assert "rose.E014" not in {m.id for m in checks.no_demo_seed(databases=["default"])}
