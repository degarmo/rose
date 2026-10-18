"""Who may see and use the member feed. Every feed view and page calls these.

Prompt 04 adds paid membership as a second entitlement inside
`has_feed_entitlement`; the staff-granted path stays for comped members and
volunteers. Nothing else changes.
"""

from django.http import Http404
from django.utils import timezone

GUIDELINES = "guidelines"
COOLDOWN = "cooldown"


def _profile(user):
    if not (user and user.is_authenticated and user.is_active):
        return None
    return getattr(user, "profile", None)


def has_feed_entitlement(user):
    profile = _profile(user)
    if profile is None:
        return False
    if profile.feed_access_granted:
        return True
    # Prompt 04: paid membership becomes the second entitlement here.
    return False


def can_join_feed(user, now=None):
    """Everything except having opted in: the bar for the join flow."""
    profile = _profile(user)
    if profile is None or not user.email_verified:
        return False
    if profile.is_feed_banned or profile.is_feed_suspended(now):
        return False
    return has_feed_entitlement(user)


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
