"""RSVP capacity rules. Every change locks the event row first.

`select_for_update` on the Event serialises all RSVP writes for one event, so
two people racing for the last place cannot both get it. Every status change
then goes through `usage.sync`, which keeps the member's monthly count right.
"""

from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.memberships import usage

from . import tasks
from .access import (
    MONTHLY_LIMIT_REACHED,
    PARTY_SIZE_EXCEEDS_TIER,
    PAST,
    RESTRICTED,
    TIER_EVENT_NOT_INCLUDED,
    can_rsvp,
    plan_has_room,
)
from .models import RSVP, Event


class RSVPError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class RSVPResult:
    rsvp: RSVP
    outcome: str
    promoted: list = field(default_factory=list)


MESSAGES = {
    PAST: "This event has passed.",
    "party_size": "Choose a party size this event allows.",
    "full": "This event is full.",
    "no_room_for_change": "There is not enough space to change your party size.",
    TIER_EVENT_NOT_INCLUDED: "Your membership does not include this event.",
    MONTHLY_LIMIT_REACHED: "You have used this month's events on your membership.",
    PARTY_SIZE_EXCEEDS_TIER: "Your membership does not include that many guests here.",
    RESTRICTED: "RSVPs are paused on your account. Your notices in Settings explain why.",
}


def _going_total(event, exclude_pk=None):
    rsvps = event.rsvps.filter(status=RSVP.Status.GOING)
    if exclude_pk:
        rsvps = rsvps.exclude(pk=exclude_pk)
    return rsvps.aggregate(total=Sum("party_size"))["total"] or 0


def _fits(event, party_size, exclude_pk=None):
    return event.capacity is None or _going_total(event, exclude_pk) + party_size <= event.capacity


def _promote_waitlist(event):
    """Move waitlisted RSVPs to going, oldest first, skipping any that do not fit.

    A member whose month has filled up since joining the waitlist stays on it.
    """
    promoted = []
    for waiting in (
        event.rsvps.filter(status=RSVP.Status.WAITLIST)
        .select_related("user")
        .order_by("waitlisted_at", "created_at")
    ):
        if not _fits(event, waiting.party_size):
            continue
        if not plan_has_room(waiting.user, event):
            continue
        waiting.status = RSVP.Status.GOING
        waiting.waitlisted_at = None
        waiting.save(update_fields=["status", "waitlisted_at", "updated_at"])
        usage.sync(waiting)
        promoted.append(waiting)
    return promoted


def _email_after_commit(rsvp_ids_by_kind):
    def send():
        for kind, ids in rsvp_ids_by_kind.items():
            for rsvp_id in ids:
                tasks.send_rsvp_email.delay(rsvp_id, kind)

    transaction.on_commit(send)


def submit_rsvp(user, event, party_size, note=""):
    mine = RSVP.objects.filter(event=event, user=user).first()
    allowed, reason = can_rsvp(user, event, party_size=party_size, mine=mine)
    if not allowed:
        raise RSVPError(reason, MESSAGES.get(reason, "RSVPs are not available for this event."))
    if not 1 <= party_size <= event.max_party_size:
        raise RSVPError("party_size", MESSAGES["party_size"])

    with transaction.atomic():
        event = Event.objects.select_for_update().get(pk=event.pk)
        rsvp = RSVP.objects.filter(event=event, user=user).first()

        if rsvp and rsvp.status == RSVP.Status.GOING:
            if not _fits(event, party_size, exclude_pk=rsvp.pk):
                raise RSVPError("no_room_for_change", MESSAGES["no_room_for_change"])
            rsvp.party_size = party_size
            rsvp.note_to_hosts = note
            rsvp.save(update_fields=["party_size", "note_to_hosts", "updated_at"])
            promoted = _promote_waitlist(event)
            _email_after_commit({"promoted": [p.pk for p in promoted]})
            return RSVPResult(rsvp, "updated", promoted)

        if rsvp and rsvp.status == RSVP.Status.WAITLIST:
            rsvp.party_size = party_size
            rsvp.note_to_hosts = note
            rsvp.save(update_fields=["party_size", "note_to_hosts", "updated_at"])
            promoted = _promote_waitlist(event)
            rsvp.refresh_from_db()
            _email_after_commit({"promoted": [p.pk for p in promoted]})
            return RSVPResult(rsvp, "updated", promoted)

        if _fits(event, party_size):
            status, waitlisted_at = RSVP.Status.GOING, None
        elif event.waitlist_enabled:
            status, waitlisted_at = RSVP.Status.WAITLIST, timezone.now()
        else:
            raise RSVPError("full", MESSAGES["full"])

        if rsvp is None:
            rsvp = RSVP(event=event, user=user)
        rsvp.status = status
        rsvp.waitlisted_at = waitlisted_at
        rsvp.party_size = party_size
        rsvp.note_to_hosts = note
        rsvp.checked_in = False
        rsvp.reminder_sent_at = None
        rsvp.save()
        usage.sync(rsvp)

        kind = "confirmation" if status == RSVP.Status.GOING else "waitlist"
        _email_after_commit({kind: [rsvp.pk]})
        return RSVPResult(rsvp, status)


def cancel_rsvp(rsvp, notify_owner=True):
    """Cancel, then hand any freed places to the waitlist."""
    with transaction.atomic():
        event = Event.objects.select_for_update().get(pk=rsvp.event_id)
        rsvp = RSVP.objects.get(pk=rsvp.pk)
        if rsvp.status == RSVP.Status.CANCELLED:
            return RSVPResult(rsvp, "unchanged")
        rsvp.status = RSVP.Status.CANCELLED
        rsvp.waitlisted_at = None
        rsvp.checked_in = False
        rsvp.save(update_fields=["status", "waitlisted_at", "checked_in", "updated_at"])
        usage.sync(rsvp)
        promoted = _promote_waitlist(event)
        _email_after_commit(
            {
                "cancellation": [rsvp.pk] if notify_owner else [],
                "promoted": [p.pk for p in promoted],
            }
        )
        return RSVPResult(rsvp, "cancelled", promoted)


def release_places_held_by(user):
    """Cancel someone's active RSVPs so their places pass to the waitlist."""
    active = RSVP.objects.filter(
        user=user,
        status__in=[RSVP.Status.GOING, RSVP.Status.WAITLIST],
        event__in=Event.objects.not_past(),
    )
    for rsvp in active:
        cancel_rsvp(rsvp, notify_owner=False)
