"""Metrics for the admin home page.

Aggregate counts only: nothing here names a person, shows an email or lists who
did what. Each section appears only to staff who may already see the data
behind it (the same permission the matching admin page needs).
"""

from dataclasses import dataclass, field
from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.urls import reverse
from django.utils import timezone


@dataclass
class Stat:
    label: str
    value: str
    hint: str = ""


@dataclass
class Section:
    title: str
    stats: list
    links: list = field(default_factory=list)
    rows: list = field(default_factory=list)


@dataclass
class Attention:
    label: str
    count: int
    url: str


def money(cents):
    sign = "-" if cents < 0 else ""
    return f"{sign}${abs(cents) / 100:,.2f}"


def month_start(moment):
    local = timezone.localtime(moment)
    return local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def build_dashboard(user, now=None):
    """Returns {"attention": [...], "sections": [...]} for this staff member."""
    now = now or timezone.now()
    attention, sections = [], []
    if user.has_perm("memberships.view_membership"):
        sections += membership_sections(now, attention)
    if user.has_perm("events.view_event"):
        sections.append(events_section(user, now))
    if user.has_perm("accounts.view_user"):
        sections.append(accounts_section(now))
    if user.has_perm("feed.view_feedpost"):
        sections.append(feed_section(now, attention))
    if user.has_perm("contact.view_contactmessage"):
        sections.append(messages_section(attention))
    sections.append(images_section(attention))
    if user.is_superuser:
        sections.append(system_section(now, attention))
    return {"attention": [item for item in attention if item.count], "sections": sections}


def membership_sections(now, attention):
    from apps.memberships.models import Membership, Payment

    statuses = dict(Membership.objects.values_list("status").annotate(n=Count("id")))
    awaiting_id = Membership.objects.filter(
        status=Membership.Status.PENDING_PAYMENT, paid_awaiting_id_check=True
    ).count()
    started = month_start(now)
    joined = Membership.objects.filter(created_at__gte=started).count()
    ending = Membership.objects.filter(
        status=Membership.Status.ACTIVE,
        auto_renew=False,
        cancel_at_period_end=False,
        current_period_end__gt=now,
        current_period_end__lte=now + timedelta(days=14),
    ).count()
    entitled = statuses.get("active", 0) + statuses.get("grace", 0)
    attention.append(
        Attention(
            "paid online, waiting for an ID check at the door",
            awaiting_id,
            reverse("admin:memberships_door_desk"),
        )
    )
    members = Section(
        "Membership",
        [
            Stat("Current members", str(entitled), "active or in grace"),
            Stat("In grace", str(statuses.get("grace", 0)), "renewal is due"),
            Stat("Ending within 14 days", str(ending), "not renewing automatically"),
            Stat(
                "Waiting to pay at the door", str(statuses.get("pending_payment", 0) - awaiting_id)
            ),
            Stat("Joined this month", str(joined)),
            Stat("Suspended", str(statuses.get("suspended", 0))),
        ],
        links=[
            ("Door desk", reverse("admin:memberships_door_desk")),
            ("Membership summary", reverse("admin:memberships_summary")),
        ],
    )

    def net(since, until):
        totals = dict(
            Payment.objects.filter(created_at__gte=since, created_at__lt=until)
            .exclude(method=Payment.Method.COMP)
            .values_list("status")
            .annotate(total=Sum("amount_cents"))
        )
        return totals.get("succeeded", 0) - totals.get("refunded", 0)

    previous = month_start(started - timedelta(days=1))
    paid_this_month = (
        Payment.objects.filter(created_at__gte=started, status=Payment.Status.SUCCEEDED)
        .exclude(method=Payment.Method.COMP)
        .count()
    )
    revenue = Section(
        "Income",
        [
            Stat("This month", money(net(started, now + timedelta(seconds=1))), "after refunds"),
            Stat("Last month", money(net(previous, started)), "after refunds"),
            Stat("Payments this month", str(paid_this_month)),
        ],
        links=[("Revenue by month", reverse("admin:memberships_summary"))],
    )
    return [members, revenue]


def events_section(user, now):
    from apps.events.models import RSVP, Event

    upcoming = Event.objects.filter(
        is_published=True, starts_at__gte=now, starts_at__lte=now + timedelta(days=30)
    ).order_by("starts_at")
    stats = [Stat("Events in the next 30 days", str(upcoming.count()))]
    rows = []
    if user.has_perm("events.view_rsvp"):
        totals = RSVP.objects.filter(event__in=upcoming).aggregate(
            going=Sum("party_size", filter=Q(status=RSVP.Status.GOING)),
            waiting=Sum("party_size", filter=Q(status=RSVP.Status.WAITLIST)),
        )
        stats += [
            Stat("People going", str(totals["going"] or 0), "including guests"),
            Stat("On waitlists", str(totals["waiting"] or 0)),
        ]
        for event in upcoming.annotate(
            going=Sum("rsvps__party_size", filter=Q(rsvps__status=RSVP.Status.GOING))
        )[:5]:
            going = event.going or 0
            rows.append(
                {
                    "title": event.title,
                    "when": timezone.localtime(event.starts_at),
                    "going": going,
                    "capacity": event.capacity,
                    "url": reverse("admin:events_event_change", args=[event.pk]),
                }
            )
    return Section(
        "Events",
        stats,
        links=[("All events", reverse("admin:events_event_changelist"))],
        rows=rows,
    )


