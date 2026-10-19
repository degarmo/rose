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
