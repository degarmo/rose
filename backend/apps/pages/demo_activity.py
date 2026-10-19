"""A year of club life for development and the browser tests, so every screen and every
staff chart has real numbers: about 40 members across the seven tiers with twelve
months of payments, past and upcoming evenings with RSVPs and check-ins, gifts, feed
posts and comments, open and closed reports, and email subscribers.

Deterministic (a fixed random seed) and run once: if the first demo member exists,
nothing happens. Never used in staging or production (seed_demo refuses to run there).
"""

import random
import secrets
from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.donations.models import Donation
from apps.events.models import RSVP, Event
from apps.feed import services as feed_services
from apps.feed.models import FeedComment, FeedPost, Guidelines, Report
from apps.memberships.models import IdCheck, Membership, Payment, Tier
from apps.newsletter.models import Subscriber

FIRST = "crowd01@example.org"
ADJECTIVES = ["amber", "velvet", "quiet", "silver", "late", "warm", "low", "soft", "night", "rose"]
NOUNS = ["lamp", "harbour", "ember", "thread", "orchid", "lantern", "ribbon", "garden"]
# How many of the ~40 members hold each tier.
TIER_MIX = {
    "rose": 9,
    "limited": 8,
    "rose-plus": 6,
    "limited-plus": 6,
    "trial": 5,
    "community": 5,
    "first-fridays": 5,
}
POSTS = [
    "Lovely evening, thank you to the hosts.",
    "The new lamps in the parlor make such a difference.",
    "Notes from the class are up on the board by the door.",
    "Quiet night, good conversation, home by midnight.",
    "Thank you to whoever restocked the tea.",
    "First time volunteering at the door. Everyone was kind.",
]
COMMENTS = ["Agreed!", "Thank you for this.", "See you next week.", "Lovely."]


