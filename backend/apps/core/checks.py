"""Deployment safety checks. Staging and production refuse to start if any fails.

They run as Django system checks (so `manage.py check --deploy --database
default` reports them) and again at process start in config/wsgi.py and
config/celery.py through assert_deploy_safe(). Development-only pieces (DEBUG,
the sandbox payment provider, demo seed data, MinIO, console email) can
therefore never run in a deployed environment. The one exception is a staging
preview (apps.core.preview): local storage and console email become warnings
there, and nowhere else.
"""

import logging
from urllib.parse import urlsplit

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register, run_checks
from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError

from .preview import STARTUP_WARNING, preview_active

logger = logging.getLogger("rose.preview")

S3_BACKENDS = {"apps.core.storage.PublicS3Storage", "apps.core.storage.PrivateS3Storage"}
LOCAL_BACKENDS = {
    "django.core.files.storage.FileSystemStorage",
    "apps.core.private_media.PrivateFileSystemStorage",
}
UNSAFE_EMAIL = {
    "django.core.mail.backends.console.EmailBackend",
    "django.core.mail.backends.locmem.EmailBackend",
    "django.core.mail.backends.filebased.EmailBackend",
    "django.core.mail.backends.dummy.EmailBackend",
    "apps.core.preview.LogEmailBackend",
}
WEAK_KEY_MARKERS = ("django-insecure", "change-me", "not-a-secret", "local-development", "dummy")
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "minio", "host.docker.internal"}
ONE_YEAR = 60 * 60 * 24 * 365


def deployed():
    return settings.DJANGO_ENV in settings.DEPLOYED_ENVS


def weak_secret(key):
    lowered = key.lower()
    return len(key) < 50 or len(set(key)) < 10 or any(m in lowered for m in WEAK_KEY_MARKERS)


def _error(code, message, hint=""):
    return Error(message, hint=hint or None, id=f"rose.{code}")


def _warning(code, message, hint=""):
    return Warning(message, hint=hint or None, id=f"rose.{code}")


@register(Tags.security, deploy=False)
def deployment_settings(app_configs=None, **kwargs):
    if not deployed():
        return []
    env = settings.DJANGO_ENV
    errors = []
    if settings.DEBUG:
        errors.append(_error("E001", f"DEBUG is on in {env}."))
    if "sandbox" in settings.PAYMENT_PROVIDERS:
        errors.append(_error("E002", "The sandbox payment provider is enabled."))
    if env == "staging" and list(settings.PAYMENT_PROVIDERS) != ["manual"]:
        errors.append(
            _error("E002", "Staging takes in-person payments only.", "PAYMENT_PROVIDERS=manual")
        )
    if weak_secret(settings.SECRET_KEY):
        errors.append(
            _error("E003", "DJANGO_SECRET_KEY is weak or a default.", "Use 50+ random characters.")
        )
    if not settings.ALLOWED_HOSTS or "*" in settings.ALLOWED_HOSTS:
        errors.append(_error("E004", "DJANGO_ALLOWED_HOSTS is missing or a wildcard."))
    origins = settings.CSRF_TRUSTED_ORIGINS
    if not origins or any(not origin.startswith("https://") for origin in origins):
        errors.append(_error("E005", "DJANGO_CSRF_TRUSTED_ORIGINS is missing or not all https."))
    if settings.PREVIEW_MODE and env == "production":
        errors.append(
            _error(
                "E013",
                "PREVIEW_MODE is on in production.",
                "Remove PREVIEW_MODE. It is for staging only.",
            )
        )
    errors.extend(_storage_errors())
    errors.extend(_email_errors())
    if settings.ADMIN_PATH.strip("/") == "admin":
        errors.append(
            _error("E008", "The admin is at the default /admin/ path.", "Set DJANGO_ADMIN_PATH.")
        )
    errors.extend(_transport_errors())
    if env == "staging" and not (
        settings.STAGING_BASIC_AUTH_USER and settings.STAGING_BASIC_AUTH_PASSWORD
    ):
        errors.append(_error("E011", "Staging needs STAGING_BASIC_AUTH_USER and _PASSWORD."))
    if settings.DEV_SKIP_STAFF_2FA:
        errors.append(
            _error(
                "E012",
                "DEV_SKIP_STAFF_2FA is on: the staff section would skip the two-step login.",
                "Remove DEV_SKIP_STAFF_2FA. It is for local development only.",
            )
        )
    return errors


