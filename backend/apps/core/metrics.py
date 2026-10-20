"""Every number staff see, in one place: the admin dashboard's cards, charts and tables,
the sidebar badges and the export all call this module, and nothing else counts.
Definitions are in docs/ops/metrics.md.

- No figure names a person or links a person to an event: only counts and sums.
- Suppression happens here, so no caller can skip it. A count from 1 to 4 is withheld
  as "fewer than 5" ("<5" where space is short); zero shows as 0, since it identifies
  nobody. A money total is withheld when it comes from fewer than SMALL payments or
  gifts, since a small total can point to someone.
- Each figure carries its own `display` (the text to show) and `spoken` (the same, for
  screen readers and the tooltip), so every screen shows the same thing for the same number.
- There is no per-member view here, and the export is the same aggregates.
"""

import calendar
import csv
import io
from datetime import datetime, time, timedelta

from django.db.models import Count, Min, Q, Sum
from django.utils import timezone

SMALL = 5
RANGES = {"30d": 30, "90d": 90, "12m": 365}


WITHHELD = f"<{SMALL}"
WITHHELD_LABEL = f"fewer than {SMALL}"


def count(value):
    value = int(value or 0)
    if value == 0 or value >= SMALL:
        return {"value": value, "display": f"{value:,}", "spoken": f"{value:,}"}
    return {"value": None, "fewer_than": SMALL, "display": WITHHELD, "spoken": WITHHELD_LABEL}


def money(cents, payments):
    if (payments or 0) < SMALL:
        return {"cents": None, "fewer_than": SMALL, "display": WITHHELD, "spoken": WITHHELD_LABEL}
    cents = int(cents or 0)
    dollars = f"${cents / 100:,.0f}"
    return {"cents": cents, "display": dollars, "spoken": dollars}


# Things waiting for staff. The same counts feed the dashboard's cards and the sidebar's
# badges.


def open_reports():
    """Reports nobody has closed yet: open, or in review."""
    from apps.feed.models import Report

    return count(
        Report.objects.filter(status__in=[Report.Status.OPEN, Report.Status.IN_REVIEW]).count()
    )


def posts_awaiting_approval():
    """A member's first posts, held for review (processed, not yet approved or removed)."""
    from apps.feed.models import FeedPost

    return count(
        FeedPost.objects.filter(status=FeedPost.Status.PENDING, is_processing=False).count()
    )


def id_checks_needed():
    """Memberships that would be active but for a missing ID check: paid online, a free
    plan, or imported paid-up, all waiting for the door desk."""
    from apps.memberships.models import Membership

    return count(
        Membership.objects.filter(
            status=Membership.Status.PENDING_PAYMENT,
            paid_awaiting_id_check=True,
            user__is_active=True,
        ).count()
    )


def unanswered_messages():
    """Contact form messages not yet marked handled."""
    from apps.contact.models import ContactMessage

    return count(ContactMessage.objects.filter(handled=False).count())


def feed_access_without_id_check():
    """Active accounts with feed access from any source and no valid ID check: who the
    member feed's age check closes it to while it is on."""
    from apps.memberships.access import feed_entitled_accounts
    from apps.memberships.models import IdCheck

    return count(feed_entitled_accounts().exclude(pk__in=IdCheck.valid().values("user_id")).count())


def email_list():
    """Confirmed newsletter subscribers."""
    from apps.newsletter.models import Subscriber

    return count(Subscriber.objects.filter(status=Subscriber.Status.CONFIRMED).count())


def _aware(day):
    return timezone.make_aware(datetime.combine(day, time.min))


def _month_bounds(day):
    first = day.replace(day=1)
    last = calendar.monthrange(day.year, day.month)[1]
    return _aware(first), _aware(first.replace(day=last) + timedelta(days=1))


def _previous_month(day):
    return (day.replace(day=1) - timedelta(days=1)).replace(day=1)


def buckets(range_key, today):
    """(label, start, end) periods for the charts: weeks for 30 and 90 days, months for 12."""
    if range_key == "12m":
        months = []
        first = today.replace(day=1)
        for _ in range(12):
            months.append(first)
            first = _previous_month(first)
        return [(m.strftime("%b %Y"), *_month_bounds(m)) for m in reversed(months)]
    weeks = RANGES[range_key] // 7 + (1 if RANGES[range_key] % 7 else 0)
    end = _aware(today + timedelta(days=1))
    periods = []
    for index in range(weeks):
        stop = end - timedelta(days=7 * index)
        start = stop - timedelta(days=7)
        periods.append((timezone.localtime(start).strftime("%b %-d"), start, stop))
    return list(reversed(periods))


