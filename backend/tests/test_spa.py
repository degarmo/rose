"""Django serves the built single-page app on the same origin as the API."""

import json
import re

import pytest

pytestmark = pytest.mark.django_db

INDEX = (
    "<!doctype html><html><head><title>Rose</title>"
    '<script type="module" src="/assets/index-AbC123.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)


@pytest.fixture
def dist(settings, tmp_path):
    (tmp_path / "index.html").write_text(INDEX)
    settings.FRONTEND_DIST = tmp_path
    return tmp_path


@pytest.mark.parametrize(
    "path", ["/", "/events", "/events/friday-social", "/members/feed", "/account/login"]
)
def test_client_routes_get_index_with_no_cache(client, dist, path):
    response = client.get(path)
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/html")
    assert response["Cache-Control"] == "no-cache"
    assert '<div id="root">' in response.content.decode()


def test_index_carries_the_page_images(client, dist):
    html = client.get("/").content.decode()
    data = re.search(r'<script type="application/json" id="rose-site-images">(.*?)</script>', html)
    images = json.loads(data.group(1))
    assert images["home.hero"]["alt"].startswith("Black-and-white photograph")
    assert images["home.hero"]["focal"] == {"x": 0.5, "y": 0.5}


def test_page_images_cannot_close_their_script_element(client, dist):
    from apps.pages.models import SiteImage

    SiteImage.objects.filter(slot="home.hero").update(image_alt="</script><script>alert(1)")
    html = client.get("/").content.decode()
    assert "</script><script>alert(1)" not in html
    assert "\\u003c/script>\\u003cscript>alert(1)" in html


def test_a_page_preloads_its_own_picture(client, dist):
    home = client.get("/", HTTP_COOKIE="age_ok=1").content.decode()
    assert 'rel="preload" as="image"' in home and "dance-floor-640w.webp 640w" in home
    about = client.get("/about", HTTP_COOKIE="age_ok=1").content.decode()
    assert 'media="(min-width: 1024px)"' in about and "pride-flag-640w.webp" in about
    events = client.get("/events", HTTP_COOKIE="age_ok=1").content.decode()
    assert 'rel="preload" as="image"' not in events


def test_index_preconnects_to_the_storage_origins(client, dist, settings):
    settings.MEDIA_ORIGINS = ["https://files.example", "https://public.example"]
    html = client.get("/members/feed").content.decode()
    assert '<link rel="preconnect" href="https://files.example" />' in html
    assert '<link rel="preconnect" href="https://public.example" />' in html


def test_index_has_no_preconnect_without_object_storage(client, dist, settings):
    settings.MEDIA_ORIGINS = []
    assert 'rel="preconnect"' not in client.get("/").content.decode()


@pytest.mark.parametrize(
    "path",
    [
        "/api/nothing-here/",
        "/admin/nothing-here/",
        "/media/feed/x.webp",
        "/static/missing.css",
        "/assets/missing.js",
        "/apple-touch-icon-precomposed.png",
        "/something.php",
    ],
)
def test_fallback_never_answers_for_api_admin_media_or_files(client, dist, path):
    response = client.get(path)
    # The admin redirects unknown paths to its login; everything else is a 404.
    assert response.status_code == (302 if path.startswith("/admin/") else 404)
    assert '<div id="root">' not in response.content.decode()


def test_moved_admin_path_is_excluded_too(client, dist, settings):
    settings.ADMIN_PATH = "staff-a8f3/"
    response = client.get("/staff-a8f3/anything/")
    assert response.status_code in (302, 404)  # the admin's own answer, never the app
    assert b'<div id="root">' not in response.content


def test_writes_are_not_served(client, dist):
    assert client.post("/events").status_code == 405


def test_missing_build_is_a_plain_404(client, settings, tmp_path):
    settings.FRONTEND_DIST = tmp_path / "missing"
    assert client.get("/").status_code == 404


def test_private_spa_routes_are_noindex(client, dist):
    assert client.get("/members/feed")["X-Robots-Tag"] == "noindex, nofollow"
    assert client.get("/members/settings")["X-Robots-Tag"] == "noindex, nofollow"
    assert client.get("/account/login")["X-Robots-Tag"] == "noindex, nofollow"
    assert "X-Robots-Tag" not in client.get("/events")


def test_the_membership_page_is_public_but_its_confirmation_is_not(client, dist):
    assert "X-Robots-Tag" not in client.get("/join")
    assert client.get("/join/confirming")["X-Robots-Tag"] == "noindex, nofollow"
