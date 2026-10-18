"""Staging and production refuse to start with anything unsafe."""

import base64

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.core.management import CommandError, call_command

from apps.core import checks
from apps.core.models import SeedMarker

pytestmark = pytest.mark.django_db

STRONG_KEY = "k7#Qm9!vR2@xL5$wT8^zN3&bJ6*hF1(pD4)sG0_yC9+eA2-uK7=iO5~"


@pytest.fixture
def safe_production(settings):
    """A configuration that passes every check; each test breaks one thing."""
    settings.DJANGO_ENV = "production"
    settings.DEBUG = False
    settings.SECRET_KEY = STRONG_KEY
    settings.ALLOWED_HOSTS = ["site.example"]
    settings.CSRF_TRUSTED_ORIGINS = ["https://site.example"]
    settings.PAYMENT_PROVIDERS = ["manual"]
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {"BACKEND": "apps.core.storage.PublicS3Storage"},
        "private": {"BACKEND": "apps.core.storage.PrivateS3Storage"},
    }
    settings.S3_ENDPOINT_URL = "https://account.r2.cloudflarestorage.com"
    settings.S3_BROWSER_ENDPOINT_URL = "https://account.r2.cloudflarestorage.com"
    settings.S3_PUBLIC_BASE_URL = "https://media.site.example"
    settings.S3_ACCESS_KEY_ID = "key"
    settings.S3_SECRET_ACCESS_KEY = "secret"
    settings.S3_PUBLIC_BUCKET = "site-public"
    settings.S3_PRIVATE_BUCKET = "site-private"
    settings.EMAIL_BACKEND = "anymail.backends.postmark.EmailBackend"
    settings.ADMIN_PATH = "staff-a8f3/"
    settings.SECURE_SSL_REDIRECT = True
    settings.SESSION_COOKIE_SECURE = True
    settings.CSRF_COOKIE_SECURE = True
    settings.SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
    settings.SECURE_CONTENT_TYPE_NOSNIFF = True
    settings.SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    return settings


def ids():
    found = checks.deployment_settings() + checks.no_demo_seed(databases=["default"])
    return {error.id for error in found}


def test_safe_configuration_passes(safe_production):
    assert ids() == set()
    checks.assert_deploy_safe()


def test_development_is_never_checked(settings):
    settings.DJANGO_ENV = "development"
    settings.DEBUG = True
    assert checks.deployment_settings() == []


@pytest.mark.parametrize(
    "setting,value,code",
    [
        ("DEBUG", True, "rose.E001"),
        ("PAYMENT_PROVIDERS", ["manual", "sandbox"], "rose.E002"),
        ("SECRET_KEY", "short", "rose.E003"),
        ("SECRET_KEY", "django-insecure-" + "a1b2c3d4e5f6g7h8i9j0" * 3, "rose.E003"),
        ("SECRET_KEY", "local-development-only-not-a-secret" * 2, "rose.E003"),
        ("SECRET_KEY", "a" * 80, "rose.E003"),
        ("ALLOWED_HOSTS", [], "rose.E004"),
        ("ALLOWED_HOSTS", ["*"], "rose.E004"),
        ("CSRF_TRUSTED_ORIGINS", [], "rose.E005"),
        ("CSRF_TRUSTED_ORIGINS", ["http://site.example"], "rose.E005"),
        ("S3_PUBLIC_BUCKET", "", "rose.E006"),
        ("S3_ENDPOINT_URL", "http://localhost:9000", "rose.E006"),
        ("S3_ENDPOINT_URL", "https://minio:9000", "rose.E006"),
        ("S3_PRIVATE_BUCKET", "site-public", "rose.E006"),
        ("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend", "rose.E007"),
        ("EMAIL_BACKEND", "django.core.mail.backends.locmem.EmailBackend", "rose.E007"),
        ("ADMIN_PATH", "admin/", "rose.E008"),
        ("SECURE_SSL_REDIRECT", False, "rose.E009"),
        ("SESSION_COOKIE_SECURE", False, "rose.E009"),
        ("CSRF_COOKIE_SECURE", False, "rose.E009"),
        ("SECURE_HSTS_SECONDS", 3600, "rose.E009"),
        ("SECURE_CONTENT_TYPE_NOSNIFF", False, "rose.E009"),
        ("SECURE_PROXY_SSL_HEADER", None, "rose.E009"),
    ],
)
def test_each_unsafe_setting_is_refused(safe_production, setting, value, code):
    setattr(safe_production, setting, value)
    assert ids() == {code}
    with pytest.raises(ImproperlyConfigured, match=code):
        checks.assert_deploy_safe()


def test_local_storage_is_refused(safe_production):
    safe_production.STORAGES = {
        **safe_production.STORAGES,
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    }
    assert ids() == {"rose.E006"}


