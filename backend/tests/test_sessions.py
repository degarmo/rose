"""Session rules: idle expiry, staff limits, rotation and "Sign out everywhere"."""

import time

import pytest
from django.contrib.auth.models import Group, Permission
from rest_framework.test import APIClient

from apps.accounts.sessions import STAFF_STARTED
from tests.conftest import PASSWORD, csrf_client_for, staff_login

pytestmark = pytest.mark.django_db


def api_login(email):
    client = csrf_client_for()
    response = client.post(
        "/api/account/login/", {"email": email, "password": PASSWORD}, format="json"
    )
    assert response.status_code == 200
    # Login rotates the CSRF token, exactly as the site's client handles it.
    client.credentials(HTTP_X_CSRFTOKEN=response.json()["csrfToken"])
    return client


def session_user(client):
    return client.get("/api/account/session/").json()["user"]


def test_member_sessions_idle_out_after_14_days(make_user, settings):
    make_user(email="m@example.org")
    client = api_login("m@example.org")
    assert settings.SESSION_COOKIE_AGE == 14 * 24 * 60 * 60
    assert settings.SESSION_SAVE_EVERY_REQUEST is True
    cookie = client.cookies[settings.SESSION_COOKIE_NAME]
    assert int(cookie["max-age"]) == settings.SESSION_COOKIE_AGE


def test_login_rotates_the_session_key(make_user, settings):
    make_user(email="m@example.org")
    client = csrf_client_for(APIClient(enforce_csrf_checks=True))
    client.get("/api/account/session/")
    session = client.session
    session["anything"] = 1
    session.save()
    before = client.cookies[settings.SESSION_COOKIE_NAME].value
    client.post(
        "/api/account/login/", {"email": "m@example.org", "password": PASSWORD}, format="json"
    )
    assert client.cookies[settings.SESSION_COOKIE_NAME].value != before


def test_staff_sessions_end_with_the_browser(client, make_user, settings):
    staff = make_user(is_staff=True)
    staff_login(client, staff)
    client.get("/api/account/session/")
    cookie = client.cookies[settings.SESSION_COOKIE_NAME]
    assert cookie["max-age"] == "" and cookie["expires"] == ""  # a browser-session cookie


def test_staff_sessions_end_after_12_hours(client, make_user, settings):
    staff = make_user(is_staff=True)
    staff_login(client, staff)
    client.get("/api/account/session/")
    session = client.session
    session[STAFF_STARTED] = time.time() - settings.STAFF_SESSION_SECONDS - 1
    session.save()
    assert client.get("/api/account/session/").json()["user"] is None


def test_sign_out_everywhere(make_user):
    make_user(email="m@example.org")
    phone, laptop = api_login("m@example.org"), api_login("m@example.org")
    assert session_user(phone) and session_user(laptop)
    response = phone.post("/api/account/sign-out-everywhere/", {}, format="json")
    assert response.status_code == 200
    assert response.json()["user"] is None
    assert session_user(phone) is None
    assert session_user(laptop) is None
    # Signing in again works as normal.
    assert session_user(api_login("m@example.org"))


def test_sign_out_everywhere_needs_a_session(csrf_client):
    assert csrf_client.post("/api/account/sign-out-everywhere/", {}, format="json").status_code in (
        401,
        403,
    )


def test_becoming_staff_ends_existing_sessions(make_user):
    user = make_user(email="m@example.org")
    client = api_login("m@example.org")
    user.is_staff = True
    user.save()
    assert session_user(client) is None


def test_deactivation_and_group_changes_end_sessions(make_user):
    user = make_user(email="m@example.org")
    client = api_login("m@example.org")
    group = Group.objects.create(name="Door desk")
    group.permissions.add(Permission.objects.get(codename="view_membership"))
    user.groups.add(group)
    assert session_user(client) is None

    client = api_login("m@example.org")
    group.user_set.remove(user)
    assert session_user(client) is None


def test_unrelated_saves_keep_sessions(make_user):
    user = make_user(email="m@example.org")
    client = api_login("m@example.org")
    user.display_name = "renamed_person"
    user.save()
    assert session_user(client)["display_name"] == "renamed_person"
