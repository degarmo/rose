import threading
from datetime import timedelta

import pytest
from django.core import mail
from django.db import connection
from django.utils import timezone

from apps.events.models import RSVP, Event
from apps.events.services import RSVPError, cancel_rsvp, submit_rsvp
from apps.events.tasks import SUBJECTS, make_cancel_token

pytestmark = pytest.mark.django_db


def going_total(event):
    return Event.objects.get(pk=event.pk).going_count()


def test_rsvp_under_capacity_is_going(make_event, make_user):
    event = make_event(capacity=10)
    result = submit_rsvp(make_user(), event, 2, "Running late")
    assert result.rsvp.status == RSVP.Status.GOING
    assert result.rsvp.note_to_hosts == "Running late"
    assert going_total(event) == 2


def test_capacity_counts_party_size(make_event, make_user):
    event = make_event(capacity=3)
    submit_rsvp(make_user(), event, 2)
    result = submit_rsvp(make_user(), event, 2)
    assert result.rsvp.status == RSVP.Status.WAITLIST
    third = submit_rsvp(make_user(), event, 1)
    assert third.rsvp.status == RSVP.Status.GOING
    assert going_total(event) == 3


def test_unlimited_capacity(make_event, make_user):
    event = make_event(capacity=None)
    for _ in range(5):
        assert submit_rsvp(make_user(), event, 2).rsvp.status == RSVP.Status.GOING
    assert going_total(event) == 10


def test_full_without_waitlist_refuses(make_event, make_user):
    event = make_event(capacity=1, waitlist_enabled=False)
    submit_rsvp(make_user(), event, 1)
    with pytest.raises(RSVPError) as exc:
        submit_rsvp(make_user(), event, 1)
    assert exc.value.code == "full"


def test_party_size_limits(make_event, make_user):
    event = make_event(max_party_size=1)
    with pytest.raises(RSVPError) as exc:
        submit_rsvp(make_user(), event, 2)
    assert exc.value.code == "party_size"
    with pytest.raises(RSVPError):
        submit_rsvp(make_user(), make_event(), 0)


def test_unverified_or_closed_refused(make_event, make_user):
    with pytest.raises(RSVPError) as exc:
        submit_rsvp(make_user(verified=False), make_event(), 1)
    assert exc.value.code == "unverified"
    closed = make_event(starts_at=timezone.now() - timedelta(minutes=1))
    with pytest.raises(RSVPError) as exc:
        submit_rsvp(make_user(), closed, 1)
    assert exc.value.code == "closed"


def test_changing_party_size_respects_capacity(make_event, make_user):
    event = make_event(capacity=2)
    first = make_user()
    submit_rsvp(first, event, 1)
    submit_rsvp(make_user(), event, 1)
    with pytest.raises(RSVPError) as exc:
        submit_rsvp(first, event, 2)
    assert exc.value.code == "no_room_for_change"
    updated = submit_rsvp(first, event, 1, "New note")
    assert updated.outcome == "updated"
    assert updated.rsvp.note_to_hosts == "New note"


def test_cancel_promotes_oldest_waitlisted_that_fits(make_event, make_user):
    event = make_event(capacity=2)
    holder = make_user()
    holder_rsvp = submit_rsvp(holder, event, 2).rsvp
    big = submit_rsvp(make_user(), event, 2).rsvp
    small = submit_rsvp(make_user(), event, 1).rsvp
    assert big.status == small.status == RSVP.Status.WAITLIST

    # A guest leaving frees one place: the oldest party of two does not fit, the party of one does.
    submit_rsvp(holder, event, 1)
    small.refresh_from_db()
    big.refresh_from_db()
    assert small.status == RSVP.Status.GOING
    assert big.status == RSVP.Status.WAITLIST

    mail.outbox.clear()
    result = cancel_rsvp(holder_rsvp)
    assert result.outcome == "cancelled"
    big.refresh_from_db()
    # Only one place is free, and the waiting party of two needs two.
    assert big.status == RSVP.Status.WAITLIST
    cancel_rsvp(small)
    big.refresh_from_db()
    assert big.status == RSVP.Status.GOING
    assert going_total(event) == 2


def test_promotion_emails_the_promoted_person(make_event, make_user):
    event = make_event(capacity=1)
    first = submit_rsvp(make_user(), event, 1).rsvp
    waiting_user = make_user(email="waiting@example.org")
    submit_rsvp(waiting_user, event, 1)
    mail.outbox.clear()
    cancel_rsvp(first)
    subjects = {(m.to[0], m.subject) for m in mail.outbox}
    day = timezone.localtime(event.starts_at).strftime("%A")
    assert ("waiting@example.org", SUBJECTS["promoted"].format(day=day)) in subjects
    assert (first.user.email, SUBJECTS["cancellation"].format(day=day)) in subjects


def test_cancel_twice_is_harmless(make_event, make_user):
    rsvp = submit_rsvp(make_user(), make_event(), 1).rsvp
    cancel_rsvp(rsvp)
    assert cancel_rsvp(rsvp).outcome == "unchanged"


def test_rebooking_after_cancel(make_event, make_user):
    user = make_user()
    event = make_event(capacity=5)
    rsvp = submit_rsvp(user, event, 1).rsvp
    cancel_rsvp(rsvp)
    again = submit_rsvp(user, event, 2)
    assert again.rsvp.pk == rsvp.pk
    assert again.rsvp.status == RSVP.Status.GOING
    assert RSVP.objects.filter(event=event, user=user).count() == 1


