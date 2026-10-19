import re

import pytest
from django.core import mail
from rest_framework.test import APIClient

from apps.accounts import tasks
from apps.accounts.models import User
from apps.accounts.tokens import make_reset_params, make_verification_token

from .conftest import PASSWORD, csrf_client_for

pytestmark = pytest.mark.django_db

NEW_ACCOUNT = {"email": "New.Person@example.org", "display_name": "night_owl", "password": PASSWORD}


def post(client, url, data):
    return client.post(f"/api/account/{url}", data, format="json")


def link_token(body, key):
    return re.search(rf"{key}=([^&\s]+)", body).group(1)


# Registration


def test_register_creates_unverified_user_and_sends_link(csrf_client):
    response = post(csrf_client, "register/", NEW_ACCOUNT)
    assert response.status_code == 201
    user = User.objects.get(display_name="night_owl")
    assert user.email == "new.person@example.org"
    assert user.email_verified is False
    assert "_auth_user_id" not in csrf_client.session

    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == tasks.VERIFY_SUBJECT
    assert "https://site.example/account/verify#token=" in mail.outbox[0].body


def test_register_existing_email_gives_same_response_and_warns_owner(csrf_client, member):
    response = post(
        csrf_client, "register/", {**NEW_ACCOUNT, "email": "PRIVATE.person@example.org"}
    )
    assert response.status_code == 201
    assert User.objects.count() == 1
    assert mail.outbox[0].subject == tasks.ALREADY_REGISTERED_SUBJECT
    assert mail.outbox[0].to == [member.email]


def test_register_response_is_identical_for_new_and_existing(csrf_client, member):
    first = post(csrf_client, "register/", NEW_ACCOUNT).json()
    second = post(
        csrf_client,
        "register/",
        {**NEW_ACCOUNT, "email": member.email, "display_name": "other_one"},
    ).json()
    assert first == second


@pytest.mark.parametrize(
    "overrides,field",
    [
        ({"display_name": "velvet_fox"}, "display_name"),
        ({"display_name": "VELVET_FOX"}, "display_name"),
        ({"display_name": "has spaces"}, "display_name"),
        ({"password": "short"}, "password"),
        ({"password": "night_owl99"}, "password"),
        ({"email": "not-an-email"}, "email"),
    ],
)
def test_register_validation(csrf_client, member, overrides, field):
    response = post(csrf_client, "register/", {**NEW_ACCOUNT, **overrides})
    assert response.status_code == 400
    assert field in response.json()


def test_register_requires_csrf():
    assert post(APIClient(enforce_csrf_checks=True), "register/", NEW_ACCOUNT).status_code == 403


def test_register_is_rate_limited_per_email(csrf_client, settings):
    settings.REGISTER_RATE_LIMIT_EMAIL = "2/h"
    statuses = [
        post(csrf_client, "register/", {**NEW_ACCOUNT, "display_name": f"owl_{i}"}).status_code
        for i in range(3)
    ]
    assert statuses == [201, 201, 429]


def test_register_is_rate_limited_per_ip(csrf_client, settings):
    settings.REGISTER_RATE_LIMIT_IP = "2/h"
    statuses = [
        post(
            csrf_client,
            "register/",
            {**NEW_ACCOUNT, "email": f"p{i}@example.org", "display_name": f"owl_{i}"},
        ).status_code
        for i in range(3)
    ]
    assert statuses == [201, 201, 429]


# Verification


def test_verification_link_verifies(csrf_client, make_user):
    user = make_user(verified=False)
    response = post(csrf_client, "verify-email/", {"token": make_verification_token(user)})
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.email_verified


def test_verification_rejects_tampered_and_expired_tokens(csrf_client, make_user, settings):
    user = make_user(verified=False)
    token = make_verification_token(user)
    assert post(csrf_client, "verify-email/", {"token": token + "x"}).status_code == 400
    settings.EMAIL_VERIFICATION_MAX_AGE = -1
    assert post(csrf_client, "verify-email/", {"token": token}).status_code == 400
    user.refresh_from_db()
    assert not user.email_verified


