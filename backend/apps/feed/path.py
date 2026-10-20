"""The way into the member community, for Home (/members/home).

feed_path(user) lists what still stands between this account and the feed, in order:
confirm the email, choose a plan that includes the community, have it switched on at the
door, the in-person age check (only while the club has it switched on) and joining. Each
step is "done", "current" (the first one not done, with its next action) or "upcoming".
It reads the same rules the feed itself uses (apps.feed.access), so the list is complete
exactly when the feed opens.

teaser(request) is the preview shown to accounts without the feed. It is built only from
the club's own posts, journal photos and announcement titles: never a member's post,
profile, avatar, display name or any count.
"""

from django.db.models import Prefetch
from django.utils import timezone

from apps.core.consent_images import consent_image_payload
from apps.journal.models import Post as JournalPost
from apps.journal.models import PostImage as JournalImage
from apps.memberships.access import age_check_required, is_age_verified
from apps.memberships.models import Membership

from . import access
from .club import club_post_payload
from .models import Announcement

TEASER_TILES = 9


def _waiting_for(membership):
    """What the door desk still has to do to switch a membership on."""
    if membership.status == Membership.Status.SUSPENDED:
        return "suspended"
    if membership.paid_awaiting_id_check:
        return "id_check"
    return "payment"


def feed_path(user):
    profile = user.profile
    membership = Membership.objects.non_terminal().filter(user=user).select_related("tier").first()
    feed_plan = membership is not None and membership.tier.grants_feed_access
    switched_on = feed_plan and membership.status in Membership.ENTITLED
    # Feed access that comes with the account itself: the team, or a staff grant.
    included = bool(user.is_superuser or user.is_staff or profile.feed_access_granted)
    paused = profile.is_feed_banned or profile.is_feed_suspended()
    at_door = feed_plan and not switched_on

    steps = [
        {"key": "email", "done": user.email_verified},
        {
            "key": "plan",
            "done": feed_plan or included,
            "included": included and not feed_plan,
            # A plan they have that leaves the community out.
            "tier": membership.tier.name if membership is not None and not feed_plan else None,
        },
        {
            "key": "door",
            "done": switched_on or included,
            "included": included and not switched_on,
            "reference_code": membership.reference_code if at_door else None,
            "waiting_for": _waiting_for(membership) if at_door else None,
        },
    ]
    if age_check_required():
        steps.append(
            {
                "key": "age",
                "done": is_age_verified(user),
                # The check was switched on after they had the feed.
                "notice": profile.age_check_notice_at is not None,
            }
        )
    steps.append(
        {
            "key": "join",
            "done": profile.participates_in_feed and not paused,
            "paused": paused,
            "can_join": access.can_join_feed(user),
            # Entitled and waiting only for the age check: the guidelines can be read now.
            "early": access.awaiting_age_check(user),
        }
    )

    current = next((step for step in steps if not step["done"]), None)
    for step in steps:
        done = step.pop("done")
        step["state"] = "done" if done else "current" if step is current else "upcoming"
    return {"steps": steps, "complete": access.can_view_feed(user)}


def _first_image(post, request):
    for image in post.images.all():
        payload = consent_image_payload(image, "image", request)
        if payload:
            return {key: payload[key] for key in ("url", "srcset", "alt", "width", "height")}
    return None


def teaser(request):
    """A grid of the club's latest journal photos and announcement titles, and its latest
    journal post as one card, posted by the club."""
    now = timezone.now()
    posts = list(
        JournalPost.objects.live()
        .select_related("event")
        .prefetch_related(Prefetch("images", queryset=JournalImage.objects.order_by("sort_order")))
        .order_by("-published_at", "-pk")[:TEASER_TILES]
    )
    notes = Announcement.objects.filter(
        is_published=True, starts_at__lte=now, ends_at__gt=now
    ).order_by("-starts_at", "-pk")[:TEASER_TILES]

    tiles = []
    for post in posts:
        image = _first_image(post, request)
        if image:
            tiles.append((post.published_at, {"kind": "photo", "image": image}))
    tiles += [(note.starts_at, {"kind": "note", "title": note.title}) for note in notes]
    tiles.sort(key=lambda row: row[0], reverse=True)

    featured = next((post for post in posts if _first_image(post, request)), None)
    return {
        "tiles": [tile for _, tile in tiles[:TEASER_TILES]],
        "post": club_post_payload(featured, request) if featured else None,
    }
