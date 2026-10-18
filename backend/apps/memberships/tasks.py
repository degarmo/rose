from celery import shared_task

from . import lifecycle


@shared_task
def run_lifecycle():
    return lifecycle.run()


@shared_task
def deliver_sandbox_events(payloads):
    """Deliver sandbox webhooks to the real endpoint, the way a processor would."""
    from .sandbox_delivery import deliver

    return [deliver(payload) for payload in payloads]
