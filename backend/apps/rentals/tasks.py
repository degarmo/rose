from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from .models import RentalInquiry
from .services import purge_contact


@shared_task
def purge_closed_inquiries():
    """Strip contact details RENTAL_RETENTION_DAYS after an inquiry closed.

    Declined and cancelled inquiries count from when they closed. Inquiries that
    were never concluded (new, in discussion, quoted) count from their last
    requested date, so a forgotten one does not keep someone's details for ever.
    Confirmed bookings are kept as the record of the booking.
    """
    now = timezone.now()
    cutoff = now - timedelta(days=settings.RENTAL_RETENTION_DAYS)
    stale_date = timezone.localdate(cutoff)
    open_statuses = (
        RentalInquiry.Status.NEW,
        RentalInquiry.Status.IN_DISCUSSION,
        RentalInquiry.Status.QUOTED,
    )
    due = RentalInquiry.objects.filter(contact_purged_at__isnull=True).filter(
        Q(status__in=RentalInquiry.CLOSED, closed_at__lt=cutoff)
        | Q(
            status__in=open_statuses,
            preferred_date__lt=stale_date,
        )
        & (Q(alternate_date__isnull=True) | Q(alternate_date__lt=stale_date))
    )
    count = 0
    for inquiry in due:
        purge_contact(inquiry, now)
        count += 1
    return count
