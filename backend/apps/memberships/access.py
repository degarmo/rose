"""Who is entitled to what. The single source of truth for paid access.

entitlements(user) is a subset of {"feed", "members_events", "members_education"}:
everything the active tier grants, plus "feed" from a staff grant (Profile.feed_access_granted),
which stays for comped members and volunteers.

The tier rules for members-only events live here too: which events a tier includes, how
many it allows each calendar month, and how many guests come with the member.
"""

from django.utils import timezone

from .models import Membership, MembershipUsage, Tier

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


def month_of(moment):
    """The first day of the calendar month a moment falls in, Chicago time."""
    return timezone.localtime(moment).date().replace(day=1)


def tier_includes_event(tier, event):
    """Tagged tiers only reach members-only events carrying one of their tags."""
    if tier.event_access == Tier.EventAccess.ALL:
        return True
    allowed = {tag.pk for tag in tier.allowed_event_tags.all()}
    return any(tag.pk in allowed for tag in event.access_tags.all())


def party_limit(tier, event):
    """The member plus their included guests plus any extra guests the event allows."""
    return 1 + tier.guests_included_per_event + event.guest_allowance


def events_used(membership, month):
    row = MembershipUsage.objects.filter(membership=membership, month=month).first()
    return row.events_used if row else 0


def events_remaining(membership, month=None):
    """Members-only events left this month (or in `month`); None means unlimited."""
    limit = membership.tier.events_per_month
    if limit is None:
        return None
    return max(0, limit - events_used(membership, month or month_of(timezone.now())))
