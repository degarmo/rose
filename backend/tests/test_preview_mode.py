"""Staging preview mode: local storage and console email on staging only, said loudly."""

import io
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import CommandError, call_command
from django.test import Client
from django.urls import reverse

from apps.accounts.tokens import user_from_reset_params, user_from_verification_token
from apps.core import checks
from apps.core.email import send_neutral_mail
from apps.core.models import AuditLog, SeedMarker
from apps.core.preview import BANNER, STARTUP_WARNING
from apps.core.private_media import private_media
from tests.conftest import staff_login
from tests.test_deploy_checks import basic

pytestmark = pytest.mark.django_db

BACKEND_DIR = Path(__file__).resolve().parent.parent
LOCAL = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "private": {"BACKEND": "apps.core.private_media.PrivateFileSystemStorage"},
}
# Through the staging password prompt, over HTTPS (the deployed settings redirect plain HTTP).
GATE = {"HTTP_AUTHORIZATION": basic("viewer", "a-long-staging-password"), "secure": True}


@pytest.fixture
def staging_preview(safe_production):
    """Staging in preview mode with local storage and console email; every other check passes."""
    settings = safe_production
    settings.DJANGO_ENV = "staging"
    settings.ALLOWED_HOSTS = ["site.example", "testserver"]
    settings.STAGING_BASIC_AUTH_USER = "viewer"
    settings.STAGING_BASIC_AUTH_PASSWORD = "a-long-staging-password"
    settings.PREVIEW_MODE = True
    settings.STORAGES = {**settings.STORAGES, **LOCAL}
    settings.EMAIL_PROVIDER = "console"
    settings.EMAIL_BACKEND = "apps.core.preview.LogEmailBackend"
    return settings


def found():
    return checks.deployment_settings() + checks.no_demo_seed(databases=["default"])


# The checks


def test_staging_preview_passes_with_only_the_two_warnings(staging_preview, caplog):
    messages = found()
    assert {message.id for message in messages} == {"rose.W006", "rose.W007"}
    assert not any(message.is_serious() for message in messages)
    with caplog.at_level(logging.WARNING, logger="rose.preview"):
        checks.assert_deploy_safe()
    assert STARTUP_WARNING in caplog.messages


def test_manage_check_lets_a_preview_deploy(staging_preview, capsys):
    call_command("check", "--deploy", "--database", "default", "--fail-level", "ERROR")
    out = capsys.readouterr()
    assert "rose.W006" in out.err + out.out and "rose.W007" in out.err + out.out


def test_staging_without_preview_still_refuses_local_storage_and_console_email(staging_preview):
    staging_preview.PREVIEW_MODE = False
    assert {"rose.E006", "rose.E007"} <= {message.id for message in found()}
    with pytest.raises(ImproperlyConfigured):
        checks.assert_deploy_safe()


def test_a_preview_allows_console_email_only(staging_preview):
    staging_preview.EMAIL_PROVIDER = "locmem"
    staging_preview.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    assert "rose.E007" in {message.id for message in found()}


def test_a_preview_with_real_storage_and_email_has_no_warnings(staging_preview, safe_production):
    staging_preview.STORAGES = {
        **staging_preview.STORAGES,
        "default": {"BACKEND": "apps.core.storage.PublicS3Storage"},
        "private": {"BACKEND": "apps.core.storage.PrivateS3Storage"},
    }
    staging_preview.EMAIL_PROVIDER = "postmark"
    staging_preview.EMAIL_BACKEND = "anymail.backends.postmark.EmailBackend"
    assert found() == []