def _tiers():
    """Tiers on offer or still with running members, cheapest first; no guest passes."""
    from apps.memberships.models import Membership, Tier

    running = Q(memberships__status__in=Membership.ENTITLED)
    return (
        Tier.objects.filter(is_guest_pass=False)
        .filter(Q(is_active=True) | running)
        .distinct()
        .order_by("price_cents", "sort_order")
    )


def _month_payments(start, stop):
    """Each membership's first successful payment, and the memberships paid in the month."""
    from apps.memberships.models import Payment

    first_paid = (
        Payment.objects.filter(status=Payment.Status.SUCCEEDED)
        .values("membership")
        .annotate(first=Min("created_at"))
    )
    first_by_membership = {row["membership"]: row["first"] for row in first_paid}
    paid_this_month = set(
        Payment.objects.filter(
            status=Payment.Status.SUCCEEDED, created_at__gte=start, created_at__lt=stop
        ).values_list("membership", flat=True)
    )
    return first_by_membership, paid_this_month


def _new_in(memberships, start, stop, first_by_membership, paid_this_month):
    """New in the month: a first payment in it, or a comp that started in it."""
    from apps.memberships.models import Membership

    return (
        sum(
            1
            for pk in memberships.filter(pk__in=paid_this_month).values_list("pk", flat=True)
            if first_by_membership.get(pk) and first_by_membership[pk] >= start
        )
        + memberships.filter(
            source=Membership.Source.COMP,
            current_period_start__gte=start,
            current_period_start__lt=stop,
        ).count()
    )


def membership_section(today):
    from apps.memberships.models import Membership

    start, stop = _month_bounds(today)
    entitled = Membership.objects.filter(status__in=Membership.ENTITLED)
    first_by_membership, paid_this_month = _month_payments(start, stop)
    rows = []
    totals = {"new": 0, "renewing": 0, "lapsing": 0, "expired": 0}
    for tier in _tiers():
        mine = Membership.objects.filter(tier=tier)
        new = _new_in(mine, start, stop, first_by_membership, paid_this_month)
        renewing = sum(
            1
            for pk in mine.filter(pk__in=paid_this_month).values_list("pk", flat=True)
            if first_by_membership.get(pk) and first_by_membership[pk] < start
        )
        lapsing = mine.filter(
            Q(status=Membership.Status.GRACE)
            | Q(
                status=Membership.Status.ACTIVE,
                auto_renew=False,
                current_period_end__gte=timezone.now(),
                current_period_end__lt=stop,
            )
        ).count()
        expired = mine.filter(
            status=Membership.Status.EXPIRED, ended_at__gte=start, ended_at__lt=stop
        ).count()
        for key, value in (
            ("new", new),
            ("renewing", renewing),
            ("lapsing", lapsing),
            ("expired", expired),
        ):
            totals[key] += value
        rows.append(
            {
                "tier": tier.name,
                "active": count(entitled.filter(tier=tier).count()),
                "new": count(new),
                "renewing": count(renewing),
                "lapsing": count(lapsing),
                "expired": count(expired),
            }
        )
    return {
        "month": today.strftime("%B %Y"),
        "total_active": count(entitled.count()),
        "tiers": rows,
        # Every tier together, counted before suppression (a sum of "fewer than 5"s
        # would be no number at all).
        "totals": {key: count(value) for key, value in totals.items()},
    }


def memberships_by_status():
    """Memberships in each state, guest passes aside."""
    from apps.memberships.models import Membership

    counts = dict(
        Membership.objects.exclude(tier__is_guest_pass=True)
        .values_list("status")
        .annotate(n=Count("pk"))
    )
    return [
        {"status": label, **count(counts.get(value, 0))}
        for value, label in Membership.Status.choices
    ]


def _last_months(today, months):
    """The first day of this month and the months before it, newest first."""
    firsts = [today.replace(day=1)]
    for _ in range(months - 1):
        firsts.append(_previous_month(firsts[-1]))
    return firsts


