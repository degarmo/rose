import pytest
from django.core import mail

from apps.accounts import tasks
from apps.accounts.models import Profile, User
from apps.contact.models import ANONYMIZED_NAME, ContactMessage
from apps.events.models import RSVP
from apps.events.services import submit_rsvp

from .conftest import PASSWORD

pytestmark = pytest.mark.django_db


def test_delete_cascades_and_anonymizes(signed_in, make_event, make_user):
    client, user = signed_in(email="leaving@example.org")
    event = make_event(capacity=1)
    submit_rsvp(user, event, 1)
    waiting = make_user()
    submit_rsvp(waiting, event, 1)
    mine = ContactMessage.objects.create(
        name="Leaving Person",
        email="LEAVING@example.org",
        phone="312 555 0100",
        topic="concern",
        message="Something happened.",
    )
    theirs = ContactMessage.objects.create(
        name="Someone Else", email="else@example.org", topic="general", message="Hello there."
    )

    response = client.post("/api/account/delete/", {"password": PASSWORD}, format="json")
    assert response.status_code == 200
    assert response.json()["user"] is None

    assert not User.objects.filter(pk=user.pk).exists()
    assert not Profile.objects.filter(user_id=user.pk).exists()
    assert not RSVP.objects.filter(user_id=user.pk).exists()

    mine.refresh_from_db()
    assert (mine.name, mine.email, mine.phone) == (ANONYMIZED_NAME, "", "")
    assert mine.anonymized_at is not None
    assert mine.message == "Something happened."
    assert mine.is_priority
    theirs.refresh_from_db()
    assert theirs.name == "Someone Else"

    # Their freed place goes to the waitlist.
    assert RSVP.objects.get(user=waiting).status == RSVP.Status.GOING
    assert any(m.subject == tasks.DELETED_SUBJECT for m in mail.outbox)
    to_leaver = [m.subject for m in mail.outbox if m.to == ["leaving@example.org"]]
    assert not any("cancelled" in subject for subject in to_leaver)
    assert client.get("/api/account/session/").json()["user"] is None


def test_delete_needs_correct_password(signed_in):
    client, user = signed_in()
    response = client.post("/api/account/delete/", {"password": "wrong"}, format="json")
    assert response.status_code == 400
    assert User.objects.filter(pk=user.pk).exists()