def test_seed_data_is_refused(safe_production):
    SeedMarker.objects.create()
    assert ids() == {"rose.E010"}
    with pytest.raises(ImproperlyConfigured, match="rose.E010"):
        checks.assert_deploy_safe()


def test_sandbox_cannot_be_enabled_even_if_debug_were_forced(safe_production):
    safe_production.DEBUG = True
    safe_production.PAYMENT_PROVIDERS = ["manual", "sandbox"]
    assert {"rose.E001", "rose.E002"} <= ids()


def test_staging_needs_basic_auth_and_manual_only(safe_production):
    safe_production.DJANGO_ENV = "staging"
    safe_production.STAGING_BASIC_AUTH_USER = ""
    assert ids() == {"rose.E011"}
    safe_production.STAGING_BASIC_AUTH_USER = "viewer"
    safe_production.STAGING_BASIC_AUTH_PASSWORD = "a-long-staging-password"
    assert ids() == set()
    safe_production.PAYMENT_PROVIDERS = ["manual", "stripe"]
    assert ids() == {"rose.E002"}


def test_manage_check_reports_them(safe_production, capsys):
    safe_production.ADMIN_PATH = "admin/"
    with pytest.raises(Exception, match="rose.E008"):
        call_command("check", "--database", "default", "--fail-level", "ERROR")


@pytest.mark.parametrize("env", ["staging", "production"])
def test_seed_demo_refuses_in_deployed_environments(settings, env):
    settings.DJANGO_ENV = env
    with pytest.raises(CommandError, match=env):
        call_command("seed_demo")
    assert not SeedMarker.objects.exists()


# Staging gate


@pytest.fixture
def staging(settings):
    settings.DJANGO_ENV = "staging"
    settings.STAGING_BASIC_AUTH_USER = "viewer"
    settings.STAGING_BASIC_AUTH_PASSWORD = "a-long-staging-password"
    return settings


def basic(user, password):
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def staging_client():
    from django.test import Client

    # The middleware reads DJANGO_ENV when it is created, so build a fresh handler.
    return Client()


@pytest.mark.parametrize("path", ["/", "/api/faqs/", "/admin/login/", "/events/x", "/robots.txt"])
def test_staging_requires_basic_auth_everywhere(staging, path):
    response = staging_client().get(path)
    assert response.status_code == 401
    assert response["WWW-Authenticate"].startswith("Basic")
    assert "noindex" in response["X-Robots-Tag"]


def test_staging_accepts_the_right_password_only(staging):
    client = staging_client()
    assert client.get("/api/faqs/", HTTP_AUTHORIZATION=basic("viewer", "wrong")).status_code == 401
    response = client.get(
        "/api/faqs/", HTTP_AUTHORIZATION=basic("viewer", "a-long-staging-password")
    )
    assert response.status_code == 200
    assert "noindex" in response["X-Robots-Tag"]


def test_staging_leaves_health_and_webhooks_open(staging):
    client = staging_client()
    assert client.get("/healthz").status_code == 200
    response = client.post(
        "/api/payments/webhook/manual/", data=b"{}", content_type="application/json"
    )
    assert response.status_code == 404  # reached the app (manual has no webhook), not 401
    assert "noindex" in response["X-Robots-Tag"]


def test_production_has_no_gate(settings):
    settings.DJANGO_ENV = "production"
    assert staging_client().get("/api/faqs/").status_code == 200


# Health


def test_health_reports_failure_without_details(client, monkeypatch):
    from django.core.cache import cache

    def broken(*args, **kwargs):
        raise ConnectionError("cache host 10.0.0.5 refused")

    monkeypatch.setattr(cache, "set", broken)
    response = client.get("/healthz")
    assert response.status_code == 503
    assert response.content == b"unavailable"


def test_health_skips_host_validation(client, settings):
    settings.ALLOWED_HOSTS = ["site.example"]
    assert client.get("/healthz", HTTP_HOST="10.1.2.3:10000").status_code == 200


@pytest.mark.parametrize("env", ["development", "staging", "production"])
def test_e2e_fixtures_only_run_in_e2e(settings, env):
    settings.DJANGO_ENV = env
    with pytest.raises(CommandError, match="DJANGO_ENV=e2e"):
        call_command("e2e_fixtures")


def test_e2e_fixtures_build_known_data(settings, capsys):
    import json

    from django_otp.oath import totp
    from django_otp.plugins.otp_totp.models import TOTPDevice

    settings.DJANGO_ENV = "e2e"
    call_command("e2e_fixtures", "--json")
    data = json.loads(capsys.readouterr().out)
    assert set(data["viewports"]) == {"phone", "desktop"}
    device = TOTPDevice.objects.get(user__email=data["staff"]["email"])
    assert device.verify_token(f"{totp(device.bin_key):06d}")
    call_command("e2e_fixtures")  # idempotent
