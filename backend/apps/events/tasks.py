from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core import signing
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from apps.core.email import send_neutral_mail, site_link

CANCEL_SALT = "events.rsvp-cancel"

SUBJECTS = {
    "confirmation": "Your plans for {day}",
    "waitlist": "Your waitlist place for {day}",
    "promoted": "A place opened up for {day}",
    "cancellation": "Your plans for {day} are cancelled",
    "reminder": "A reminder for {day}",
}

OPENINGS = {
    "confirmation": "You are on the list.",
    "waitlist": "This evening is full, so you are on the waitlist. "
    "We will email you if a place opens up.",
    "promoted": "A place opened up and it is yours. You are now on the list.",
    "cancellation": "Your RSVP has been cancelled. Thank you for letting us know.",
    "reminder": "A quick reminder that you are on the list.",
}


def make_cancel_token(rsvp):
    return signing.dumps({"r": rsvp.pk}, salt=CANCEL_SALT)


def rsvp_from_cancel_token(token):
    from .models import RSVP

    try:
        data = signing.loads(token, salt=CANCEL_SALT)
    except signing.BadSignature:
        return None
    return RSVP.objects.select_related("event").filter(pk=data.get("r")).first()


def subject_for(kind, event):
    day = timezone.localtime(event.starts_at).strftime("%A")
    return SUBJECTS[kind].format(day=day)


def _clock(moment):
    return moment.strftime("%I:%M %p").lstrip("0")


def when_text(event):
    start = timezone.localtime(event.starts_at)
    end = timezone.localtime(event.ends_at)
    return f"{start:%A, %B} {start.day}, {_clock(start)} to {_clock(end)}"


def build_body(rsvp, kind):
    event = rsvp.event
    lines = [
        f"Hello {rsvp.user.display_name},",
        "",
        OPENINGS[kind],
        "",
        event.title,
        when_text(event),
    ]
    if kind != "cancellation":
        party = "just you" if rsvp.party_size == 1 else f"you and {rsvp.party_size - 1} guest"
        lines += [f"Party: {party}", "", "Please bring a valid photo ID."]
        lines += [
            "",
            "If your plans change, cancel here so someone else can come:",
            site_link(f"/events/cancel#token={make_cancel_token(rsvp)}"),
        ]
    lines += ["", f"Event details: {site_link(f'/events/{event.slug}')}", ""]
    return "\n".join(lines)


@shared_task
def send_rsvp_email(rsvp_id, kind):
    from .models import RSVP

    rsvp = RSVP.objects.select_related("event", "user").filter(pk=rsvp_id).first()
    if rsvp is None:
        return
    send_neutral_mail(subject_for(kind, rsvp.event), build_body(rsvp, kind), to=[rsvp.user.email])


@shared_task
def send_due_reminders():
    """Remind people about events in the next 24 hours, once each.

    People who RSVPed inside that window already have a fresh confirmation.
    """
    from .models import RSVP

    now = timezone.now()
    due = RSVP.objects.select_related("event", "user").filter(
        status=RSVP.Status.GOING,
        reminder_sent_at__isnull=True,
        event__is_published=True,
        event__starts_at__gt=now,
        event__starts_at__lte=now + timedelta(hours=24),
    )
    sent = 0
    for rsvp in due:
        if rsvp.created_at > rsvp.event.starts_at - timedelta(hours=24):
            continue
        send_rsvp_email(rsvp.pk, "reminder")
        rsvp.reminder_sent_at = now
        rsvp.save(update_fields=["reminder_sent_at"])
        sent += 1
    return sent


@shared_task
def purge_expired_rsvps():
    """Delete RSVPs once an event is long over, keeping only aggregate counts."""
    from .models import RSVP, Event

    cutoff = timezone.now() - timedelta(days=settings.RSVP_RETENTION_DAYS)
    purged = 0
    for event in Event.objects.filter(ends_at__lt=cutoff, rsvps_purged_at__isnull=True):
        with transaction.atomic():
            totals = event.rsvps.aggregate(
                going=Sum("party_size", filter=Q(status=RSVP.Status.GOING)),
                checked_in=Sum("party_size", filter=Q(checked_in=True)),
            )
            event.final_going_count = totals["going"] or 0
            event.final_checked_in_count = totals["checked_in"] or 0
            event.rsvps_purged_at = timezone.now()
            event.save(
                update_fields=["final_going_count", "final_checked_in_count", "rsvps_purged_at"]
            )
            event.rsvps.all().delete()
        purged += 1
    return purged
