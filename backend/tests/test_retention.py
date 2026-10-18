from datetime import timedelta

import pytest
from django.utils import timezone

from apps.events.models import RSVP, Event
from apps.events.services import submit_rsvp
from apps.events.tasks import purge_expired_rsvps

pytestmark = pytest.mark.django_db


def move_to_past(event, days_ago):
    end = timezone.now() - timedelta(days=days_ago)
    Event.objects.filter(pk=event.pk).update(starts_at=end - timedelta(hours=3), ends_at=end)


def test_purge_keeps_only_counts(make_event, make_user, settings):
    settings.RSVP_RETENTION_DAYS = 30
    old = make_event(capacity=10)
    recent = make_event(capacity=10)
    for event in (old, recent):
        a = submit_rsvp(make_user(), event, 2).rsvp
        submit_rsvp(make_user(), event, 1)
        cancelled = submit_rsvp(make_user(), event, 1).rsvp
        cancelled.status = RSVP.Status.CANCELLED
        cancelled.save()
        a.checked_in = True
        a.save()
    move_to_past(old, 31)
    move_to_past(recent, 29)

    assert purge_expired_rsvps() == 1

    old.refresh_from_db()
    assert old.rsvps.count() == 0
    assert old.final_going_count == 3
    assert old.final_checked_in_count == 2
    assert old.rsvps_purged_at is not None
    assert recent.rsvps.count() == 3

    assert purge_expired_rsvps() == 0


def test_retention_days_configurable(make_event, make_user, settings):
    settings.RSVP_RETENTION_DAYS = 7
    event = make_event()
    submit_rsvp(make_user(), event, 1)
    move_to_past(event, 8)
    assert purge_expired_rsvps() == 1
    assert RSVP.objects.count() == 0


def test_beat_schedule_runs_purge_and_reminders(settings):
    tasks = {entry["task"] for entry in settings.CELERY_BEAT_SCHEDULE.values()}
    assert tasks == {
        "apps.events.tasks.purge_expired_rsvps",
        "apps.events.tasks.send_due_reminders",
    }
