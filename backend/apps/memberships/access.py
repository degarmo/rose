"""Who is entitled to what. The single source of truth for paid access.

entitlements(user) is a subset of {"feed", "members_events", "members_education"}:
everything the active tier grants, plus "feed" from a staff grant (Profile.feed_access_granted),
which stays for comped members and volunteers, and "feed" for every staff account, so the
team can always reach the member app. A superuser holds every entitlement (the owner's
"everything" account), with no membership record behind it.

An entitlement to the feed is not enough to use it: age_gate_passes(user) must be true as
well, whatever the entitlement came from, staff and superusers included (apps.feed.access).
It is true when the club has the age check switched off (SiteSettings), or when the person's
in-person ID check is on file (is_age_verified). Callers use age_gate_passes, never the
setting itself.

The tier rules for members-only events live here too: which events a tier includes, how
many it allows each calendar month, and how many guests come with the member.
"""

from contextlib import contextmanager

from django.core.cache import cache
from django.utils import timezone

from .models import IdCheck, Membership, MembershipUsage, Tier

FEED = "feed"
MEMBERS_EVENTS = "members_events"
MEMBERS_EDUCATION = "members_education"


# Read from the cache for a few seconds at most, and cleared when the setting changes
# (apps.memberships.age.set_age_check_required), so a switch reaches every request, media
# URLs included, almost at once.
AGE_CHECK_CACHE_KEY = "age-check-required"
AGE_CHECK_CACHE_SECONDS = 5


def age_check_required():
    """Whether the club asks for the in-person age check before the member feed opens."""
    required = cache.get(AGE_CHECK_CACHE_KEY)
    if required is None:
        from apps.pages.models import SiteSettings

        required = SiteSettings.load().require_age_verification_for_feed
        cache.set(AGE_CHECK_CACHE_KEY, required, AGE_CHECK_CACHE_SECONDS)
    return required


def age_gate_passes(user):
    """The member feed's age gate: open when the check is switched off, else only to people
    whose ID check is on file."""
    return not age_check_required() or is_age_verified(user)


def is_age_verified(user):
    """Staff saw a valid photo ID showing 18+ for this person, and nobody revoked it."""
    if not (user and user.is_authenticated):
        return False
    return IdCheck.valid().filter(user=user).exists()


def feed_entitled_accounts():
    """Active accounts with feed access from any source, with or without an ID check."""
    from django.db.models import Q

    from apps.accounts.models import User

    feed_members = Membership.objects.filter(
        status__in=Membership.ENTITLED, tier__grants_feed_access=True
    ).values("user_id")
    return (
        User.objects.filter(is_active=True)
        .filter(
            Q(is_superuser=True)
            | Q(is_staff=True)
            | Q(profile__feed_access_granted=True)
            | Q(pk__in=feed_members)
        )
        .distinct()
    )


@contextmanager
def remembered(user):
    """Within the block, this person's membership and monthly use are looked up once, not once
    per event: for lists. Never around a change (an RSVP), which would make them stale."""
    if not (user and user.is_authenticated):
        yield
        return
    user._access_memo = {}
    try:
        yield
    finally:
        del user._access_memo


def _remember(user, key, compute):
    memo = getattr(user, "_access_memo", None)
    if memo is None:
        return compute()
    if key not in memo:
        memo[key] = compute()
    return memo[key]


def active_membership(user):
    """The membership currently giving access. Grace counts as entitled."""
    if not (user and user.is_authenticated and user.is_active):
        return None
    return _remember(user, "membership", lambda: _membership_of(user))


def _membership_of(user):
    membership = (
        Membership.objects.filter(user=user, status__in=Membership.ENTITLED)
        .select_related("tier")
        .prefetch_related("tier__allowed_event_tags")
        .first()
    )
    if membership is not None and hasattr(user, "_access_memo"):
        # Inside remembered(): each month's use is looked up once too (events_used).
        membership._used_by_month = {}
    return membership


ALL = frozenset({FEED, MEMBERS_EVENTS, MEMBERS_EDUCATION})


def entitlements(user):
    if not (user and user.is_authenticated and user.is_active):
        return set()
    if user.is_superuser:
        return set(ALL)
    granted = set()
    membership = active_membership(user)
    if membership is not None:
        granted |= membership.tier.entitlement_flags
    profile = getattr(user, "profile", None)
    if user.is_staff or (profile is not None and profile.feed_access_granted):
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
    memo = getattr(membership, "_used_by_month", None)
    if memo is None:
        return _events_used(membership, month)
    if month not in memo:
        memo[month] = _events_used(membership, month)
    return memo[month]


def _events_used(membership, month):
    row = MembershipUsage.objects.filter(membership=membership, month=month).first()
    return row.events_used if row else 0


def events_remaining(membership, month=None):
    """Members-only events left this month (or in `month`); None means unlimited."""
    limit = membership.tier.events_per_month
    if limit is None:
        return None
    return max(0, limit - events_used(membership, month or month_of(timezone.now())))
