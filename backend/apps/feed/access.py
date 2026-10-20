"""Who may see and use the member feed. Every feed view and page calls these.

The entitlement comes from apps.memberships.access.entitlements(): a tier that
grants feed access, the staff grant for comped members and volunteers, a staff
account or a superuser. Whichever it is, nobody gets in without an in-person age
check (age_gate_passes, while the club has the check switched on): no exceptions for
the team.
"""

from django.http import Http404
from django.utils import timezone

from apps.memberships.access import (
    FEED,
    age_gate_passes,
    entitlements,
)

GUIDELINES = "guidelines"
COOLDOWN = "cooldown"


def _profile(user):
    if not (user and user.is_authenticated and user.is_active):
        return None
    return getattr(user, "profile", None)


def has_feed_entitlement(user):
    if _profile(user) is None:
        return False
    return FEED in entitlements(user)


def _entitled_and_in_good_standing(user, now=None):
    profile = _profile(user)
    if profile is None or not user.email_verified:
        return False
    if profile.is_feed_banned or profile.is_feed_suspended(now):
        return False
    return has_feed_entitlement(user)


def can_join_feed(user, now=None):
    """Everything except having opted in: the bar for the join flow."""
    return _entitled_and_in_good_standing(user, now) and age_gate_passes(user)


def awaiting_age_check(user, now=None):
    """Entitled to the feed and in good standing, but nobody has checked their ID yet.

    They see the verify card and may accept the guidelines in advance; the feed itself
    stays a 404 until staff record the check. Never while the check is switched off."""
    return _entitled_and_in_good_standing(user, now) and not age_gate_passes(user)


def can_view_feed(user, now=None):
    profile = _profile(user)
    return bool(profile and profile.participates_in_feed and can_join_feed(user, now))


def has_accepted_current_guidelines(user):
    from .models import Guidelines, GuidelinesAcceptance

    current = Guidelines.current()
    if current is None:
        return True
    return GuidelinesAcceptance.objects.filter(user=user, guidelines=current).exists()


def post_block_reason(user, now=None):
    """Why a feed member cannot post right now, or None."""
    if not has_accepted_current_guidelines(user):
        return GUIDELINES
    cooldown = user.profile.posting_cooldown_until
    if cooldown and cooldown > (now or timezone.now()):
        return COOLDOWN
    return None


def can_post(user, now=None):
    return can_view_feed(user, now) and post_block_reason(user, now) is None


def feed_account_visible(user):
    """Whether /account shows feed controls: entitled now, or has feed data to manage."""
    profile = _profile(user)
    if profile is None:
        return False
    return has_feed_entitlement(user) or profile.joined_feed_at is not None


def require_feed(user):
    """404, never 403, so the feed's existence is not confirmed."""
    if not can_view_feed(user):
        raise Http404


def feed_access_label(user):
    """How staff see someone's feed access: where it stands, never why. None without one."""
    if not has_feed_entitlement(user):
        return None
    granted = user.profile.feed_access_granted
    if not age_gate_passes(user):
        return "Granted, awaiting ID check" if granted else "Awaiting ID check"
    return "Granted" if granted else "Included"
