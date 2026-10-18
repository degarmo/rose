"""Logs never identify a member."""

import json
import logging

import pytest
from django.test import RequestFactory

from apps.core.logging import JsonFormatter, ScrubFilter, scrub_event, scrub_text

pytestmark = pytest.mark.django_db

LEAKY = "\n".join(
    [
        "user velvet.fox@private.example from 203.0.113.9 and 2001:db8:85a3::8a2e:370:7334",
        "code R7K-42Q sessionid=abc123def csrftoken=zzz999",
        "Cookie: sessionid=abc; csrftoken=x",
        "Authorization: Basic dmlld2VyOnNlY3JldA==",
        "token Bearer eyJhbGciOi.payload.sig",
        'typed_name="Jordan Realname" display_name=velvet_fox',
        "GET /api/account/verify-email/?token=SECRET",
        "GET /api/members/u/velvet_fox/",
        "GET /api/membership/me/?ref=R7K-42Q",
        "GET /api/payments/sandbox/signed.token.value/",
        "GET /join/confirming?ref=ABC-DEF",
    ]
)
MUST_GO = [
    "velvet.fox@private.example",
    "203.0.113.9",
    "2001:db8:85a3::8a2e:370:7334",
    "R7K-42Q",
    "abc123def",
    "zzz999",
    "dmlld2VyOnNlY3JldA==",
    "eyJhbGciOi",
    "Jordan Realname",
    "velvet_fox",
    "SECRET",
    "signed.token.value",
    "ABC-DEF",
]


def test_scrub_text_removes_every_identifier():
    cleaned = scrub_text(LEAKY)
    for secret in MUST_GO:
        assert secret not in cleaned, secret
    assert "/api/members/u/[redacted]/" in cleaned
    assert "/api/account/verify-email/?[redacted]" in cleaned


def test_public_paths_keep_their_query():
    assert scrub_text("GET /api/events/?category=social") == "GET /api/events/?category=social"


def record(message, *args, request=None, exc_info=None):
    entry = logging.LogRecord(
        "django.request", logging.WARNING, __file__, 1, message, args, exc_info
    )
    if request is not None:
        entry.request = request
        entry.status_code = 404
    return entry


def test_filter_scrubs_message_args_and_the_requesting_member(make_user):
    user = make_user(display_name="quiet_heron", email="heron@example.org")
    request = RequestFactory().get("/api/members/u/quiet_heron/?x=1")
    request.user = user
    entry = record("Not Found: %s (%s)", request.path, "quiet_heron said hi", request=request)
    assert ScrubFilter().filter(entry) is True
    text = JsonFormatter().format(entry)
    assert "quiet_heron" not in text and "heron@example.org" not in text
    data = json.loads(text)
    assert data["level"] == "WARNING" and data["status"] == 404
    assert entry.request is None  # never serialised


def test_exceptions_are_scrubbed():
    try:
        raise ValueError("bad email someone@private.example from 10.1.2.3")
    except ValueError:
        import sys

        entry = record("failed", exc_info=sys.exc_info())
    ScrubFilter().filter(entry)
    text = JsonFormatter().format(entry)
    assert "someone@private.example" not in text and "10.1.2.3" not in text
    assert "ValueError" in text


def test_configured_handlers_use_the_filter(settings):
    assert settings.LOGGING["handlers"]["stdout"]["filters"] == ["scrub"]
    assert settings.ADMINS == []
    assert "mail_admins" not in json.dumps(settings.LOGGING)


def test_gunicorn_access_log_has_no_address_or_query():
    import runpy
    from pathlib import Path

    config = runpy.run_path(str(Path(__file__).resolve().parent.parent / "gunicorn.conf.py"))
    fmt = config["access_log_format"]
    for leaky in ("%(h)s", "%(r)s", "%(q)s", "%(a)s", "%(f)s", "%(u)s", "{"):
        assert leaky not in fmt
    assert config["logconfig_dict"]["handlers"]["stdout"]["filters"] == ["scrub"]


def test_sentry_event_is_stripped():
    event = {
        "request": {
            "url": "https://site.example/api/members/u/velvet_fox/?ref=R7K-42Q",
            "data": {"password": "x"},
            "cookies": {"sessionid": "abc"},
            "headers": {"Authorization": "Basic x"},
            "query_string": "token=1",
            "env": {"REMOTE_ADDR": "203.0.113.9"},
        },
        "user": {"email": "velvet.fox@private.example", "ip_address": "203.0.113.9"},
        "server_name": "web-1",
        "logentry": {"message": "Login failed for velvet.fox@private.example", "params": ["x"]},
        "exception": {
            "values": [
                {
                    "value": "no row for R7K-42Q",
                    "stacktrace": {"frames": [{"vars": {"password": "hunter22"}}]},
                }
            ]
        },
        "breadcrumbs": {"values": [{"message": "GET /account?x=1", "data": {"ip": "1.2.3.4"}}]},
    }
    cleaned = json.dumps(scrub_event(event))
    for secret in ("velvet_fox", "R7K-42Q", "abc", "Basic x", "203.0.113.9", "hunter22", "1.2.3.4"):
        assert secret not in cleaned, secret
    assert "user" not in event and "data" not in event["request"]


def test_sentry_is_off_unless_configured(settings):
    import sentry_sdk

    assert settings.SENTRY_DSN == ""
    assert sentry_sdk.get_client().is_active() is False