@pytest.mark.parametrize(
    "setting,value,code",
    [
        ("DEBUG", True, "rose.E001"),
        ("PAYMENT_PROVIDERS", ["manual", "sandbox"], "rose.E002"),
        ("SECRET_KEY", "short", "rose.E003"),
        ("ALLOWED_HOSTS", ["*"], "rose.E004"),
        ("CSRF_TRUSTED_ORIGINS", ["http://site.example"], "rose.E005"),
        ("ADMIN_PATH", "admin/", "rose.E008"),
        ("SECURE_SSL_REDIRECT", False, "rose.E009"),
        ("STAGING_BASIC_AUTH_PASSWORD", "", "rose.E011"),
        ("DEV_SKIP_STAFF_2FA", True, "rose.E012"),
    ],
)
def test_a_preview_relaxes_nothing_else(staging_preview, setting, value, code):
    setattr(staging_preview, setting, value)
    serious = {message.id for message in found() if message.is_serious()}
    assert serious == {code}
    with pytest.raises(ImproperlyConfigured):
        checks.assert_deploy_safe()


def test_a_preview_still_refuses_demo_data(staging_preview):
    SeedMarker.objects.create()
    assert "rose.E010" in {message.id for message in found() if message.is_serious()}


def test_production_refuses_preview_mode(safe_production):
    safe_production.PREVIEW_MODE = True
    assert {message.id for message in found()} == {"rose.E013"}
    with pytest.raises(ImproperlyConfigured, match="rose.E013"):
        checks.assert_deploy_safe()


@pytest.mark.parametrize("preview", [False, True])
def test_production_refuses_local_storage_and_console_email_whatever_the_flag(
    safe_production, preview
):
    safe_production.PREVIEW_MODE = preview
    safe_production.STORAGES = {**safe_production.STORAGES, **LOCAL}
    safe_production.EMAIL_PROVIDER = "console"
    safe_production.EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    serious = {message.id for message in found() if message.is_serious()}
    assert {"rose.E006", "rose.E007"} <= serious
    assert ("rose.E013" in serious) is preview
    assert not any(message.id.startswith("rose.W") for message in found())


