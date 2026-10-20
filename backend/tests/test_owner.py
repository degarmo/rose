"""The owner's superuser: Admin everywhere, every entitlement, a ready member profile,
the two-step login (or the development skip), make_owner and demo data to look at."""

import os
from io import StringIO
from unittest import mock
from urllib.parse import urlsplit

import pytest
from django.contrib.auth.models import Group
from django.core.management import CommandError, call_command
from django.urls import reverse
from rest_framework.test import APIClient

from apps.core.checks import deployment_settings
from apps.feed.models import FeedPost
from apps.memberships.access import ALL, entitlements
from apps.memberships.models import Membership
from apps.safety import roles
from tests.conftest import PASSWORD, csrf_client_for, staff_login, verify_age

pytestmark = pytest.mark.django_db

STAFF_PATHS = [
    "/api/staff/overview/",
    "/api/staff/metrics/",
    "/api/staff/team/",
    "/api/staff/reports/",
    "/api/staff/appeals/",
    "/api/staff/members/?q=ow",
]


@pytest.fixture
def owner(django_user_model):
    # As `createsuperuser` makes it: email not confirmed, never joined the member app.
    return django_user_model.objects.create_superuser(
        email="owner@example.org", display_name="the_owner", password=PASSWORD
    )


def login(user):
    client = csrf_client_for(APIClient(enforce_csrf_checks=True))
    response = client.post(
        "/api/account/login/", {"email": user.email, "password": PASSWORD}, format="json"
    )
    assert response.status_code == 200
    return csrf_client_for(client)


def test_a_superuser_is_an_admin_with_every_entitlement_and_no_membership(owner):
    assert roles.role_of(owner) == roles.ADMIN
    assert entitlements(owner) == set(ALL)
    assert not Membership.objects.filter(user=owner).exists()


def test_first_login_prepares_the_account_and_waits_for_the_age_check(owner):
    assert not owner.email_verified and not owner.profile.participates_in_feed
    client = login(owner)
    owner.refresh_from_db()
    assert owner.email_verified
    # No exception for the owner: the feed waits for their own in-person ID check.
    assert not owner.profile.participates_in_feed
    user = client.get("/api/account/session/").json()["user"]
    assert user["member_app"] == "verify" and not user["feed_access"]
    assert client.get("/api/members/me/").status_code == 404


def test_once_checked_the_owner_is_joined_on_the_next_session_check(owner):
    client = login(owner)
    verify_age(owner)
    user = client.get("/api/account/session/").json()["user"]
    assert user["member_app"] == "open" and user["feed_access"]
    profile = owner.profile
    profile.refresh_from_db()
    assert profile.participates_in_feed and profile.joined_feed_at
    assert profile.hide_from_directory and profile.bio == "" and not profile.avatar
    assert not FeedPost.objects.filter(author=owner).exists()
    assert client.get("/api/members/me/").status_code == 200


def test_an_owner_already_signed_in_is_prepared_on_the_next_session_check(owner):
    verify_age(owner)
    client = APIClient()
    client.force_login(owner)
    assert client.get("/api/account/session/").json()["user"]["member_app"] == "open"


def test_the_superuser_reaches_every_section_after_the_two_step_login(owner, client):
    api = APIClient()
    staff_login(api, owner)
    for path in STAFF_PATHS:
        assert api.get(path).status_code == 200, path
    staff_login(client, owner)
    assert client.get(reverse("admin:memberships_door_desk")).status_code == 200
    assert client.get(reverse("admin:index")).status_code == 200


def test_the_superuser_manages_the_team(owner, make_user):
    api = APIClient(enforce_csrf_checks=True)
    staff_login(api, owner)
    api = csrf_client_for(api)
    make_user(display_name="new_admin")
    response = api.post("/api/staff/team/", {"person": "new_admin", "role": "admin"}, format="json")
    assert response.status_code == 200
    assert {
        "display_name": "new_admin",
        "role": "admin",
        "is_superuser": False,
        "is_self": False,
    } in (response.json())