def revenue_by_method(today, months=12):
    """Membership and guest payments per month and method, refunds subtracted, no comps."""
    from apps.memberships.models import Payment

    methods = [m for m in Payment.Method.values if m != Payment.Method.COMP]
    rows = []
    for first in _last_months(today, months):
        start, stop = _month_bounds(first)
        payments = (
            Payment.objects.filter(created_at__gte=start, created_at__lt=stop)
            .exclude(status=Payment.Status.FAILED)
            .exclude(method=Payment.Method.COMP)
        )
        cells = [
            money(*_net(payments.filter(method=method), Payment.Status.REFUNDED))
            for method in methods
        ]
        rows.append(
            {
                "month": first.strftime("%b %Y"),
                "cells": cells,
                "total": money(*_net(payments, Payment.Status.REFUNDED)),
            }
        )
    return {"methods": [Payment.Method(m).label for m in methods], "rows": rows}


def guest_visits_by_month(today, months=12):
    """Paid guest nights per month."""
    from apps.memberships.models import Payment

    rows = []
    for first in _last_months(today, months):
        start, stop = _month_bounds(first)
        visits = Payment.objects.filter(
            status=Payment.Status.SUCCEEDED,
            membership__tier__is_guest_pass=True,
            created_at__gte=start,
            created_at__lt=stop,
        ).count()
        rows.append({"month": first.strftime("%b %Y"), **count(visits)})
    return rows


def with_event_counts(events):
    """The events, with what event_figures needs counted alongside."""
    from django.db.models.functions import Coalesce

    from apps.events.models import RSVP

    return events.annotate(
        going_n=Coalesce(Sum("rsvps__party_size", filter=Q(rsvps__status=RSVP.Status.GOING)), 0),
        waiting_n=Count("rsvps", filter=Q(rsvps__status=RSVP.Status.WAITLIST)),
        checked_n=Coalesce(Sum("rsvps__party_size", filter=Q(rsvps__checked_in=True)), 0),
    )


def event_figures(event):
    """Going, waitlist and checked in for one event from with_event_counts: the stored final
    counts once its RSVPs are purged. Numbers only, never names."""
    return {
        "event": event,
        "going": count(event.final_going_count if event.rsvps_purged_at else event.going_n),
        "waiting": count(event.waiting_n),
        "checked_in": count(
            event.final_checked_in_count if event.rsvps_purged_at else event.checked_n
        ),
    }


def event_counts(events):
    """Going, waitlist and checked in for each event."""
    return [event_figures(event) for event in with_event_counts(events)]


def next_events(now, limit=3):
    """The next published events, with how many are going."""
    from apps.events.models import Event

    upcoming = Event.objects.published().upcoming(now).order_by("starts_at")[:limit]
    return event_counts(Event.objects.filter(pk__in=[e.pk for e in upcoming]).order_by("starts_at"))


def _net(queryset, refund_status):
    paid = queryset.exclude(status=refund_status).aggregate(
        cents=Sum("amount_cents"), n=Count("pk")
    )
    refunds = queryset.filter(status=refund_status).aggregate(cents=Sum("amount_cents"))
    return (paid["cents"] or 0) - (refunds["cents"] or 0), paid["n"] or 0


def revenue_for(month_day):
    from apps.donations.models import Donation
    from apps.memberships.models import Payment

    start, stop = _month_bounds(month_day)
    payments = (
        Payment.objects.filter(created_at__gte=start, created_at__lt=stop)
        .exclude(status=Payment.Status.FAILED)
        .exclude(method=Payment.Method.COMP)
    )
    rows = []
    for tier in _tiers():
        cents, n = _net(payments.filter(membership__tier=tier), Payment.Status.REFUNDED)
        rows.append({"label": tier.name, **money(cents, n)})
    cents, n = _net(payments.filter(membership__tier__is_guest_pass=True), Payment.Status.REFUNDED)
    rows.append({"label": "Guest passes", **money(cents, n)})
    gifts = Donation.objects.filter(created_at__gte=start, created_at__lt=stop).exclude(
        status=Donation.Status.FAILED
    )
    cents, n = _net(gifts, Donation.Status.REFUNDED)
    rows.append({"label": "Donations", **money(cents, n)})
    total_cents, total_n = _net(payments, Payment.Status.REFUNDED)
    gift_cents, gift_n = _net(gifts, Donation.Status.REFUNDED)
    return {
        "month": month_day.strftime("%B %Y"),
        "rows": rows,
        "total": money(total_cents + gift_cents, total_n + gift_n),
    }


