from datetime import timedelta

import pytest
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from apps.events.access import can_rsvp

pytestmark = pytest.mark.django_db


@pytest.fixture
def people(make_user):
    return {
        "anonymous": AnonymousUser(),
        "unverified": make_user(verified=False),
        "verified": make_user(),
    }


@pytest.mark.parametrize(
    "audience,person,expected",
    [
        ("public", "anonymous", (False, "login_required")),
        ("public", "unverified", (False, "unverified")),
        ("public", "verified", (True, "ok")),
        ("account", "anonymous", (False, "login_required")),
        ("account", "unverified", (False, "unverified")),
        ("account", "verified", (True, "ok")),
        ("members", "anonymous", (False, "members_only")),
        ("members", "unverified", (False, "members_only")),
        ("members", "verified", (False, "members_only")),
    ],
)
def test_audiences(make_event, people, audience, person, expected):
    event = make_event(audience=audience)
    assert can_rsvp(people[person], event) == expected


def test_unpublished_is_unavailable(make_event, people):
    assert can_rsvp(people["verified"], make_event(is_published=False)) == (False, "unavailable")


@pytest.mark.parametrize("audience", ["public", "account", "members"])
def test_window_not_open_yet(make_event, people, audience):
    event = make_event(audience=audience, rsvp_opens_at=timezone.now() + timedelta(days=1))
    expected = (False, "members_only") if audience == "members" else (False, "not_open_yet")
    assert can_rsvp(people["verified"], event) == expected


@pytest.mark.parametrize("audience", ["public", "account", "members"])
def test_window_closed_by_deadline(make_event, people, audience):
    event = make_event(audience=audience, rsvp_closes_at=timezone.now() - timedelta(minutes=1))
    assert can_rsvp(people["verified"], event) == (False, "closed")


def test_window_closes_when_event_starts_by_default(make_event, people):
    started = make_event(starts_at=timezone.now() - timedelta(minutes=5))
    assert can_rsvp(people["verified"], started) == (False, "closed")


def test_window_open_between_open_and_close(make_event, people):
    event = make_event(
        rsvp_opens_at=timezone.now() - timedelta(hours=1),
        rsvp_closes_at=timezone.now() + timedelta(hours=1),
    )
    assert can_rsvp(people["verified"], event) == (True, "ok")


def test_explicit_now_parameter(make_event, people):
    event = make_event(rsvp_opens_at=timezone.now() + timedelta(days=1))
    later = timezone.now() + timedelta(days=2)
    assert can_rsvp(people["verified"], event, now=later) == (True, "ok")
