from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import ContactMessage


@shared_task
def purge_old_messages():
    """Delete handled messages older than CONTACT_RETENTION_DAYS. Unhandled ones wait for staff."""
    cutoff = timezone.now() - timedelta(days=settings.CONTACT_RETENTION_DAYS)
    deleted, _ = ContactMessage.objects.filter(handled=True, created_at__lt=cutoff).delete()
    return deleted
