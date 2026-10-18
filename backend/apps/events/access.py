"""Who may RSVP to what."""

from django.utils import timezone

from apps.memberships.access import MEMBERS_EVENTS, entitlements

from .models import Event

OK = "ok"
UNAVAILABLE = "unavailable"
CLOSED = "closed"
MEMBERS_ONLY = "members_only"
NOT_OPEN_YET = "not_open_yet"
LOGIN_REQUIRED = "login_required"
UNVERIFIED = "unverified"


def can_rsvp(user, event, now=None):
    """Return (allowed, reason). Reasons are the constants above."""
    now = now or timezone.now()
    if not event.is_published:
        return False, UNAVAILABLE
    if event.audience == Event.Audience.ACCOUNT and not (user and user.is_authenticated):
        return False, LOGIN_REQUIRED
    if now >= event.rsvp_deadline:
        return False, CLOSED
    if event.audience == Event.Audience.MEMBERS and MEMBERS_EVENTS not in entitlements(user):
        return False, MEMBERS_ONLY
    if event.rsvp_opens_at and now < event.rsvp_opens_at:
        return False, NOT_OPEN_YET
    if not (user and user.is_authenticated):
        return False, LOGIN_REQUIRED
    if not user.email_verified:
        return False, UNVERIFIED
    return True, OK