def test_verification_token_dies_if_email_changes(csrf_client, make_user):
    user = make_user(verified=False)
    token = make_verification_token(user)
    user.email = "changed@example.org"
    user.save()
    assert post(csrf_client, "verify-email/", {"token": token}).status_code == 400


def test_resend_verification_for_signed_in_user(signed_in):
    client, user = signed_in(verified=False)
    assert post(client, "verify-email/resend/", {}).status_code == 200
    assert mail.outbox[0].subject == tasks.VERIFY_SUBJECT
    mail.outbox.clear()
    client, _ = signed_in(verified=True)
    post(client, "verify-email/resend/", {})
    assert mail.outbox == []


def test_registration_link_end_to_end(csrf_client):
    post(csrf_client, "register/", NEW_ACCOUNT)
    token = link_token(mail.outbox[0].body, "token")
    assert post(csrf_client, "verify-email/", {"token": token}).status_code == 200
    assert User.objects.get(display_name="night_owl").email_verified


# Login and lockout


def test_login_success_starts_session(csrf_client, make_user):
    user = make_user(email="login@example.org")
    response = post(csrf_client, "login/", {"email": "LOGIN@example.org", "password": PASSWORD})
    assert response.status_code == 200
    body = response.json()
    assert body["user"] == {
        "display_name": user.display_name,
        "email": "login@example.org",
        "email_verified": True,
        "has_membership": False,
        "staff_guide_url": None,
        "feed_access": False,
        "feed_controls": False,
        "member_app": None,
        "staff": None,
        "calendar_details": False,
        "unread_notices": 0,
        "appearance": "light",
    }
    assert body["csrfToken"]
    assert int(csrf_client.session["_auth_user_id"]) == user.pk


def test_login_failure_is_generic(csrf_client, make_user):
    make_user(email="login@example.org")
    wrong = post(csrf_client, "login/", {"email": "login@example.org", "password": "nope-nope"})
    unknown = post(csrf_client, "login/", {"email": "nobody@example.org", "password": "nope"})
    assert wrong.status_code == unknown.status_code == 400
    assert wrong.json() == unknown.json()


def test_lockout_after_five_failures(csrf_client, make_user):
    make_user(email="login@example.org")
    bad = {"email": "login@example.org", "password": "wrong-password"}
    statuses = [post(csrf_client, "login/", bad).status_code for _ in range(5)]
    assert statuses == [400, 400, 400, 400, 429]
    good = post(csrf_client, "login/", {"email": "login@example.org", "password": PASSWORD})
    assert good.status_code == 429
    assert "15 minutes" in good.json()["detail"]


def test_lockout_expires(csrf_client, make_user, settings):
    from django.core.cache import cache

    make_user(email="login@example.org")
    for _ in range(5):
        post(csrf_client, "login/", {"email": "login@example.org", "password": "wrong-pass"})
    cache.clear()
    good = post(csrf_client, "login/", {"email": "login@example.org", "password": PASSWORD})
    assert good.status_code == 200


def test_lockout_uses_15_minute_window(settings):
    assert settings.LOGIN_LOCKOUT_ATTEMPTS == 5
    assert settings.LOGIN_LOCKOUT_SECONDS == 15 * 60


def test_successful_login_resets_failure_count(csrf_client, make_user):
    make_user(email="login@example.org")
    for _ in range(4):
        post(csrf_client, "login/", {"email": "login@example.org", "password": "wrong-pass"})
    good = post(csrf_client, "login/", {"email": "login@example.org", "password": PASSWORD})
    assert good.status_code == 200
    response = post(csrf_client_for(), "login/", {"email": "login@example.org", "password": "x"})
    assert response.status_code == 400


def test_login_rate_limited_per_ip(csrf_client, settings):
    settings.LOGIN_RATE_LIMIT_IP = "3/h"
    statuses = [
        post(csrf_client, "login/", {"email": f"x{i}@example.org", "password": "p"}).status_code
        for i in range(4)
    ]
    assert statuses == [400, 400, 400, 429]