def events_section(since, now):
    """Events from the start of the range to two months ahead, newest first."""
    from apps.events.models import Event, Timing

    events = (
        Event.objects.published()
        .filter(starts_at__gte=since, starts_at__lt=now + timedelta(days=60))
        .order_by("-starts_at")
    )
    return [
        {
            "title": row["event"].title,
            "starts_at": row["event"].starts_at,
            "rsvps": row["going"],
            # Check-ins count once the evening has begun.
            "check_ins": (
                row["checked_in"] if row["event"].timing_at(now) != Timing.UPCOMING else None
            ),
        }
        for row in event_counts(events)
    ]


def feed_section(since, now):
    from apps.feed.models import FeedComment, FeedPost

    published = FeedPost.objects.exclude(status=FeedPost.Status.PENDING)
    return {
        "posts": count(published.filter(created_at__gte=since).count()),
        "comments": count(FeedComment.objects.filter(created_at__gte=since).count()),
        "active_posters_week": count(
            published.filter(created_at__gte=now - timedelta(days=7))
            .values("author")
            .distinct()
            .count()
        ),
        "open_reports": open_reports(),
        "posts_awaiting_approval": posts_awaiting_approval(),
    }


def series(range_key, today):
    from apps.events.models import RSVP
    from apps.feed.models import FeedPost
    from apps.memberships.models import Payment

    points = []
    for label, start, stop in buckets(range_key, today):
        payments = Payment.objects.filter(
            status=Payment.Status.SUCCEEDED, created_at__gte=start, created_at__lt=stop
        ).exclude(method=Payment.Method.COMP)
        paid = payments.aggregate(cents=Sum("amount_cents"), n=Count("pk"))
        points.append(
            {
                "label": label,
                "payments": count(paid["n"]),
                "revenue": money(paid["cents"], paid["n"]),
                "rsvps": count(
                    RSVP.objects.filter(
                        status=RSVP.Status.GOING,
                        event__starts_at__gte=start,
                        event__starts_at__lt=stop,
                    ).aggregate(n=Sum("party_size"))["n"]
                ),
                "posts": count(
                    FeedPost.objects.exclude(status=FeedPost.Status.PENDING)
                    .filter(created_at__gte=start, created_at__lt=stop)
                    .count()
                ),
            }
        )
    return points


def dashboard(range_key, now=None):
    if range_key not in RANGES:
        range_key = "30d"
    now = now or timezone.now()
    today = timezone.localdate(now)
    since = now - timedelta(days=RANGES[range_key])
    return {
        "range": range_key,
        "generated_at": now,
        "small": SMALL,
        "members": membership_section(today),
        "revenue": {
            "this_month": revenue_for(today),
            "last_month": revenue_for(_previous_month(today)),
        },
        "events": events_section(since, now),
        "feed": feed_section(since, now),
        "email_list": email_list(),
        "id_checks_needed": id_checks_needed(),
        "series": series(range_key, today),
    }


def _shown(metric, key="value"):
    if metric is None:
        return ""
    value = metric.get(key)
    return WITHHELD_LABEL if value is None else value


def export_csv(data):
    """The same aggregates as the dashboard, one figure per row."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Section", "Item", "Measure", "Value"])
    members = data["members"]
    writer.writerow(["Members", "All tiers", "Active", _shown(members["total_active"])])
    for row in members["tiers"]:
        for measure in ("active", "new", "renewing", "lapsing", "expired"):
            writer.writerow(["Members", row["tier"], measure.title(), _shown(row[measure])])
    for key in ("this_month", "last_month"):
        block = data["revenue"][key]
        for row in block["rows"]:
            writer.writerow(["Revenue (cents)", row["label"], block["month"], _shown(row, "cents")])
        writer.writerow(
            ["Revenue (cents)", "Total", block["month"], _shown(block["total"], "cents")]
        )
    for row in data["events"]:
        day = timezone.localtime(row["starts_at"]).date().isoformat()
        writer.writerow(["Events", f"{row['title']} ({day})", "RSVPs", _shown(row["rsvps"])])
        if row["check_ins"] is not None:
            writer.writerow(
                ["Events", f"{row['title']} ({day})", "Check-ins", _shown(row["check_ins"])]
            )
    labels = {
        "posts": "Posts",
        "comments": "Comments",
        "active_posters_week": "Active posters this week",
        "open_reports": "Open reports",
        "posts_awaiting_approval": "Posts awaiting approval",
    }
    for key, label in labels.items():
        writer.writerow(["Feed", "", label, _shown(data["feed"][key])])
    writer.writerow(["Email list", "", "Confirmed subscribers", _shown(data["email_list"])])
    writer.writerow(["Door desk", "", "ID checks needed", _shown(data["id_checks_needed"])])
    return out.getvalue()