def _storage_errors():
    backends = {settings.STORAGES["default"]["BACKEND"], settings.STORAGES["private"]["BACKEND"]}
    if backends == LOCAL_BACKENDS and preview_active():
        return [
            _warning(
                "W006",
                "Preview mode: uploads are kept on this container's disk and are lost on every "
                "redeploy. Private media is still served only through its access-checked view.",
                "Set STORAGE_BACKEND=s3 and the S3_* settings, then remove PREVIEW_MODE.",
            )
        ]
    if backends != S3_BACKENDS:
        return [_error("E006", "Media is not on S3-compatible storage.", "STORAGE_BACKEND=s3")]
    errors = []
    required = (
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
        "S3_PUBLIC_BUCKET",
        "S3_PRIVATE_BUCKET",
        "S3_PUBLIC_BASE_URL",
    )
    missing = [name for name in required if not getattr(settings, name)]
    if missing:
        errors.append(_error("E006", f"Storage settings missing: {', '.join(missing)}."))
    if settings.S3_PUBLIC_BUCKET and settings.S3_PUBLIC_BUCKET == settings.S3_PRIVATE_BUCKET:
        errors.append(_error("E006", "The public and private buckets must be different."))
    for name in ("S3_ENDPOINT_URL", "S3_PUBLIC_BASE_URL", "S3_BROWSER_ENDPOINT_URL"):
        value = getattr(settings, name)
        if not value:
            continue
        parts = urlsplit(value)
        if parts.scheme != "https" or (parts.hostname or "") in LOCAL_HOSTS:
            errors.append(_error("E006", f"{name} must be an https address, not a local emulator."))
    return errors


def _email_errors():
    if settings.EMAIL_BACKEND not in UNSAFE_EMAIL:
        return []
    if settings.EMAIL_PROVIDER == "console" and preview_active():
        return [
            _warning(
                "W007",
                "Preview mode: email is not sent. Each message is a line in the log (subject "
                "only); manage.py show_email_link gives staff a sign-in link when one is needed.",
                "Set EMAIL_PROVIDER to a real provider, then remove PREVIEW_MODE.",
            )
        ]
    return [_error("E007", "Email goes to the console or memory, not a real provider.")]


def _transport_errors():
    off = []
    if not getattr(settings, "SECURE_SSL_REDIRECT", False):
        off.append("SECURE_SSL_REDIRECT")
    if not getattr(settings, "SESSION_COOKIE_SECURE", False):
        off.append("SESSION_COOKIE_SECURE")
    if not getattr(settings, "CSRF_COOKIE_SECURE", False):
        off.append("CSRF_COOKIE_SECURE")
    if getattr(settings, "SECURE_HSTS_SECONDS", 0) < ONE_YEAR:
        off.append("SECURE_HSTS_SECONDS")
    if not getattr(settings, "SECURE_CONTENT_TYPE_NOSNIFF", False):
        off.append("SECURE_CONTENT_TYPE_NOSNIFF")
    if not getattr(settings, "SECURE_PROXY_SSL_HEADER", None):
        off.append("SECURE_PROXY_SSL_HEADER")
    if off:
        return [_error("E009", f"Transport security is off: {', '.join(off)}.")]
    return []


@register(Tags.database)
def no_demo_seed(app_configs=None, databases=None, **kwargs):
    if not deployed() or not databases:
        return []
    from .models import SampleRecord, SeedMarker

    errors = []
    try:
        seeded = SeedMarker.objects.exists()
        # Sample content belongs on staging; production must never carry it.
        samples = settings.DJANGO_ENV == "production" and SampleRecord.objects.exists()
    except DatabaseError:
        # Before the first migration there are no tables, and so no seed or samples.
        return []
    if seeded:
        errors.append(
            _error(
                "E010",
                "Demo data (seed_demo or make_feed_member) is in this database. "
                "Restore a clean database.",
            )
        )
    if samples:
        errors.append(
            _error(
                "E014",
                "Sample content (load_staging_samples) is in this database.",
                "Samples belong on staging only. Restore a clean database.",
            )
        )
    return errors


def assert_deploy_safe():
    """Called at process start. Raises with every problem listed if any check fails."""
    if not deployed():
        return
    problems = [
        message
        for message in run_checks(include_deployment_checks=False, databases=["default"])
        if message.id and message.id.startswith("rose.") and message.is_serious()
    ]
    if problems:
        lines = "\n".join(f"  {problem.id}: {problem.msg}" for problem in problems)
        raise ImproperlyConfigured(f"Refusing to start {settings.DJANGO_ENV}:\n{lines}")
    if preview_active():
        logger.warning(STARTUP_WARNING)
