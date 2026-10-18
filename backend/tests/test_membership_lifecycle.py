"""The daily lifecycle: grace, expiry, stale codes and neutral reminders."""

from datetime import timedelta

import pytest
from django.core import mail
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.memberships import lifecycle
from apps.memberships.emails import NOTE_SUBJECT
from apps.memberships.models import Membership

pytestmark = pytest.mark.django_db
DAY = timedelta(days=1)


def ending(make_membership, days, **kwargs):
    end = timezone.now() + days * DAY
    return make_membership(current_period_start=end - 30 * DAY, current_period_end=end, **kwargs)


def refreshed(membership):
    membership.refresh_from_db()
    return membership


def test_active_to_grace_to_expired(make_membership):
    membership = ending(make_membership, -0.1)
    lifecycle.run()
    assert refreshed(membership).status == "grace"
    assert [m.subject for m in mail.outbox] == [NOTE_SUBJECT]
    assert "few more days" in mail.outbox[0].body

    lifecycle.run(timezone.now() + 6 * DAY)
    assert refreshed(membership).status == "grace"
    lifecycle.run(timezone.now() + 7 * DAY)
    assert refreshed(membership).status == "expired"
    assert membership.ended_at is not None
    assert [m.subject for m in mail.outbox] == [NOTE_SUBJECT, NOTE_SUBJECT]
    assert "lapsed" in mail.outbox[1].body


def test_grace_days_are_configurable(make_membership, settings):
    settings.MEMBERSHIP_GRACE_DAYS = 2
    membership = ending(make_membership, -0.1, status="active")
    lifecycle.run()
    lifecycle.run(timezone.now() + 2 * DAY)
    assert refreshed(membership).status == "expired"


def test_cancel_at_period_end_becomes_cancelled_without_grace(make_membership):
    membership = ending(make_membership, -0.1, cancel_at_period_end=True)
    lifecycle.run()
    assert refreshed(membership).status == "cancelled"
    assert mail.outbox == []


def test_reminders_at_14_and_3_days_once_each(make_membership):
    membership = ending(make_membership, 20)
    now = timezone.now()
    assert lifecycle.run(now)["reminders"] == 0
    assert lifecycle.run(now + 7 * DAY)["reminders"] == 1  # 13 days left
    assert lifecycle.run(now + 8 * DAY)["reminders"] == 0
    assert lifecycle.run(now + 17.5 * DAY)["reminders"] == 1  # 2.5 days left
    assert lifecycle.run(now + 18 * DAY)["reminders"] == 0
    assert len(mail.outbox) == 2
    assert all(m.subject == NOTE_SUBJECT for m in mail.outbox)
    assert refreshed(membership).reminded_3_at is not None


def test_no_reminders_for_auto_renew_or_cancelling(make_membership, make_user):
    ending(make_membership, 10, auto_renew=True)
    ending(make_membership, 10, cancel_at_period_end=True)
    assert lifecycle.run()["reminders"] == 0


def test_stale_pending_codes_expire(make_membership, settings):
    old = make_membership(status="pending_payment", created_at=timezone.now() - 31 * DAY)
    fresh = make_membership(status="pending_payment", created_at=timezone.now() - 29 * DAY)
    paid = make_membership(
        status="pending_payment", created_at=timezone.now() - 40 * DAY, paid_awaiting_id_check=True
    )
    lifecycle.run()
    assert refreshed(old).status == "expired"
    assert refreshed(fresh).status == "pending_payment"
    assert refreshed(paid).status == "pending_payment"  # paid: waits for the door, never expires


def test_emails_never_name_the_club_or_activities(make_membership):
    for days in (-0.1, 10):
        ending(make_membership, days)
    lifecycle.run()
    lifecycle.run(timezone.now() + 8 * DAY)
    assert mail.outbox
    for message in mail.outbox:
        text = (message.subject + message.body).lower()
        for word in ("bdsm", "kink", "fetish", "dungeon", "play party"):
            assert word not in text


def test_reinstated_after_period_end_moves_on(make_membership, desk_staff):
    from apps.memberships import desk

    membership = ending(make_membership, 5)
    desk.suspend(desk_staff, membership, "pause")
    Membership.objects.filter(pk=membership.pk).update(current_period_end=timezone.now() - DAY)
    desk.reinstate(desk_staff, membership, "back")
    lifecycle.run()
    assert refreshed(membership).status == "grace"


def test_beat_runs_the_lifecycle_daily(settings):
    entry = settings.CELERY_BEAT_SCHEDULE["membership-lifecycle"]
    assert entry["task"] == "apps.memberships.tasks.run_lifecycle"


def test_membership_clock_is_development_only(make_membership, settings):
    with pytest.raises(CommandError):
        call_command("membership_clock", days=10)
    settings.DEBUG = True
    membership = ending(make_membership, 2)
    call_command("membership_clock", days=3)
    assert refreshed(membership).status == "grace"
    call_command("membership_clock", days=8)
    assert refreshed(membership).status == "expired"