def load_settings(**environment):
    """Read config.settings in a fresh interpreter with this environment."""
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "config.settings",
        "DJANGO_SECRET_KEY": "x" * 60,
        "PREVIEW_MODE": "false",
        "STORAGE_BACKEND": "local",
        "EMAIL_PROVIDER": "console",
        "CELERY_TASK_ALWAYS_EAGER": "false",
        **environment,
    }
    script = (
        "from django.conf import settings; "
        "print(settings.EMAIL_BACKEND, settings.CELERY_TASK_ALWAYS_EAGER)"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    backend, eager = result.stdout.split()
    return backend, eager == "True"


@pytest.mark.parametrize(
    "environment,backend,eager",
    [
        # Staging preview: email through the scrubbed log, upload tasks in the web process.
        (
            {"DJANGO_ENV": "staging", "PREVIEW_MODE": "true"},
            "apps.core.preview.LogEmailBackend",
            True,
        ),
        # Without the flag, or outside staging, nothing changes (and the checks refuse it).
        ({"DJANGO_ENV": "staging"}, "django.core.mail.backends.console.EmailBackend", False),
        (
            {"DJANGO_ENV": "production", "PREVIEW_MODE": "true"},
            "django.core.mail.backends.console.EmailBackend",
            False,
        ),
        (
            {"DJANGO_ENV": "development", "PREVIEW_MODE": "true"},
            "django.core.mail.backends.console.EmailBackend",
            False,
        ),
    ],
)
def test_the_settings_follow_the_flag_on_staging_only(environment, backend, eager):
    assert load_settings(**environment) == (backend, eager)


# Email


def test_preview_email_is_one_log_line_without_the_address_or_body(staging_preview, caplog):
    with caplog.at_level(logging.INFO, logger="rose.preview"):
        send_neutral_mail(
            "Reset your password",
            "Use this link: https://site.example/account/reset#uid=MQ&token=abc",
            to=["someone@example.org"],
        )
    lines = [record.getMessage() for record in caplog.records if record.name == "rose.preview"]
    assert lines == ["Preview email not sent: 'Reset your password' to 1 recipient(s)"]
    assert "someone@example.org" not in caplog.text and "token=" not in caplog.text


def call_show(*args):
    out = io.StringIO()
    call_command("show_email_link", *args, stdout=out)
    return out.getvalue().strip()


def test_show_email_link_prints_working_links_for_staff(staging_preview, make_user, admin_user):
    member = make_user(email="new@example.org", verified=False)
    link = call_show("new@example.org", "--staff", admin_user.email)
    assert link.startswith("https://site.example/account/verify#token=")
    assert user_from_verification_token(link.split("#token=")[1]) == member

    link = call_show("new@example.org", "--staff", admin_user.email, "--reset")
    params = dict(part.split("=", 1) for part in link.split("#", 1)[1].split("&"))
    assert user_from_reset_params(params["uid"], params["token"]) == member

    entries = AuditLog.objects.filter(action="preview_link_shown")
    assert entries.count() == 2
    assert all(entry.target_user == member and "@" not in entry.target_label for entry in entries)


def test_show_email_link_refuses_outside_a_preview_and_for_non_staff(
    staging_preview, make_user, admin_user
):
    make_user(email="new@example.org", verified=False)
    member = make_user(email="member@example.org")
    with pytest.raises(CommandError, match="staff"):
        call_show("new@example.org", "--staff", member.email)
    with pytest.raises(CommandError, match="already confirmed"):
        call_show("member@example.org", "--staff", admin_user.email)
    staging_preview.PREVIEW_MODE = False
    with pytest.raises(CommandError, match="staging preview"):
        call_show("new@example.org", "--staff", admin_user.email)
    assert not AuditLog.objects.filter(action="preview_link_shown").exists()


# Uploads


def test_public_uploads_are_saved_and_served_locally(staging_preview):
    name = default_storage.save("events/hero.webp", ContentFile(b"RIFF-public"))
    response = Client().get(f"/media/{name}", **GATE)
    assert response.status_code == 200
    assert b"".join(response.streaming_content) == b"RIFF-public"


def test_private_media_still_needs_access(staging_preview, make_member, make_post):
    post = make_post(make_member(display_name="photo_author"), images=1)
    image = post.images.get()
    assert private_media().exists(image.image.name)
    # Not under /media/: a 404, and a path climbing out of it is refused outright.
    assert Client().get(f"/media/{image.image.name}", **GATE).status_code == 404
    assert Client().get(f"/media/../private/{image.image.name}", **GATE).status_code == 400
    url = f"/api/members/media/{image.public_id}/"
    assert Client().get(url, **GATE).status_code == 404
    member = Client()
    member.force_login(make_member())
    assert member.get(url, **GATE).status_code == 200


def test_media_is_not_served_outside_a_preview(settings):
    settings.DEBUG = False
    name = default_storage.save("events/hero.webp", ContentFile(b"RIFF-public"))
    assert Client().get(f"/media/{name}").status_code == 404


# Being visible about it


def staff_page(user, path):
    client = staff_login(Client(), user)
    return client.get(path, **GATE)


def test_the_admin_shows_the_preview_strip_to_staff(staging_preview, admin_user):
    page = staff_page(admin_user, reverse("admin:index")).content.decode()
    assert BANNER in page and "rose-banner-preview" in page


def test_no_strip_without_preview(staging_preview, admin_user):
    staging_preview.PREVIEW_MODE = False
    page = staff_page(admin_user, reverse("admin:index")).content.decode()
    assert BANNER not in page


def test_the_staff_section_is_told(staging_preview, admin_user):
    staff = staff_page(admin_user, "/api/account/session/").json()["user"]["staff"]
    assert staff["preview_mode"] is True
    staging_preview.PREVIEW_MODE = False
    staff = staff_page(admin_user, "/api/account/session/").json()["user"]["staff"]
    assert staff["preview_mode"] is False
