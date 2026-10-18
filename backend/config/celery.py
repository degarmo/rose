import os

from celery import Celery
from celery.signals import beat_init, worker_init

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@worker_init.connect
@beat_init.connect
def refuse_unsafe_deployments(**kwargs):
    """The worker and beat run the same safety checks as the web process."""
    import django

    django.setup()
    from apps.core.checks import assert_deploy_safe

    assert_deploy_safe()
