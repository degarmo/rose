"""The admin home page (Unfold's DASHBOARD_CALLBACK).

Aggregates only, with the staff metrics' rules (apps.safety.metrics): counts, never
names, and any number under 5 shown as "fewer than 5". Each card appears only to
staff who may already see the data behind it (the permission its admin page needs).
Charts are drawn in the browser by the Chart.js copy Unfold serves from this site.
"""

import json
from dataclasses import dataclass

from django.urls import reverse
from django.utils import timezone

from apps.safety import metrics


@dataclass
class Kpi:
    label: str
    value: str
    icon: str
    url: str = ""


def shown(metric, key="value"):
    """A count or a sum as it may be shown: "fewer than 5" when withheld."""
    value = metric.get(key)
    if value is None:
        return f"fewer than {metrics.SMALL}"
    if key == "cents":
        return f"${value / 100:,.0f}"
    return f"{value:,}"


def _chart(labels, label, values):
    """Chart.js data for Unfold's bar chart; a withheld value has no bar."""
    return json.dumps(
        {
            "labels": labels,
            "datasets": [
                {
                    "label": label,
                    "data": values,
                    "backgroundColor": "var(--color-primary-600)",
                    "displayYAxis": True,
                    "maxBarThickness": 28,
                }
            ],
        }
    )


def _kpis(user, today):
    from apps.memberships.models import Membership

    cards = []
    if user.has_perm("memberships.view_membership"):
        members = reverse("admin:memberships_membership_changelist")
        section = metrics.membership_section(today)
        cards.append(Kpi("Active members", shown(section["total_active"]), "users-round", members))
        cards.append(Kpi("New this month", shown(metrics.new_members(today)), "user-check"))
    if user.has_perm("memberships.view_payment"):
        cards.append(
            Kpi(
                "Revenue this month",
                shown(metrics.revenue_for(today)["total"], "cents"),
                "credit-card",
                reverse("admin:memberships_summary"),
            )
        )
    if user.has_perm("feed.view_report"):
        cards.append(
            Kpi(
                "Open reports",
                shown(metrics.feed_section(timezone.now(), timezone.now())["open_reports"]),
                "flag",
                reverse("admin:feed_moderation"),
            )
        )
    if user.has_perm("memberships.change_membership"):
        waiting = Membership.objects.filter(
            status=Membership.Status.PENDING_PAYMENT, paid_awaiting_id_check=True
        ).count()
        cards.append(
            Kpi(
                "ID checks needed",
                shown(metrics.count(waiting)),
                "badge-check",
                reverse("admin:memberships_door_desk"),
            )
        )
    return cards


def _revenue_chart(today):
    points = metrics.series("12m", today)
    labels = [point["label"] for point in points]
    values = [
        None if point["revenue"]["cents"] is None else round(point["revenue"]["cents"] / 100)
        for point in points
    ]
    return _chart(labels, "Revenue ($)", values)


def _tier_chart(today):
    rows = metrics.membership_section(today)["tiers"]
    return _chart(
        [row["tier"] for row in rows], "Active members", [row["active"]["value"] for row in rows]
    )


def _next_events(now):
    from django.db.models import Q, Sum

    from apps.events.models import RSVP, Event

    upcoming = (
        Event.objects.published()
        .filter(starts_at__gte=now)
        .annotate(going=Sum("rsvps__party_size", filter=Q(rsvps__status=RSVP.Status.GOING)))
        .order_by("starts_at")[:3]
    )
    return [
        {
            "title": event.title,
            "starts_at": event.starts_at,
            "rsvps": shown(metrics.count(event.going)),
            "url": reverse("admin:events_event_change", args=[event.pk]),
        }
        for event in upcoming
    ]


def _quick_actions(user):
    actions = []
    if user.has_perm("events.add_event"):
        actions.append(("New event", "calendar-days", reverse("admin:events_event_add")))
    if user.has_perm("journal.add_post"):
        actions.append(("New journal post", "newspaper", reverse("admin:journal_post_add")))
    if user.has_perm("memberships.change_membership"):
        actions.append(("Open door desk", "scan-line", reverse("admin:memberships_door_desk")))
    from apps.feed.admin import QUEUE_PERMISSION

    if user.has_perm(QUEUE_PERMISSION):
        actions.append(("Open reports", "flag", reverse("admin:feed_moderation")))
    return actions


def dashboard_callback(request, context):
    user = request.user
    now = timezone.now()
    today = timezone.localdate(now)
    money = user.has_perm("memberships.view_payment")
    members = user.has_perm("memberships.view_membership")
    events = user.has_perm("events.view_event")
    context.update(
        {
            "small": metrics.SMALL,
            "kpis": _kpis(user, today),
            "revenue_chart": _revenue_chart(today) if money else None,
            "tier_chart": _tier_chart(today) if members else None,
            "next_events": _next_events(now) if events else None,
            "quick_actions": _quick_actions(user),
        }
    )
    return context
