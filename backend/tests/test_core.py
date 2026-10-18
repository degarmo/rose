import pytest
from django.conf import settings
from django.core import mail
from django.test import RequestFactory

from apps.core.email import neutral_sender, send_neutral_mail
from apps.core.ratelimit import client_ip, hashed_ip_key

pytestmark = pytest.mark.django_db


def test_robots_txt_is_closed_outside_production(client):
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/plain")
    assert response.content.decode() == "User-agent: *\nDisallow: /\n"


def test_production_robots_lists_private_paths_but_never_the_admin(client, settings):
    settings.DJANGO_ENV = "production"
    settings.SITE_INDEXABLE = True
    settings.ADMIN_PATH = "staff-a8f3/"
    body = client.get("/robots.txt").content.decode()
    assert "Disallow: /members" in body and "Disallow: /account" in body
    assert "staff-a8f3" not in body and "admin" not in body


@pytest.mark.parametrize("url", ["/api/csrf/", "/api/faqs/", "/admin/login/", "/members/x"])
def test_private_paths_are_noindex(client, url):
    response = client.get(url)
    assert response["X-Robots-Tag"] == "noindex, nofollow"


def test_api_responses_are_not_cached(client):
    assert client.get("/api/faqs/")["Cache-Control"] == "no-store"


def test_robots_txt_has_no_robots_header(client):
    assert "X-Robots-Tag" not in client.get("/robots.txt")


def test_security_headers_present(client):
    response = client.get("/api/csrf/")
    csp = response["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert response["X-Frame-Options"] == "DENY"
    assert response["Referrer-Policy"] == "no-referrer"
    assert "geolocation=()" in response["Permissions-Policy"]


def test_csrf_endpoint_returns_token_and_httponly_cookie(client):
    response = client.get("/api/csrf/")
    assert response.status_code == 200
    assert len(response.json()["csrfToken"]) >= 32
    cookie = response.cookies[settings.CSRF_COOKIE_NAME]
    assert cookie["httponly"]
    assert cookie["samesite"] == "Strict"


def test_health(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.content == b"ok"
    assert response["Cache-Control"] == "no-store"


def test_password_hashing_and_cookie_baseline():
    assert settings.PASSWORD_HASHERS[0].endswith("Argon2PasswordHasher")
    assert settings.SESSION_COOKIE_HTTPONLY is True
    assert settings.CSRF_COOKIE_HTTPONLY is True
    assert "csp.middleware.CSPMiddleware" in settings.MIDDLEWARE
    assert "django.middleware.csrf.CsrfViewMiddleware" in settings.MIDDLEWARE


def test_rest_framework_serves_json_only():
    assert settings.REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] == [
        "rest_framework.renderers.JSONRenderer"
    ]


def test_neutral_mail_uses_configured_sender(settings):
    settings.EMAIL_SENDER_NAME = "Notices"
    settings.EMAIL_SENDER_ADDRESS = "notices@example.org"
    assert neutral_sender() == "Notices <notices@example.org>"
    send_neutral_mail("Hello", "Body", to=["x@example.org"], reply_to=["r@example.org"])
    assert mail.outbox[0].from_email == "Notices <notices@example.org>"
    assert mail.outbox[0].reply_to == ["r@example.org"]
    message_id = mail.outbox[0].message()["Message-ID"]
    assert message_id.endswith("@example.org>")


def test_client_ip_without_proxy_uses_remote_addr(settings):
    settings.TRUSTED_PROXY_COUNT = 0
    request = RequestFactory().get("/", REMOTE_ADDR="198.51.100.7", HTTP_X_FORWARDED_FOR="1.1.1.1")
    assert client_ip(request) == "198.51.100.7"


def test_client_ip_with_two_proxies(settings):
    settings.TRUSTED_PROXY_COUNT = 2
    request = RequestFactory().get(
        "/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="forged, 203.0.113.9, 10.0.0.2"
    )
    assert client_ip(request) == "203.0.113.9"


def test_ratelimit_key_never_contains_raw_ip():
    request = RequestFactory().get("/", REMOTE_ADDR="198.51.100.7")
    key = hashed_ip_key("contact", request)
    assert "198.51.100.7" not in key
    assert len(key) == 64


def test_csrf_failure_is_json():
    from rest_framework.test import APIClient

    response = APIClient(enforce_csrf_checks=True).post("/api/contact/", {}, format="json")
    assert response.status_code == 403
    assert response.json()["detail"].startswith("CSRF Failed")


def test_staging_is_never_indexable(client, settings):
    settings.DJANGO_ENV = "staging"
    settings.SITE_INDEXABLE = True
    settings.STAGING_BASIC_AUTH_USER = ""
    from django.test import RequestFactory

    from apps.core.views import robots_txt

    body = robots_txt(RequestFactory().get("/robots.txt")).content.decode()
    assert body == "User-agent: *\nDisallow: /\n"
