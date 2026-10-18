"""Django serves the built single-page app on the same origin as the API."""

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
    "path", ["/", "/events", "/events/friday-social", "/members/feed", "/account"]
)
def test_client_routes_get_index_with_no_cache(client, dist, path):
    response = client.get(path)
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/html")
    assert response["Cache-Control"] == "no-cache"
    assert '<div id="root">' in response.content.decode()


def test_index_carries_the_site_images_address(client, dist, settings):
    settings.SITE_IMAGES_URL = "https://media.site.example/site/"
    html = client.get("/").content.decode()
    assert '<meta name="rose-site-images" content="https://media.site.example/site/" />' in html


@pytest.mark.parametrize(
    "path",
    [
        "/api/nothing-here/",
        "/admin/nothing-here/",
        "/media/feed/x.webp",
        "/static/missing.css",
        "/assets/missing.js",
        "/favicon.ico",
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
    assert client.get("/account")["X-Robots-Tag"] == "noindex, nofollow"
    assert "X-Robots-Tag" not in client.get("/events")
