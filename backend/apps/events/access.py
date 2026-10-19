"""Who may RSVP to what."""

from django.utils import timezone

from apps.memberships.access import (
    MEMBERS_EVENTS,
    active_membership,
    entitlements,
    events_remaining,
    month_of,
    party_limit,
    tier_includes_event,
)

from .models import RSVP, Event

OK = "ok"
UNAVAILABLE = "unavailable"
CLOSED = "closed"
MEMBERS_ONLY = "members_only"
NOT_OPEN_YET = "not_open_yet"
LOGIN_REQUIRED = "login_required"
UNVERIFIED = "unverified"
RESTRICTED = "restricted"
TIER_EVENT_NOT_INCLUDED = "tier_event_not_included"
MONTHLY_LIMIT_REACHED = "monthly_limit_reached"
PARTY_SIZE_EXCEEDS_TIER = "party_size_exceeds_tier"

HOLDING = (RSVP.Status.GOING, RSVP.Status.WAITLIST)


def plan_for(user, event):
    """The membership whose tier rules apply to this RSVP, or None.

    Tier rules apply only to members-only events: anyone with a verified account may
    RSVP to the others, so a membership neither limits nor counts towards them.
    """
    if event.audience != Event.Audience.MEMBERS:
        return None
    return active_membership(user)


def plan_party_limit(user, event):
    """The largest party this person's membership allows here, or None if no plan applies."""
    membership = plan_for(user, event)
    return party_limit(membership.tier, event) if membership else None


def plan_events_remaining(user, event):
    """This person's own members-only events left in the event's month (None: unlimited)."""
    membership = plan_for(user, event)
    if membership is None:
        return None
    return events_remaining(membership, month_of(event.starts_at))


def plan_has_room(user, event):
    """False only when this person's membership has no members-only events left that month."""
    membership = plan_for(user, event)
    return membership is None or events_remaining(membership, month_of(event.starts_at)) != 0


def can_rsvp(user, event, now=None, party_size=1, mine=None):
    """Return (allowed, reason). Reasons are the constants above.

    `mine` is this person's existing RSVP, if any. Someone already going or waitlisted
    keeps their place when their month fills up.
    """
    now = now or timezone.now()
    if not event.is_published:
        return False, UNAVAILABLE
    if event.audience == Event.Audience.ACCOUNT and not (user and user.is_authenticated):
        return False, LOGIN_REQUIRED
    if now >= event.rsvp_deadline:
        return False, CLOSED
    if event.audience == Event.Audience.MEMBERS and MEMBERS_EVENTS not in entitlements(user):
        return False, MEMBERS_ONLY
    membership = plan_for(user, event)
    if membership is not None and not tier_includes_event(membership.tier, event):
        return False, TIER_EVENT_NOT_INCLUDED
    if event.rsvp_opens_at and now < event.rsvp_opens_at:
        return False, NOT_OPEN_YET
    if not (user and user.is_authenticated):
        return False, LOGIN_REQUIRED
    if not user.email_verified:
        return False, UNVERIFIED
    profile = getattr(user, "profile", None)
    if profile is not None and (profile.is_events_suspended(now) or profile.do_not_admit_at):
        # An event suspension or a ban (apps/safety): RSVPs are paused.
        return False, RESTRICTED
    if membership is not None:
        holding = mine is not None and mine.status in HOLDING
        if not holding and events_remaining(membership, month_of(event.starts_at)) == 0:
            return False, MONTHLY_LIMIT_REACHED
        if party_size > party_limit(membership.tier, event):
            return False, PARTY_SIZE_EXCEEDS_TIER
    return True, OK
