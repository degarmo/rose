from celery import shared_task

from . import lifecycle, usage


@shared_task
def run_lifecycle():
    return lifecycle.run()


@shared_task
def purge_old_usage():
    """Monthly event counts are kept for 13 months, then deleted."""
    return usage.purge_old()


@shared_task
def deliver_sandbox_events(payloads):
    """Deliver sandbox webhooks to the real endpoint, the way a processor would."""
    from .sandbox_delivery import deliver

    return [deliver(payload) for payload in payloads]


@shared_task
def send_age_check_notices():
    """Email, once, the people who had the member feed before it asked for an ID check
    (memberships migration 0007 stamps them). Someone checked in the meantime is skipped."""
    from django.utils import timezone

    from apps.accounts.models import Profile

    from .emails import send_age_check_notice

    sent = 0
    due = Profile.objects.filter(
        age_check_notice_at__isnull=False,
        age_check_emailed_at__isnull=True,
        user__is_active=True,
    ).select_related("user")
    for profile in due:
        send_age_check_notice(profile.user)
        profile.age_check_emailed_at = timezone.now()
        profile.save(update_fields=["age_check_emailed_at", "updated_at"])
        sent += 1
    return sent