def test_logout_ends_session(signed_in):
    client, _ = signed_in()
    assert post(client, "logout/", {}).status_code == 200
    assert client.get("/api/account/session/").json()["user"] is None


def test_session_endpoint_for_anonymous(api_client):
    body = api_client.get("/api/account/session/").json()
    assert body["user"] is None
    assert body["csrfToken"]


# Password reset and change


def test_password_reset_flow(csrf_client, make_user):
    user = make_user(email="reset@example.org", verified=False)
    response = post(csrf_client, "password-reset/", {"email": "Reset@example.org"})
    assert response.status_code == 200
    assert mail.outbox[0].subject == tasks.RESET_SUBJECT
    body = mail.outbox[0].body
    assert "/account/reset#uid=" in body
    uid, token = link_token(body, "uid"), link_token(body, "token")

    confirm = post(
        csrf_client,
        "password-reset/confirm/",
        {"uid": uid, "token": token, "new_password": "a-brand-new-password-9"},
    )
    assert confirm.status_code == 200
    user.refresh_from_db()
    assert user.check_password("a-brand-new-password-9")
    assert user.email_verified
    assert mail.outbox[-1].subject == tasks.PASSWORD_CHANGED_SUBJECT

    reused = post(
        csrf_client,
        "password-reset/confirm/",
        {"uid": uid, "token": token, "new_password": "another-new-password-9"},
    )
    assert reused.status_code == 400


def test_password_reset_unknown_email_looks_the_same(csrf_client, make_user):
    make_user(email="reset@example.org")
    known = post(csrf_client, "password-reset/", {"email": "reset@example.org"})
    unknown = post(csrf_client, "password-reset/", {"email": "nobody@example.org"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert len(mail.outbox) == 1


def test_password_reset_rejects_weak_password(csrf_client, make_user):
    user = make_user()
    uid, token = make_reset_params(user)
    response = post(
        csrf_client, "password-reset/confirm/", {"uid": uid, "token": token, "new_password": "abc"}
    )
    assert response.status_code == 400
    assert "new_password" in response.json()


def test_password_reset_rate_limited_per_email(csrf_client, settings):
    settings.PASSWORD_RESET_RATE_LIMIT_EMAIL = "2/h"
    statuses = [
        post(csrf_client, "password-reset/", {"email": "a@example.org"}).status_code
        for _ in range(3)
    ]
    assert statuses == [200, 200, 429]


def test_change_password(signed_in):
    client, user = signed_in()
    wrong = post(
        client, "password/", {"current_password": "nope", "new_password": "another-good-pass-1"}
    )
    assert wrong.status_code == 400
    response = post(
        client, "password/", {"current_password": PASSWORD, "new_password": "another-good-pass-1"}
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password("another-good-pass-1")
    assert client.get("/api/account/session/").json()["user"] is not None


def test_change_display_name(signed_in, make_user):
    make_user(display_name="taken_name")
    client, user = signed_in()
    taken = client.patch("/api/account/session/", {"display_name": "Taken_Name"}, format="json")
    assert taken.status_code == 400
    ok = client.patch("/api/account/session/", {"display_name": "new_handle"}, format="json")
    assert ok.status_code == 200
    assert ok.json()["user"]["display_name"] == "new_handle"


def test_change_display_name_requires_login(csrf_client):
    response = csrf_client.patch("/api/account/session/", {"display_name": "x_y_z"}, format="json")
    assert response.status_code == 403


def test_account_routes_need_login(csrf_client):
    assert post(csrf_client, "password/", {}).status_code == 403
    assert post(csrf_client, "delete/", {}).status_code == 403
    assert csrf_client.get("/api/account/rsvps/").status_code == 403


def test_signed_in_post_without_csrf_is_rejected(make_user):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(make_user())
    assert post(client, "logout/", {}).status_code == 403
    assert csrf_client_for(client).post("/api/account/logout/").status_code == 200
