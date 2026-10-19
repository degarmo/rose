"""Rental pipeline: conflict checks, status changes and the private calendar hold.

Every status change writes an audit entry. Confirming can add a private,
never-published placeholder event for the booked time so the calendar shows
the date as taken; declining or cancelling removes it again.
"""

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from apps.core.models import AuditLog, audit
from apps.events.models import Event

from .models import RentalInquiry


class RentalError(Exception):
    """A pipeline action was refused; the message is shown to staff."""


def overlapping_events(start, end, exclude=None):
    """Published events and private holds that overlap [start, end)."""
    events = Event.objects.filter(
        Q(is_published=True) | Q(is_private_hold=True), starts_at__lt=end, ends_at__gt=start
    )
    if exclude is not None:
        events = events.exclude(pk=exclude.pk)
    return events.order_by("starts_at")


def conflicts(inquiry):
    """{"preferred": [events], "alternate": [events]} for the requested dates."""
    found = {"preferred": list(overlapping_events(*inquiry.window(), exclude=inquiry.hold))}
    found["alternate"] = (
        list(overlapping_events(*inquiry.window(inquiry.alternate_date), exclude=inquiry.hold))
        if inquiry.alternate_date
        else []
    )
    return found


def log_action(staff, action, inquiry, reason=""):
    audit(
        AuditLog.Category.RENTALS,
        action,
        staff,
        inquiry.label,
        "rental_inquiry",
        target_ref=str(inquiry.pk),
        reason=reason,
    )


def _remove_hold(inquiry):
    if inquiry.hold_id:
        hold = inquiry.hold
        inquiry.hold = None
        hold.delete()


@transaction.atomic
def change_status(staff, inquiry, status, reason=""):
    """Move an inquiry to a new status, logging who did it."""
    inquiry = RentalInquiry.objects.select_for_update().get(pk=inquiry.pk)
    if status not in RentalInquiry.Status.values:
        raise RentalError("Unknown status.")
    if inquiry.contact_purged_at is not None:
        raise RentalError("This inquiry has passed its retention period and is closed.")
    if status == inquiry.status:
        return inquiry
    previous = inquiry.get_status_display()
    inquiry.status = status
    if status in RentalInquiry.CLOSED:
        inquiry.closed_at = timezone.now()
        _remove_hold(inquiry)
    else:
        inquiry.closed_at = None
        if status != RentalInquiry.Status.CONFIRMED:
            _remove_hold(inquiry)
    inquiry.save()
    log_action(
        staff,
        f"status_{status}",
        inquiry,
        f"{previous} to {inquiry.get_status_display()}. {reason}".strip(),
    )
    return inquiry


@transaction.atomic
def confirm(staff, inquiry, create_hold=False, reason=""):
    """Mark confirmed and, if asked, hold the time on the calendar privately."""
    inquiry = change_status(staff, inquiry, RentalInquiry.Status.CONFIRMED, reason)
    if create_hold and inquiry.hold_id is None:
        start, end = inquiry.window()
        hold = Event(
            title="Private booking",
            slug=f"private-booking-{inquiry.pk}-{slugify(str(inquiry.preferred_date))}",
            summary="A private rental. Not shown on the site.",
            category=Event.Category.SPECIAL,
            audience=Event.Audience.ACCOUNT,
            starts_at=start,
            ends_at=end,
            is_published=False,
            is_private_hold=True,
            waitlist_enabled=False,
        )
        hold.save()
        inquiry.hold = hold
        inquiry.save(update_fields=["hold", "updated_at"])
        log_action(staff, "calendar_hold", inquiry)
    return inquiry


def purge_contact(inquiry, now=None):
    """Keep only the type, the date and the status."""
    inquiry.user = None
    inquiry.contact_name = ""
    inquiry.contact_email = ""
    inquiry.contact_phone = ""
    inquiry.notes = ""
    inquiry.staff_notes = ""
    inquiry.alternate_date = None
    inquiry.start_time = None
    inquiry.duration_hours = None
    inquiry.party_size = None
    inquiry.quoted_amount_cents = None
    inquiry.photoshoot_acknowledged = False
    inquiry.contact_purged_at = now or timezone.now()
    inquiry.save()


def forget_account(user):
    """Account deletion: strip contact details from that person's inquiries."""
    for inquiry in RentalInquiry.objects.filter(user=user, contact_purged_at__isnull=True):
        purge_contact(inquiry)
