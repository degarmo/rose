from celery import shared_task
from django.conf import settings

from . import backups


@shared_task
def nightly_backup():
    """Runs from beat every night when BACKUP_ENABLED is true."""
    if not settings.BACKUP_ENABLED:
        return None
    return backups.run_backup()
