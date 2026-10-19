from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from .models import VolunteerSignup


@shared_task
def purge_old_signups():
    """Delete signups that went nowhere: inactive, or never contacted, after
    VOLUNTEER_RETENTION_DAYS without any change. Active volunteers are kept."""
    cutoff = timezone.now() - timedelta(days=settings.VOLUNTEER_RETENTION_DAYS)
    deleted, _ = VolunteerSignup.objects.filter(
        Q(status=VolunteerSignup.Status.INACTIVE) | Q(status=VolunteerSignup.Status.NEW),
        updated_at__lt=cutoff,
    ).delete()
    return deleted
