from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import Acknowledgement, DonationCheckout


@shared_task
def purge_donation_contacts():
    """Forget what is only needed for a short while.

    Online gifts that were started but never finished, and finished ones once
    their gift is recorded, go after DONATION_CHECKOUT_RETENTION_DAYS. An email
    for an acknowledgement that was never sent is cleared after
    DONATION_ACK_EMAIL_RETENTION_DAYS.
    """
    now = timezone.now()
    checkouts, _ = DonationCheckout.objects.filter(
        created_at__lt=now - timedelta(days=settings.DONATION_CHECKOUT_RETENTION_DAYS)
    ).delete()
    emails = 0
    for acknowledgement in Acknowledgement.objects.filter(
        emailed_at__isnull=True,
        created_at__lt=now - timedelta(days=settings.DONATION_ACK_EMAIL_RETENTION_DAYS),
    ).exclude(email=""):
        acknowledgement.email = ""
        acknowledgement.save(update_fields=["email"])
        emails += 1
    return {"checkouts": checkouts, "emails": emails}