def test_without_an_authenticator_the_session_routes_to_enrolment(owner):
    client = login(owner)
    staff = client.get("/api/account/session/").json()["user"]["staff"]
    assert staff["role"] == "admin" and not staff["verified"] and staff["needs_enrollment"]
    assert staff["admin_url"].endswith(reverse("admin:index"))
    assert staff["door_desk_url"].endswith(reverse("admin:memberships_door_desk"))
    for path in STAFF_PATHS:
        assert client.get(path).status_code == 404
    # The admin's login takes a signed-in, unverified superuser straight to enrolment.
    verify = urlsplit(staff["verify_url"])
    page = client.get(f"{verify.path}?{verify.query}", follow=True)
    assert page.redirect_chain[-1][0] == reverse("admin:otp_enrol")


def test_the_development_skip_works_only_in_development(owner, settings):
    client = login(owner)
    settings.DEV_SKIP_STAFF_2FA = True
    settings.DEBUG = True
    assert client.get("/api/staff/metrics/").status_code == 200
    assert client.get("/api/account/session/").json()["user"]["staff"]["verified"]
    settings.DEBUG = False
    assert client.get("/api/staff/metrics/").status_code == 404
    settings.DEBUG = True
    settings.DJANGO_ENV = "production"
    assert client.get("/api/staff/metrics/").status_code == 404


def test_the_deployment_check_refuses_the_development_skip(settings):
    settings.DJANGO_ENV = "production"
    settings.DEV_SKIP_STAFF_2FA = True
    assert "rose.E012" in {error.id for error in deployment_settings()}
    settings.DEV_SKIP_STAFF_2FA = False
    assert "rose.E012" not in {error.id for error in deployment_settings()}


def test_make_owner_creates_then_does_nothing_new(django_user_model):
    out = StringIO()
    with mock.patch.dict(os.environ, {"DJANGO_SUPERUSER_PASSWORD": "a-long-owner-password-42"}):
        call_command("make_owner", "boss@example.org", stdout=out)
        call_command("make_owner", "boss@example.org", stdout=out)
    user = django_user_model.objects.get(email="boss@example.org")
    assert user.is_superuser and user.is_staff and user.display_name == "boss"
    assert list(user.groups.values_list("name", flat=True)) == ["Admin"]
    assert user.email_verified and not user.profile.participates_in_feed
    text = out.getvalue()
    assert "ID check" in text
    assert "Created boss@example.org" in text and "Upgraded boss@example.org" in text
    assert "authenticator" in text and "DEV_SKIP_STAFF_2FA" in text
    assert django_user_model.objects.filter(email__iexact="boss@example.org").count() == 1


def test_make_owner_upgrades_an_existing_member(make_user):
    member = make_user(email="member@example.org", display_name="a_member")
    call_command("make_owner", "MEMBER@example.org", stdout=StringIO())
    member.refresh_from_db()
    assert member.is_superuser and member.groups.filter(name="Admin").exists()
    assert member.check_password(PASSWORD)  # an existing account keeps its password


def test_make_owner_refuses_a_weak_password():
    with mock.patch.dict(os.environ, {"DJANGO_SUPERUSER_PASSWORD": "short"}):
        with pytest.raises(CommandError):
            call_command("make_owner", "weak@example.org", stdout=StringIO())


def test_the_admin_group_exists():
    assert Group.objects.filter(name="Admin").exists()


def test_a_fresh_seed_demo_fills_the_dashboard(settings):
    from apps.safety import metrics

    settings.DEBUG = True
    call_command("seed_demo", stdout=StringIO())
    data = metrics.dashboard("30d")
    assert data["members"]["total_active"]["value"] >= 30
    assert data["email_list"]["value"] >= 30
    assert data["feed"]["open_reports"]["value"] >= 5
    for key in ("revenue", "payments", "rsvps", "posts"):
        shown = [p[key] for p in data["series"] if (p[key].get("cents") or p[key].get("value"))]
        assert shown, key
    year = metrics.dashboard("12m")
    assert sum(1 for p in year["series"] if p["revenue"]["cents"]) >= 10
    assert any(event["check_ins"] and event["check_ins"]["value"] for event in data["events"])


def test_the_two_step_form_may_return_to_the_site(client, settings):
    """In development the site runs on another origin than the admin; the form's redirect
    back must be allowed (in production both share one origin)."""
    policy = client.get(reverse("admin:login"))["Content-Security-Policy"]
    form_action = next(part for part in policy.split(";") if "form-action" in part)
    assert "'self'" in form_action
    assert settings.FORM_ORIGINS and all(origin in form_action for origin in settings.FORM_ORIGINS)
