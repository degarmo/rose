"""Who is entitled to what. The single source of truth for paid access.

entitlements(user) is a subset of {"feed", "members_events", "members_education"}:
everything the active tier grants, plus "feed" from a staff grant (Profile.feed_access_granted),
which stays for comped members and volunteers.
"""

from .models import Membership

FEED = "feed"
MEMBERS_EVENTS = "members_events"
MEMBERS_EDUCATION = "members_education"


def active_membership(user):
    """The membership currently giving access. Grace counts as entitled."""
    if not (user and user.is_authenticated and user.is_active):
        return None
    return (
        Membership.objects.filter(user=user, status__in=Membership.ENTITLED)
        .select_related("tier")
        .first()
    )


def entitlements(user):
    if not (user and user.is_authenticated and user.is_active):
        return set()
    granted = set()
    membership = active_membership(user)
    if membership is not None:
        granted |= membership.tier.entitlement_flags
    profile = getattr(user, "profile", None)
    if profile is not None and profile.feed_access_granted:
        granted.add(FEED)
    return granted