def test_confirmation_and_waitlist_emails(make_event, make_user):
    event = make_event(capacity=1, title="Secret Evening Title")
    submit_rsvp(make_user(email="first@example.org"), event, 1)
    submit_rsvp(make_user(email="second@example.org"), event, 1)
    day = timezone.localtime(event.starts_at).strftime("%A")
    by_recipient = {m.to[0]: m for m in mail.outbox}
    assert by_recipient["first@example.org"].subject == f"Your plans for {day}"
    assert by_recipient["second@example.org"].subject == f"Your waitlist place for {day}"
    body = by_recipient["first@example.org"].body
    assert "Secret Evening Title" in body
    assert "https://site.example/events/cancel#token=" in body
    for message in mail.outbox:
        assert "Secret" not in message.subject


@pytest.mark.django_db(transaction=True)
def test_two_people_racing_for_the_last_place(make_event, make_user):
    event = make_event(capacity=1, waitlist_enabled=True)
    racers = [make_user(), make_user()]
    barrier = threading.Barrier(2)
    outcomes, errors = [], []

    def attempt(user):
        try:
            barrier.wait(timeout=5)
            outcomes.append(submit_rsvp(user, event, 1).rsvp.status)
        except Exception as exc:  # surfaced in the assertion below
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=attempt, args=(user,)) for user in racers]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert errors == []
    assert sorted(outcomes) == [RSVP.Status.GOING, RSVP.Status.WAITLIST]
    assert going_total(event) == 1


@pytest.mark.django_db(transaction=True)
def test_racing_without_waitlist_never_oversells(make_event, make_user):
    event = make_event(capacity=1, waitlist_enabled=False)
    racers = [make_user() for _ in range(4)]
    barrier = threading.Barrier(len(racers))
    codes = []

    def attempt(user):
        try:
            barrier.wait(timeout=5)
            submit_rsvp(user, event, 1)
            codes.append("going")
        except RSVPError as exc:
            codes.append(exc.code)
        finally:
            connection.close()

    threads = [threading.Thread(target=attempt, args=(user,)) for user in racers]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert sorted(codes) == ["full", "full", "full", "going"]
    assert going_total(event) == 1


# API


def test_rsvp_api_flow(signed_in, make_event):
    event = make_event(capacity=4, show_attendee_count=True)
    client, user = signed_in()
    response = client.post(
        f"/api/events/{event.slug}/rsvp/", {"party_size": 2, "note_to_hosts": " hi "}, format="json"
    )
    assert response.status_code == 200
    rsvp = response.json()["rsvp"]
    assert rsvp["state"] == "going"
    assert rsvp["mine"] == {"status": "going", "party_size": 2, "note_to_hosts": "hi"}

    detail = client.get(f"/api/events/{event.slug}/").json()
    assert detail["rsvp"]["state"] == "going"
    assert detail["attendee_count"] == 2

    cancelled = client.delete(f"/api/events/{event.slug}/rsvp/")
    assert cancelled.json()["rsvp"]["state"] == "open"
    assert cancelled.json()["rsvp"]["mine"] is None


def test_rsvp_api_conflicts_and_auth(signed_in, make_event, csrf_client):
    event = make_event(capacity=1, waitlist_enabled=False)
    assert csrf_client.post(f"/api/events/{event.slug}/rsvp/", {}, format="json").status_code == 403
    first, _ = signed_in()
    second, _ = signed_in()
    assert first.post(f"/api/events/{event.slug}/rsvp/", {}, format="json").status_code == 200
    response = second.post(f"/api/events/{event.slug}/rsvp/", {}, format="json")
    assert response.status_code == 409
    assert response.json()["code"] == "full"
    unverified, _ = signed_in(verified=False)
    response = unverified.post(f"/api/events/{event.slug}/rsvp/", {}, format="json")
    assert response.json()["code"] == "unverified"


def test_rsvp_api_validates_input(signed_in, make_event):
    event = make_event()
    client, _ = signed_in()
    too_big = client.post(f"/api/events/{event.slug}/rsvp/", {"party_size": 3}, format="json")
    assert too_big.status_code == 400
    long_note = client.post(
        f"/api/events/{event.slug}/rsvp/", {"note_to_hosts": "x" * 281}, format="json"
    )
    assert long_note.status_code == 400


def test_cancel_by_email_token(csrf_client, make_event, make_user):
    event = make_event()
    rsvp = submit_rsvp(make_user(), event, 1).rsvp
    response = csrf_client.post(
        "/api/events/rsvp/cancel/", {"token": make_cancel_token(rsvp)}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["event"]["slug"] == event.slug
    rsvp.refresh_from_db()
    assert rsvp.status == RSVP.Status.CANCELLED
    bad = csrf_client.post("/api/events/rsvp/cancel/", {"token": "forged"}, format="json")
    assert bad.status_code == 400


def test_my_rsvps_lists_only_own_upcoming(signed_in, make_event, make_user):
    client, user = signed_in()
    mine = make_event(title="Mine")
    submit_rsvp(user, mine, 1)
    submit_rsvp(make_user(), make_event(title="Theirs"), 1)
    past = make_event(starts_at=timezone.now() + timedelta(days=1))
    submit_rsvp(user, past, 1)
    Event.objects.filter(pk=past.pk).update(
        starts_at=timezone.now() - timedelta(days=3), ends_at=timezone.now() - timedelta(days=2)
    )
    data = client.get("/api/account/rsvps/").json()
    assert [item["event"]["title"] for item in data] == ["Mine"]
    assert set(data[0]) == {"status", "party_size", "note_to_hosts", "event"}