def _handle(index):
    adjective = ADJECTIVES[index % len(ADJECTIVES)]
    noun = NOUNS[(index // len(ADJECTIVES)) % len(NOUNS)]
    return f"{adjective}_{noun}_{index:02d}"


def _members(rng, now):
    tiers = {tier.slug: tier for tier in Tier.objects.filter(slug__in=TIER_MIX)}
    people = []
    index = 0
    for slug, count in TIER_MIX.items():
        tier = tiers.get(slug)
        if tier is None:
            continue
        for _ in range(count):
            index += 1
            user = User.objects.create_user(
                email=f"crowd{index:02d}@example.org",
                display_name=_handle(index),
                password=secrets.token_urlsafe(16),
            )
            user.mark_email_verified()
            people.append((user, tier, _membership(rng, user, tier, now, index)))
    return people


def _membership(rng, user, tier, now, index):
    """Joined some time in the last year; most still running, a few lapsing or ended.
    Short passes (a free week, a two-week trial) mostly started within their length."""
    if tier.interval == Tier.Interval.ONCE and index % 5:
        started = now - timedelta(days=rng.randint(1, max(1, (tier.duration_days or 7) - 1)))
    else:
        started = now - timedelta(days=rng.randint(3, 360))
    membership = Membership(user=user, tier=tier, created_at=started - timedelta(days=2))
    membership.save()
    IdCheck.objects.create(membership=membership)
    if tier.is_free:
        membership.start_new_period(started)
        if tier.interval == Tier.Interval.ONCE and membership.current_period_end < now:
            membership.end(Membership.Status.EXPIRED, membership.current_period_end)
        else:
            membership.status = Membership.Status.ACTIVE
        membership.save()
        return membership
    if tier.interval == Tier.Interval.ONCE:
        _pay(rng, membership, started)
        membership.start_new_period(started)
        if membership.current_period_end < now:
            membership.end(Membership.Status.EXPIRED, membership.current_period_end)
        else:
            membership.status = Membership.Status.ACTIVE
        membership.save()
        return membership
    # Monthly: a payment every 30 days from the start, so the paid period runs past today.
    # One in eight stopped paying a little while ago (grace, or expired this month).
    paid_until = started
    stopped = index % 8 == 0
    while paid_until <= now:
        if stopped and paid_until > now - timedelta(days=35):
            break
        _pay(rng, membership, paid_until)
        paid_until += timedelta(days=30)
    membership.current_period_start = paid_until - timedelta(days=30)
    membership.current_period_end = paid_until
    if membership.current_period_end > now:
        membership.status = Membership.Status.ACTIVE
    elif now - membership.current_period_end < timedelta(days=7):
        membership.status = Membership.Status.GRACE
        membership.grace_started_at = membership.current_period_end
    else:
        membership.end(Membership.Status.EXPIRED, membership.current_period_end + timedelta(days=7))
    membership.save()
    return membership


def _pay(rng, membership, when):
    method = rng.choice([Payment.Method.CASH, Payment.Method.CARD_IN_PERSON])
    Payment.objects.create(
        membership=membership,
        amount_cents=membership.tier.price_cents,
        method=method,
        created_at=when,
    )


def _gifts(rng, now):
    for months_ago in range(12):
        for gift in range(rng.randint(5, 8)):
            when = now - timedelta(days=months_ago * 30 + gift * 3 + 1)
            Donation.objects.create(
                amount_cents=rng.choice([1000, 2500, 5000, 10000]),
                method=rng.choice([Donation.Method.CASH, Donation.Method.CHECK]),
                created_at=when,
            )


def _evenings(rng, people, now):
    """Ten past Friday socials with check-ins, and RSVPs on what is coming up."""
    attendees = [user for user, _, membership in people if membership.is_entitled] or [
        user for user, _, _ in people
    ]
    for weeks_ago in range(1, 11):
        day = timezone.localdate(now) - timedelta(days=7 * weeks_ago)
        while day.weekday() != 4:
            day -= timedelta(days=1)
        starts = timezone.make_aware(datetime.combine(day, time(21, 0)))
        event, _ = Event.objects.update_or_create(
            slug=f"past-social-{day.isoformat()}",
            defaults={
                "title": "Friday Social",
                "summary": "An unhurried evening of conversation, with hosts on the floor.",
                "category": Event.Category.SOCIAL,
                "starts_at": starts,
                "ends_at": starts + timedelta(hours=4),
                "location_label": "Main floor",
                "capacity": 80,
                "is_published": True,
            },
        )
        for user in rng.sample(attendees, min(len(attendees), rng.randint(8, 18))):
            RSVP.objects.get_or_create(
                event=event,
                user=user,
                defaults={
                    "status": RSVP.Status.GOING,
                    "party_size": 1,
                    "checked_in": rng.random() < 0.8,
                },
            )
    upcoming = Event.objects.published().filter(starts_at__gt=now, audience=Event.Audience.PUBLIC)
    for event in upcoming:
        room = max(0, (event.capacity or 40) - event.going_count())
        for user in rng.sample(attendees, min(len(attendees), room, rng.randint(5, 12))):
            RSVP.objects.get_or_create(
                event=event, user=user, defaults={"status": RSVP.Status.GOING, "party_size": 1}
            )


def _feed(rng, people, now):
    guidelines = Guidelines.current()
    if guidelines is None:
        return [], []
    posters = [user for user, tier, _ in people if tier.grants_feed_access][:15]
    for user in posters:
        user.profile.feed_access_granted = True
        user.profile.save(update_fields=["feed_access_granted", "updated_at"])
        feed_services.join_feed(user, guidelines.version, hide_from_directory=False)
    posts = []
    for months_ago in range(12):
        for n in range(6):
            author = posters[(months_ago * 6 + n) % len(posters)]
            created = now - timedelta(days=months_ago * 30 + n * 4 + 1, hours=n)
            post = FeedPost.objects.create(
                author=author,
                caption=POSTS[(months_ago + n) % len(POSTS)],
                status=FeedPost.Status.PUBLISHED,
                consent_attested_at=created,
                first_published_at=created,
            )
            FeedPost.objects.filter(pk=post.pk).update(created_at=created)
            posts.append(post)
            if n % 2 == 0:
                commenter = posters[(months_ago + n + 3) % len(posters)]
                if commenter != author:
                    comment = FeedComment.objects.create(
                        post=post, author=commenter, body=rng.choice(COMMENTS)
                    )
                    FeedComment.objects.filter(pk=comment.pk).update(
                        created_at=created + timedelta(hours=2)
                    )
    return posters, posts


def _reports(rng, posters, posts, now):
    """Five waiting and six closed, about the older demo posts."""
    for index, post in enumerate(posts[6:17]):
        reporter = posters[(index + 5) % len(posters)]
        if reporter == post.author:
            continue
        report = Report.objects.create(
            reporter=reporter,
            target_type=Report.TargetType.POST,
            post=post,
            reason=rng.choice([Report.Reason.SPAM, Report.Reason.HARASSMENT, Report.Reason.OTHER]),
            details="Demo report." if index % 2 else "",
        )
        if index >= 5:
            status = Report.Status.DISMISSED if index % 2 else Report.Status.RESOLVED
            Report.objects.filter(pk=report.pk).update(
                status=status, resolved_at=now - timedelta(days=index), resolution=status
            )


def _subscribers(now):
    for n in range(1, 31):
        Subscriber.objects.get_or_create(
            email=f"reader{n:02d}@example.net",
            defaults={
                "status": Subscriber.Status.CONFIRMED,
                "confirmed_at": now - timedelta(days=n * 9),
                "created_at": now - timedelta(days=n * 9 + 1),
            },
        )


@transaction.atomic
def seed_activity(now=None):
    """Returns how many demo members were added (0 when it has run before)."""
    if User.objects.filter(email=FIRST).exists():
        return 0
    now = now or timezone.now()
    rng = random.Random(2026)
    people = _members(rng, now)
    _gifts(rng, now)
    _evenings(rng, people, now)
    posters, posts = _feed(rng, people, now)
    if posters:
        _reports(rng, posters, posts, now)
    _subscribers(now)
    return len(people)
