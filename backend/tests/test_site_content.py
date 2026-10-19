"""load_site_content, editable page copy and its cached API, staff profiles and redirects."""

from io import StringIO
from pathlib import Path

import pytest
import yaml
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command
from django.urls import reverse

from apps.core.models import AuditLog
from apps.pages.content import BUILTIN_REDIRECTS
from apps.pages.models import FAQItem, PageContent, Redirect, SiteSettings, StaffProfile

pytestmark = pytest.mark.django_db
REPO = Path(__file__).resolve().parents[2]
REDIRECTS_YAML = REPO / "content" / "redirects.yaml"
DEMO_CONTENT = Path(__file__).resolve().parents[1] / "apps" / "pages" / "demo_content"


@pytest.fixture
def content_dir(tmp_path):
    folder = tmp_path / "content"
    folder.mkdir()
    (folder / "about.yaml").write_text(
        yaml.safe_dump(
            {
                "status": "draft - needs club approval",
                "source_url": ["https://old.example/about"],
                "page": "about",
                "copy": {
                    "hero": {"title": "About us", "lede": {"rich": "<p>Hi<script>x</script></p>"}},
                    "steps": [{"title": "One"}, {"title": "Two"}],
                },
                "site_settings": {"tagline": "A tagline", "hours_text": "Thursdays"},
                "faqs": [{"slug": "parking", "question": "Parking?", "answer": "The lot."}],
                "staff": [{"slug": "wren", "display_name": "Wren", "role_title": "Host"}],
                "tiers": [{"slug": "monthly", "price_cents": 4000}],
                "redirects": [{"from": "/Our-Staff/", "to": "/about/staff"}],
            }
        )
    )
    return folder


def run(*args):
    out = StringIO()
    call_command("load_site_content", *args, stdout=out)
    return out.getvalue()


def test_dry_run_writes_nothing(content_dir, make_tier):
    make_tier(slug="monthly")
    output = run("--dir", str(content_dir))
    assert "Dry run" in output and "about.yaml: 7 new, 2 changed" in output
    assert not PageContent.objects.exists() and not FAQItem.objects.exists()
    assert not AuditLog.objects.exists()


def test_commit_loads_every_section(content_dir, make_tier):
    tier = make_tier(slug="monthly", name="Monthly", price_cents=2500)
    run("--dir", str(content_dir), "--commit")
    copy = dict(PageContent.objects.filter(page="about").values_list("key", "value"))
    assert copy["hero.title"] == "About us"
    assert copy["steps.1.title"] == "One" and copy["steps.2.title"] == "Two"
    assert copy["hero.lede"] == "<p>Hi</p>"  # sanitised
    assert PageContent.objects.get(key="hero.lede").format == "rich"
    site = SiteSettings.load()
    assert (site.tagline, site.hours_text) == ("A tagline", "Thursdays")
    assert FAQItem.objects.get(slug="parking").question == "Parking?"
    assert StaffProfile.objects.get(slug="wren").is_published is True
    tier.refresh_from_db()
    assert tier.price_cents == 4000 and tier.name == "Monthly"
    assert Redirect.objects.get().old_path == "/our-staff"
    assert AuditLog.objects.get(category="content").action == "load_site_content"


def test_loading_is_idempotent_and_never_deletes(content_dir, make_tier):
    make_tier(slug="monthly")
    run("--dir", str(content_dir), "--commit")
    PageContent.objects.create(page="about", key="extra", value="Staff added this")
    output = run("--dir", str(content_dir), "--commit")
    assert "about.yaml: 0 new, 0 changed, 9 unchanged" in output, output
    assert PageContent.objects.filter(key="extra").exists()


def test_tier_prices_only_change_when_given(content_dir, make_tier):
    tier = make_tier(slug="monthly", price_cents=2500)
    data = yaml.safe_load((content_dir / "about.yaml").read_text())
    data["tiers"] = [{"slug": "monthly", "description": "New words"}]
    (content_dir / "about.yaml").write_text(yaml.safe_dump(data))
    run("--dir", str(content_dir), "--commit")
    tier.refresh_from_db()
    assert tier.price_cents == 2500 and tier.description == "New words"


def test_a_new_tier_needs_a_price(content_dir):
    with pytest.raises(CommandError, match="needs a name, an interval and a price"):
        run("--dir", str(content_dir), "--commit")
    assert not PageContent.objects.exists()  # all or nothing


def test_files_need_status_and_sources(tmp_path):
    (tmp_path / "x.yaml").write_text("page: home\ncopy: {a: b}\n")
    with pytest.raises(CommandError, match="missing `status`"):
        run("--dir", str(tmp_path))


def test_production_refuses_drafts(content_dir, settings, make_tier):
    make_tier(slug="monthly")
    settings.DJANGO_ENV = "production"
    with pytest.raises(CommandError, match="still drafts"):
        run("--dir", str(content_dir), "--commit")
    assert not PageContent.objects.exists()


def test_allow_draft_in_production_is_logged(content_dir, settings, make_tier):
    make_tier(slug="monthly")
    settings.DJANGO_ENV = "production"
    run("--dir", str(content_dir), "--commit", "--allow-draft")
    actions = set(AuditLog.objects.filter(category="content").values_list("action", flat=True))
    assert actions == {"load_site_content", "load_draft_content"}
    assert "about.yaml" in AuditLog.objects.get(action="load_draft_content").reason


