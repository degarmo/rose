"""Counting members-only events against a membership's monthly allowance.

Every RSVP change goes through sync(): it counts an RSVP once it is going and gives the
place back when it stops being going. A row holds a count per membership per month and
nothing else, so it never says which events someone went to.
"""

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .access import active_membership, month_of
from .models import MembershipUsage

RETENTION_MONTHS = 13


def _count(event):
    from apps.events.models import Event

    return event.audience == Event.Audience.MEMBERS


@transaction.atomic
def sync(rsvp):
    """Bring the monthly count in line with the RSVP's status. Saves the RSVP's flag."""
    from apps.events.models import RSVP

    going = rsvp.status == RSVP.Status.GOING
    if going and not rsvp.counts_toward_plan and _count(rsvp.event):
        membership = active_membership(rsvp.user)
        if membership is None:
            return
        row, _ = MembershipUsage.objects.select_for_update().get_or_create(
            membership=membership, month=month_of(rsvp.event.starts_at)
        )
        MembershipUsage.objects.filter(pk=row.pk).update(events_used=F("events_used") + 1)
        rsvp.counts_toward_plan = True
        rsvp.save(update_fields=["counts_toward_plan"])
    elif not going and rsvp.counts_toward_plan:
        row = (
            MembershipUsage.objects.select_for_update()
            .filter(
                membership__user=rsvp.user,
                month=month_of(rsvp.event.starts_at),
                events_used__gt=0,
            )
            .order_by("-membership__created_at")
            .first()
        )
        if row is not None:
            MembershipUsage.objects.filter(pk=row.pk).update(events_used=F("events_used") - 1)
        rsvp.counts_toward_plan = False
        rsvp.save(update_fields=["counts_toward_plan"])


def purge_old(now=None):
    """Delete counts for months that ended more than 13 months ago."""
    today = timezone.localtime(now or timezone.now()).date()
    month, year = today.month - RETENTION_MONTHS, today.year
    while month < 1:
        month += 12
        year -= 1
    cutoff = today.replace(year=year, month=month, day=1)
    deleted, _ = MembershipUsage.objects.filter(month__lt=cutoff).delete()
    return deleted
