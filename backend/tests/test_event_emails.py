import re
from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from apps.accounts import tasks as account_tasks
from apps.contact import notifications
from apps.events.models import RSVP
from apps.events.services import submit_rsvp
from apps.events.tasks import SUBJECTS, send_due_reminders, subject_for

pytestmark = pytest.mark.django_db

# Words that would tell anyone glancing at an inbox what this is about.
REVEALING = re.compile(
    r"club|rose|event|rsvp|social|education|member|night|class|workshop|adult|18", re.I
)


def all_subject_templates():
    templates = list(SUBJECTS.values())
    templates += [
        account_tasks.VERIFY_SUBJECT,
        account_tasks.ALREADY_REGISTERED_SUBJECT,
        account_tasks.RESET_SUBJECT,
        account_tasks.PASSWORD_CHANGED_SUBJECT,
        account_tasks.DELETED_SUBJECT,
        notifications.SUBJECT,
        notifications.PRIORITY_SUBJECT,
    ]
    return templates


@pytest.mark.parametrize("template", all_subject_templates())
def test_subjects_are_neutral(template):
    assert not REVEALING.search(template.format(day="Friday")), template


def test_rsvp_subjects_never_include_event_details(make_event):
    event = make_event(title="Members Social Night", category="member_night")
    for kind in SUBJECTS:
        subject = subject_for(kind, event)
        assert "Members" not in subject and "Social" not in subject
        assert timezone.localtime(event.starts_at).strftime("%A") in subject


def test_every_sent_email_uses_neutral_sender(make_event, make_user):
    submit_rsvp(make_user(), make_event(), 1)
    assert mail.outbox
    for message in mail.outbox:
        assert message.from_email == "Rose <no-reply@localhost>"
        assert not REVEALING.search(message.subject)


def test_reminders_sent_once_within_24_hours(make_event, make_user):
    soon = make_event(starts_at=timezone.now() + timedelta(hours=20))
    later = make_event(starts_at=timezone.now() + timedelta(days=3))
    early = submit_rsvp(make_user(email="early@example.org"), soon, 1).rsvp
    RSVP.objects.filter(pk=early.pk).update(created_at=timezone.now() - timedelta(days=2))
    submit_rsvp(make_user(email="late@example.org"), soon, 1)
    submit_rsvp(make_user(email="other@example.org"), later, 1)
    mail.outbox.clear()

    assert send_due_reminders() == 1
    assert [m.to for m in mail.outbox] == [["early@example.org"]]
    day = timezone.localtime(soon.starts_at).strftime("%A")
    assert mail.outbox[0].subject == f"A reminder for {day}"
    assert "/events/cancel#token=" in mail.outbox[0].body
    assert send_due_reminders() == 0


def test_no_reminder_for_cancelled_or_waitlisted(make_event, make_user):
    event = make_event(starts_at=timezone.now() + timedelta(hours=10), capacity=1)
    going = submit_rsvp(make_user(), event, 1).rsvp
    waiting = submit_rsvp(make_user(), event, 1).rsvp
    RSVP.objects.filter(pk__in=[going.pk, waiting.pk]).update(
        created_at=timezone.now() - timedelta(days=2), status=RSVP.Status.CANCELLED
    )
    RSVP.objects.filter(pk=waiting.pk).update(status=RSVP.Status.WAITLIST)
    mail.outbox.clear()
    assert send_due_reminders() == 0