def accounts_section(now):
    from apps.accounts.models import User

    accounts = User.objects.filter(is_active=True)
    return Section(
        "Accounts",
        [
            Stat("Accounts", str(accounts.count())),
            Stat("Email confirmed", str(accounts.filter(email_verified_at__isnull=False).count())),
            Stat(
                "New in 30 days",
                str(accounts.filter(date_joined__gte=now - timedelta(days=30)).count()),
            ),
        ],
    )


def feed_section(now, attention):
    from apps.accounts.models import Profile
    from apps.feed.models import FeedPost, Report

    open_reports = Report.objects.filter(resolved_at__isnull=True).count()
    pending = FeedPost.objects.filter(status=FeedPost.Status.PENDING).count()
    queue = reverse("admin:feed_moderation")
    attention += [
        Attention("open feed reports", open_reports, queue),
        Attention("first posts waiting for review", pending, queue),
    ]
    stats = [
        Stat("Members in the feed", str(Profile.objects.filter(participates_in_feed=True).count())),
        Stat(
            "Posts in the last 7 days",
            str(FeedPost.objects.filter(created_at__gte=now - timedelta(days=7)).count()),
        ),
        Stat("Open reports", str(open_reports)),
        Stat("Waiting for review", str(pending)),
    ]
    if not settings.FEED_ENABLED:
        stats.insert(0, Stat("Feed", "Switched off", "FEED_ENABLED is false"))
    return Section("Member feed", stats, links=[("Moderation queue", queue)])


def messages_section(attention):
    from apps.contact.models import ContactMessage

    unhandled = ContactMessage.objects.filter(handled=False)
    priority = unhandled.filter(is_priority=True).count()
    changelist = reverse("admin:contact_contactmessage_changelist")
    attention.append(
        Attention(
            "unhandled concerns from the contact form",
            priority,
            f"{changelist}?handled__exact=0&is_priority__exact=1",
        )
    )
    return Section(
        "Messages",
        [
            Stat("Waiting for a reply", str(unhandled.count())),
            Stat("Of which concerns", str(priority)),
        ],
        links=[("Messages", f"{changelist}?handled__exact=0")],
    )


def images_section(attention):
    from .consent_images import consent_image_field_names, consent_image_models
    from .manifest import entry_status, load_manifest

    hidden = sum(1 for entry in load_manifest()["images"] if entry_status(entry) != "shown")
    for model in consent_image_models(include_private=False):
        for name in consent_image_field_names(model):
            faces = {f"{name}_faces_visible": True, f"{name}_consent_confirmed": False}
            hidden += model.objects.exclude(**{name: ""}).filter(**faces).count()
    attention.append(
        Attention("site images hidden for lack of consent", hidden, reverse("admin:image_review"))
    )
    return Section(
        "Images",
        [Stat("Hidden images", str(hidden), "faces without confirmed consent")],
        links=[("Image review", reverse("admin:image_review"))],
    )


def system_section(now, attention):
    from apps.memberships.models import WebhookEvent

    from .models import AuditLog

    failed_webhooks = (
        WebhookEvent.objects.filter(processed_at__isnull=True).exclude(error="").count()
    )
    attention.append(
        Attention(
            "payment events that could not be applied",
            failed_webhooks,
            reverse("admin:memberships_webhookevent_changelist"),
        )
    )
    last_backup = AuditLog.objects.filter(action="backup_created").order_by("-created_at").first()
    if not settings.BACKUP_ENABLED:
        backup = Stat("Last backup", "Off", "BACKUP_ENABLED is false")
    elif last_backup is None:
        backup = Stat("Last backup", "None yet")
    else:
        age = now - last_backup.created_at
        local = timezone.localtime(last_backup.created_at)
        overdue = age > timedelta(hours=26)
        backup = Stat(
            "Last backup", f"{local:%b} {local.day}, {local:%H:%M}", "overdue" if overdue else ""
        )
        if overdue:
            attention.append(
                Attention("nightly backup is overdue", 1, reverse("admin:core_auditlog_changelist"))
            )
    return Section(
        "System",
        [
            Stat("Environment", settings.DJANGO_ENV),
            backup,
            Stat("Payment events not applied", str(failed_webhooks)),
        ],
        links=[("Audit log", reverse("admin:core_auditlog_changelist"))],
    )
