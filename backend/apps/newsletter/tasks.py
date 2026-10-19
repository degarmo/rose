from celery import shared_task
from django.utils import timezone

from . import services
from .models import Newsletter


@shared_task
def send_newsletter(newsletter_pk):
    return services.deliver(newsletter_pk)


@shared_task
def send_scheduled_newsletters():
    """Beat: start any scheduled newsletter whose time has come."""
    due = Newsletter.objects.filter(
        status=Newsletter.Status.SCHEDULED,
        scheduled_at__lte=timezone.now(),
        send_started_at__isnull=True,
    ).values_list("pk", flat=True)
    return [services.deliver(pk) for pk in due]


@shared_task
def purge_subscribers():
    return services.purge()
