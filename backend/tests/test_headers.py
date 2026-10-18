"""The final header audit: a public page, a member page, an admin page and the media view."""

import re

import pytest
from django.urls import reverse

from tests.conftest import staff_login

pytestmark = pytest.mark.django_db


@pytest.fixture
def dist(settings, tmp_path):
    (tmp_path / "index.html").write_text("<!doctype html><html><head></head><body></body></html>")
    settings.FRONTEND_DIST = tmp_path


@pytest.fixture
def photo_url(make_member, make_post):
    post = make_post(make_member(display_name="photo_author"), images=1)
    return f"/api/members/media/{post.images.get().public_id}/"


def directives(csp):
    return {
        part.split()[0]: part.split()[1:] for part in (p.strip() for p in csp.split(";")) if part
    }


def assert_baseline(response, referrer="no-referrer", camera="()"):
    csp = directives(response["Content-Security-Policy"])
    assert csp["default-src"] == ["'self'"]
    assert "'unsafe-inline'" not in csp["script-src"] and "'unsafe-eval'" not in csp["script-src"]
    assert all(
        source in ("'self'",) or source.startswith("'nonce-") for source in csp["script-src"]
    )
    assert csp["frame-ancestors"] == ["'none'"]
    assert csp["object-src"] == ["'none'"]
    assert csp["base-uri"] == ["'self'"]
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["X-Frame-Options"] == "DENY"
    assert response["Cross-Origin-Opener-Policy"] == "same-origin"
    assert response["Referrer-Policy"] == referrer
    policy = response["Permissions-Policy"]
    assert f"camera={camera}" in policy
    for feature in ("microphone", "geolocation", "payment", "usb", "browsing-topics"):
        assert f"{feature}=()" in policy
    assert "interest-cohort" not in policy


def test_public_page(client, dist):
    response = client.get("/events")
    assert response.status_code == 200
    assert_baseline(response)
    assert "X-Robots-Tag" not in response


def test_member_page_and_api(member_client, dist):
    client, _ = member_client()
    page = client.get("/members/feed")
    assert_baseline(page)
    assert page["X-Robots-Tag"] == "noindex, nofollow"
    api = client.get("/api/members/feed/")
    assert api.status_code == 200
    assert_baseline(api)
    assert api["Cache-Control"] == "no-store"


def test_admin_page(admin_client):
    response = admin_client.get(reverse("admin:index"))
    assert response.status_code == 200
    # Django's own admin forms post with an Origin header that no-referrer would null.
    assert_baseline(response, referrer="same-origin")
    assert response["X-Robots-Tag"] == "noindex, nofollow"


def test_admin_login_page(client):
    assert_baseline(client.get(reverse("admin:login")), referrer="same-origin")


def test_media_view(member_client, photo_url, settings):
    settings.FEED_WATERMARK = False
    client, _ = member_client()
    response = client.get(photo_url)
    assert response.status_code == 200
    assert_baseline(response)
    assert response["Cache-Control"] == "private, no-store, max-age=0"
    assert response["Cross-Origin-Resource-Policy"] == "same-origin"


def test_only_the_door_desk_may_use_the_camera(client, desk_staff):
    staff_login(client, desk_staff)
    desk = client.get(reverse("admin:memberships_door_desk"))
    assert_baseline(desk, referrer="same-origin", camera="(self)")
    other = client.get(reverse("admin:memberships_summary"))
    assert "camera=()" in other["Permissions-Policy"]


def test_no_response_reveals_the_django_version(client, admin_client, dist):
    import django

    version = re.escape(django.get_version())
    for response in (
        client.get("/"),
        client.get("/api/faqs/"),
        client.get("/api/nothing/"),
        client.get(reverse("admin:login")),
        admin_client.get(reverse("admin:index")),
    ):
        text = response.content.decode(errors="ignore") + str(dict(response.headers))
        assert not re.search(version, text)
        assert "Django" not in response.get("Server", "")
