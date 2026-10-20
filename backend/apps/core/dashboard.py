"""The admin home page (Unfold's DASHBOARD_CALLBACK): the only dashboard.

Every number comes from apps.core.metrics, which withholds small ones; nothing here counts.
Who sees what (docs/ops/metrics.md):

- The Admin and Staff roles (superusers count as admins): everything, with the range
  switch, the charts, the tables, the export and the age verification card.
- Everyone else on the team sees only what is waiting for them: open reports and posts
  awaiting approval (moderators, and anyone who can use the moderation queue), and ID
  checks needed (moderators, and anyone who can use the door desk). No revenue and no
  membership figures.
"""

import json
from dataclasses import dataclass
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from apps.core import metrics
from apps.core.email import site_link
from apps.safety import roles

RANGES = [("30d", "30 days"), ("90d", "90 days"), ("12m", "12 months")]
STAFF_DOOR = "/members/staff/door"


@dataclass
class Kpi:
    label: str
    metric: dict
    icon: str
    url: str = ""


def sees_everything(user):
    return roles.has_role(user, roles.STAFF)


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


def _series_charts(points):
    labels = [point["label"] for point in points]

    def values(key, money=False):
        if money:
            return [
                None if p[key]["cents"] is None else round(p[key]["cents"] / 100) for p in points
            ]
        return [p[key]["value"] for p in points]

    return [
        ("Revenue ($)", _chart(labels, "Revenue ($)", values("revenue", money=True))),
        ("Payments", _chart(labels, "Payments", values("payments"))),
        ("RSVPs", _chart(labels, "RSVPs", values("rsvps"))),
        ("Feed posts", _chart(labels, "Feed posts", values("posts"))),
    ]


def _waiting_cards(user, full):
    """What is waiting for staff: the same counts as the sidebar's badges."""
    from apps.feed.admin import QUEUE_PERMISSION
    from apps.memberships.desk import DESK_PERMISSION

    team = full or roles.has_role(user, roles.MODERATOR)
    queue = user.has_perm(QUEUE_PERMISSION)
    cards = []
    if team or queue:
        reports = reverse("admin:feed_moderation") if queue else site_link("/members/staff/reports")
        cards.append(Kpi("Open reports", metrics.open_reports(), "flag", reports))
        cards.append(
            Kpi(
                "Posts awaiting approval",
                metrics.posts_awaiting_approval(),
                "images",
                reverse("admin:feed_moderation") if queue else "",
            )
        )
    if team or user.has_perm(DESK_PERMISSION):
        cards.append(
            Kpi(
                "ID checks needed",
                metrics.id_checks_needed(),
                "badge-check",
                site_link(f"{STAFF_DOOR}?needs_id=1"),
            )
        )
    return cards


def _quick_actions(user):
    from apps.feed.admin import QUEUE_PERMISSION
    from apps.memberships.desk import DESK_PERMISSION

    actions = []
    if user.has_perm("events.add_event"):
        actions.append(("New event", "calendar-days", reverse("admin:events_event_add")))
    if user.has_perm("journal.add_post"):
        actions.append(("New journal post", "newspaper", reverse("admin:journal_post_add")))
    if user.has_perm(DESK_PERMISSION):
        actions.append(("Open door desk", "scan-line", site_link(STAFF_DOOR)))
    if user.has_perm(QUEUE_PERMISSION):
        actions.append(("Open reports", "flag", reverse("admin:feed_moderation")))
    elif roles.has_role(user, roles.MODERATOR):
        actions.append(("Open reports", "flag", site_link("/members/staff/reports")))
    return actions


def _age_check(user):
    from apps.memberships.access import age_check_required
    from apps.memberships.age import can_change_setting

    return {
        "required": age_check_required(),
        "unchecked": metrics.feed_access_without_id_check(),
        "can_change": can_change_setting(user),
        "url": reverse("admin:pages_sitesettings_age_verification"),
    }


def dashboard_callback(request, context):
    user = request.user
    full = sees_everything(user)
    range_key = request.GET.get("range", "30d")
    if range_key not in metrics.RANGES:
        range_key = "30d"
    waiting = _waiting_cards(user, full)
    context.update(
        {
            "small": metrics.SMALL,
            "full": full,
            "waiting": waiting,
            "quick_actions": _quick_actions(user),
        }
    )
    if not full:
        return context
    now = timezone.now()
    data = metrics.dashboard(range_key, now)
    members = data["members"]
    kpis = [
        Kpi(
            "Active members",
            members["total_active"],
            "users-round",
            reverse("admin:memberships_membership_changelist"),
        ),
        Kpi("New this month", members["totals"]["new"], "user-check"),
        Kpi(
            "Revenue this month",
            data["revenue"]["this_month"]["total"],
            "credit-card",
            reverse("admin:memberships_summary"),
        ),
        Kpi(
            "Email list",
            data["email_list"],
            "mail-check",
            reverse("admin:newsletter_subscriber_changelist"),
        ),
        *waiting,
    ]
    tiers = members["tiers"]
    context.update(
        {
            "kpis": kpis,
            "range": range_key,
            "ranges": RANGES,
            "range_label": dict(RANGES)[range_key],
            "series_charts": _series_charts(data["series"]),
            "tier_chart": _chart(
                [row["tier"] for row in tiers],
                "Active members",
                [row["active"]["value"] for row in tiers],
            ),
            "members": members,
            "revenue": data["revenue"],
            "events": data["events"],
            "feed": data["feed"],
            "next_events": [
                {**row, "url": reverse("admin:events_event_change", args=[row["event"].pk])}
                for row in metrics.next_events(now)
            ],
            "since": now - timedelta(days=metrics.RANGES[range_key]),
            "age_check": _age_check(user),
        }
    )
    return context
