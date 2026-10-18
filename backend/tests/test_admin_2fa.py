"""Staff two-factor: required for every admin view, enrolment forced on first login."""

import re
import time

import pytest
from django.contrib import admin
from django.urls import URLPattern, URLResolver, reverse
from django_otp.oath import totp
from django_otp.plugins.otp_static.models import StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.core.models import AuditLog
from tests.conftest import PASSWORD

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff(django_user_model):
    return django_user_model.objects.create_superuser(
        email="volunteer@example.org", display_name="night_volunteer", password=PASSWORD
    )


def code_for(device, offset=0):
    return (
        f"{totp(device.bin_key, device.step, device.t0, device.digits, device.drift + offset):06d}"
    )


def password_step(client, email="volunteer@example.org", password=PASSWORD):
    return client.post(
        reverse("admin:login"), {"username": email, "password": password, "next": ""}
    )


def admin_paths():
    """Every admin URL, with placeholder arguments."""
    paths = []

    def walk(patterns, prefix):
        for pattern in patterns:
            route = prefix + str(pattern.pattern)
            if isinstance(pattern, URLResolver):
                walk(pattern.url_patterns, route)
            elif isinstance(pattern, URLPattern):
                path = re.sub(r"<(?:int:)?[^>]*(?:object_id|pk|id)[^>]*>", "1", route)
                path = re.sub(r"<path:[^>]+>", "x/y", path)
                path = re.sub(r"<[^>]+>", "x", path).replace("^", "").replace("$", "")
                paths.append("/admin/" + path)

    walk(admin.site.get_urls(), "")
    exempt = ("/admin/login/", "/admin/logout/")
    return sorted({p for p in paths if not p.startswith(exempt) and "(?" not in p})


def test_every_admin_view_needs_the_second_step(client, staff):
    client.force_login(staff)  # password only, as through the site's own login
    paths = admin_paths()
    assert len(paths) > 40
    for path in paths:
        response = client.get(path)
        assert response.status_code == 302, path
        assert response["Location"].startswith("/admin/login/"), path


def test_first_login_forces_enrolment(client, staff, settings):
    # django-otp pauses verification briefly after a wrong code; not needed here.
    settings.OTP_TOTP_THROTTLE_FACTOR = 0
    response = password_step(client)
    assert response["Location"] == reverse("admin:otp_verify")
    assert "_auth_user_id" not in client.session  # not logged in yet
    response = client.get(reverse("admin:otp_verify"))
    assert response["Location"] == reverse("admin:otp_enrol")
    page = client.get(reverse("admin:otp_enrol")).content.decode()
    assert "data:image/svg+xml;base64," in page
    assert "volunteer@example.org" not in page

    device = TOTPDevice.objects.get(user=staff)
    assert not device.confirmed
    assert client.get(reverse("admin:index")).status_code == 302  # still not in

    bad = client.post(reverse("admin:otp_enrol"), {"token": "000000"})
    assert "did not work" in bad.content.decode()

    response = client.post(reverse("admin:otp_enrol"), {"token": code_for(device)})
    assert response["Location"] == reverse("admin:otp_backup_codes")
    codes_page = client.get(reverse("admin:otp_backup_codes")).content.decode()
    codes = re.findall(r"<code>([0-9a-f]{10})</code>", codes_page)
    assert len(codes) == 10
    assert client.get(reverse("admin:otp_backup_codes"))["Location"] == reverse("admin:index")
    assert client.get(reverse("admin:index")).status_code == 200
    assert AuditLog.objects.filter(action="two_factor_enrolled").count() == 1


def test_enrolment_shows_display_name_not_email_to_the_app(client, staff):
    password_step(client)
    client.get(reverse("admin:otp_enrol"))
    from apps.core.admin_auth import _otpauth_url

    url, _ = _otpauth_url(TOTPDevice.objects.get(user=staff), staff)
    assert "night_volunteer" in url and "volunteer" in url and "example.org" not in url


@pytest.fixture
def enrolled(staff):
    device = TOTPDevice.objects.create(user=staff, name="app", confirmed=True)
    from django_otp.plugins.otp_static.models import StaticDevice

    backup = StaticDevice.objects.create(user=staff, name="backup", confirmed=True)
    StaticToken.objects.create(device=backup, token="abcde12345")
    return device


def test_login_with_authenticator_code(client, staff, enrolled):
    password_step(client)
    old_key = client.session.session_key
    response = client.post(reverse("admin:otp_verify"), {"token": code_for(enrolled)})
    assert response["Location"] == reverse("admin:index")
    assert client.session.session_key != old_key  # rotated on login
    assert client.get(reverse("admin:index")).status_code == 200
    assert client.get(reverse("admin:memberships_door_desk")).status_code == 200


def test_backup_code_works_once(client, staff, enrolled, settings):
    settings.OTP_STATIC_THROTTLE_FACTOR = 0
    password_step(client)
    response = client.post(reverse("admin:otp_verify"), {"token": "abcde-12345"})
    assert response["Location"] == reverse("admin:index")
    assert AuditLog.objects.filter(action="backup_code_used").exists()
    client.post(reverse("admin:logout"))
    password_step(client)
    again = client.post(reverse("admin:otp_verify"), {"token": "abcde12345"})
    assert again.status_code == 200 and "did not work" in again.content.decode()


def test_wrong_codes_lock_the_account(client, staff, enrolled, settings):
    settings.OTP_TOTP_THROTTLE_FACTOR = 0
    password_step(client)
    for _ in range(settings.LOGIN_LOCKOUT_ATTEMPTS):
        response = client.post(reverse("admin:otp_verify"), {"token": "123456"})
    assert "Too many attempts" in response.content.decode()
    response = client.post(reverse("admin:otp_verify"), {"token": code_for(enrolled)})
    assert "Too many attempts" in response.content.decode()


def test_wrong_passwords_lock_the_account(client, staff, settings):
    for _ in range(settings.LOGIN_LOCKOUT_ATTEMPTS):
        password_step(client, password="wrong-password-123")
    response = password_step(client)
    assert response.status_code == 200
    assert "Too many attempts" in response.content.decode()


def test_admin_login_is_rate_limited_per_ip(client, staff, settings):
    settings.ADMIN_LOGIN_RATE_LIMIT_IP = "3/h"
    for _ in range(3):
        password_step(client, email="nobody@example.org", password="x")
    assert "Too many attempts" in password_step(client).content.decode()


def test_pending_step_expires(client, staff, enrolled):
    password_step(client)
    session = client.session
    session["admin_pending_at"] = time.time() - 600
    session.save()
    response = client.post(reverse("admin:otp_verify"), {"token": code_for(enrolled)})
    assert response["Location"] == reverse("admin:login")


def test_site_login_then_admin_goes_straight_to_the_code(client, staff, enrolled):
    client.force_login(staff)
    response = client.get(reverse("admin:login"))
    assert response["Location"] == reverse("admin:otp_verify")
    response = client.post(reverse("admin:otp_verify"), {"token": code_for(enrolled)})
    assert client.get(reverse("admin:index")).status_code == 200


def test_members_cannot_use_the_admin_login(client, make_user):
    make_user(email="member@example.org")
    response = password_step(client, email="member@example.org")
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session