def test_approved_files_load_in_production(content_dir, settings, make_tier):
    make_tier(slug="monthly")
    path = content_dir / "about.yaml"
    path.write_text(path.read_text().replace("draft - needs club approval", "approved"))
    settings.DJANGO_ENV = "production"
    run("--dir", str(content_dir), "--commit")
    assert PageContent.objects.filter(page="about").exists()


def test_superusers_can_load_content_by_upload(admin_client, content_dir, make_tier):
    make_tier(slug="monthly")
    url = reverse("admin:pages_load_content")
    upload = SimpleUploadedFile("about.yaml", (content_dir / "about.yaml").read_bytes())
    page = admin_client.post(url, {"files": upload}).content.decode()
    assert "Dry run, nothing written" in page and not PageContent.objects.exists()
    upload = SimpleUploadedFile("about.yaml", (content_dir / "about.yaml").read_bytes())
    admin_client.post(url, {"files": upload, "commit": "on"})
    assert PageContent.objects.filter(page="about").count() == 4


def test_only_superusers_may_upload_content(client, desk_staff):
    from tests.conftest import staff_login

    staff_login(client, desk_staff)
    assert client.get(reverse("admin:pages_load_content")).status_code == 403


def test_the_demo_content_loads_cleanly():
    out = StringIO()
    call_command("load_site_content", "--dir", str(DEMO_CONTENT), "--commit", stdout=out)
    pages = set(PageContent.objects.values_list("page", flat=True))
    assert {
        "home",
        "about",
        "visit",
        "guests",
        "rentals",
        "volunteer",
        "donate",
        "privacy",
    } <= pages


# The cached, read-only page copy API


def test_page_copy_api_is_cached_and_refreshed_on_edit(api_client, django_assert_num_queries):
    entry = PageContent.objects.create(page="home", key="hero.title", value="Hello")
    cache.clear()
    first = api_client.get("/api/content/home/")
    assert first.json() == {
        "page": "home",
        "entries": {"hero.title": {"value": "Hello", "format": "plain"}},
    }
    assert first["Cache-Control"] == "public, max-age=60"
    with django_assert_num_queries(0):
        api_client.get("/api/content/home/")
    entry.value = "Welcome"
    entry.save()
    assert (
        api_client.get("/api/content/home/").json()["entries"]["hero.title"]["value"] == "Welcome"
    )
    entry.delete()
    assert api_client.get("/api/content/home/").json()["entries"] == {}


def test_page_copy_is_read_only(csrf_client):
    response = csrf_client.post("/api/content/home/", {}, format="json")
    assert response.status_code == 405


def test_bad_keys_are_refused():
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        PageContent(page="home", key="Hero Title!", value="x").full_clean()


# Staff profiles


def test_staff_list_shows_only_published_profiles_and_no_account(api_client, member):
    StaffProfile.objects.create(
        slug="wren", display_name="Wren", role_title="Host", is_published=True, user=member
    )
    StaffProfile.objects.create(slug="ash", display_name="Ash", role_title="Safety")
    data = api_client.get("/api/staff/").json()
    assert data == [
        {"slug": "wren", "display_name": "Wren", "role_title": "Host", "bio": "", "photo": None}
    ]
    body = api_client.get("/api/staff/").content.decode()
    assert member.email not in body and member.display_name not in body


# Redirects from the old site


def committed_redirects():
    data = yaml.safe_load(REDIRECTS_YAML.read_text())
    return [(item["from"], item["to"]) for item in data["redirects"]]


def test_the_redirect_file_loads():
    run("--dir", str(REDIRECTS_YAML.parent), "redirects.yaml", "--commit")
    assert Redirect.objects.count() == len(committed_redirects())


@pytest.mark.parametrize(("old", "new"), committed_redirects())
def test_every_old_address_redirects(client, old, new):
    run("--dir", str(REDIRECTS_YAML.parent), "redirects.yaml", "--commit")
    path = old.replace("/*", "/some-page-under-it")
    response = client.get(path)
    assert response.status_code == 301, path
    assert response["Location"] == new
    # Case and a trailing slash do not matter.
    assert client.get(path.upper() + "/").status_code == 301


def test_gallery_moves_to_the_journal_even_without_a_table(client):
    assert not Redirect.objects.exists()
    response = client.get("/gallery")
    assert (response.status_code, response["Location"]) == (301, "/journal")
    assert BUILTIN_REDIRECTS["/gallery"] == "/journal"


def test_unknown_old_paths_fall_through(client, settings, tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><head></head><body>app</body></html>")
    settings.FRONTEND_DIST = dist
    run("--dir", str(REDIRECTS_YAML.parent), "redirects.yaml", "--commit")
    response = client.get("/category/bar")
    assert response.status_code == 200 and b"app" in response.content  # the site's own 404


def test_redirects_never_touch_the_api_or_admin(client):
    Redirect.objects.create(old_path="/api/csrf/*", new_path="/elsewhere")
    Redirect.objects.create(old_path="/admin/*", new_path="/elsewhere")
    assert client.get("/api/csrf/").status_code == 200
    assert client.get("/admin/login/").status_code == 200


def test_redirect_cache_refreshes_on_edit(client):
    redirect = Redirect.objects.create(old_path="/old", new_path="/visit")
    assert client.get("/old")["Location"] == "/visit"
    redirect.new_path = "/faq"
    redirect.save()
    assert client.get("/old")["Location"] == "/faq"
