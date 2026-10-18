"""Entitlements: every membership status, every tier flag, with and without the staff grant."""

import itertools

import pytest
from django.contrib.auth.models import AnonymousUser

from apps.events.access import MEMBERS_ONLY, OK, can_rsvp
from apps.feed import access as feed_access
from apps.memberships.access import (
    FEED,
    MEMBERS_EDUCATION,
    MEMBERS_EVENTS,
    active_membership,
    entitlements,
)
from apps.memberships.models import Membership

pytestmark = pytest.mark.django_db

STATUSES = [value for value, _ in Membership.Status.choices]
FLAGS = {
    "grants_feed_access": FEED,
    "grants_members_events": MEMBERS_EVENTS,
    "grants_members_education": MEMBERS_EDUCATION,
}
FLAG_SETS = [
    dict(zip(FLAGS, values, strict=True))
    for values in itertools.product([False, True], repeat=len(FLAGS))
]


def expected(status, flags, staff_grant):
    granted = set()
    if status in Membership.ENTITLED:
        granted = {FLAGS[name] for name, on in flags.items() if on}
    if staff_grant:
        granted.add(FEED)
    return granted


@pytest.mark.parametrize("staff_grant", [False, True])
@pytest.mark.parametrize(
    "flags", FLAG_SETS, ids=lambda f: "+".join(k[7:] for k, v in f.items() if v) or "none"
)
@pytest.mark.parametrize("status", STATUSES)
def test_entitlement_matrix(
    status, flags, staff_grant, make_user, make_tier, make_membership, make_event
):
    user = make_user()
    if staff_grant:
        user.profile.feed_access_granted = True
        user.profile.save()
    make_membership(user=user, tier=make_tier(**flags), status=status)

    want = expected(status, flags, staff_grant)
    assert entitlements(user) == want
    assert (active_membership(user) is not None) == (status in Membership.ENTITLED)
    assert feed_access.has_feed_entitlement(user) == (FEED in want)

    event = make_event(audience="members")
    allowed, reason = can_rsvp(user, event)
    assert allowed == (MEMBERS_EVENTS in want)
    assert reason == (OK if allowed else MEMBERS_ONLY)


def test_no_membership_means_nothing(make_user):
    assert entitlements(make_user()) == set()
    assert entitlements(AnonymousUser()) == set()
    assert entitlements(None) == set()


def test_inactive_account_loses_everything(make_user, make_membership):
    user = make_user()
    make_membership(user=user)
    user.is_active = False
    user.save()
    assert entitlements(user) == set()


def test_feed_still_needs_opt_in_and_verification(make_user, make_membership):
    user = make_user()
    make_membership(user=user)
    assert feed_access.has_feed_entitlement(user)
    assert not feed_access.can_view_feed(user)  # entitled, but has not joined the feed


def test_members_event_for_anonymous_and_unverified(make_event, make_user, make_membership):
    event = make_event(audience="members")
    assert can_rsvp(AnonymousUser(), event) == (False, MEMBERS_ONLY)
    unverified = make_user(verified=False)
    make_membership(user=unverified)
    assert can_rsvp(unverified, event) == (False, "unverified")


def test_only_one_open_membership_per_person(make_user, make_membership):
    from django.db import IntegrityError, transaction

    user = make_user()
    make_membership(user=user, status="active")
    make_membership(user=user, status="expired")
    with pytest.raises(IntegrityError), transaction.atomic():
        make_membership(user=user, status="pending_payment")
