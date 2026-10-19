"""Rental inquiries: the form, clash warnings, the pipeline, the private hold and retention."""

from datetime import datetime, time, timedelta

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.core.models import AuditLog
from apps.events.models import Event
from apps.rentals import services
from apps.rentals.models import RentalInquiry
from apps.rentals.tasks import purge_closed_inquiries
from tests.conftest import PASSWORD

pytestmark = pytest.mark.django_db
URL = "/api/rentals/inquiries/"


def payload(**overrides):
    data = {
        "contact_name": "Robin Planner",
        "contact_email": "robin@private.example",
        "contact_phone": "",
        "type": "workshop",
        "preferred_date": (timezone.localdate() + timedelta(days=10)).isoformat(),
        "alternate_date": None,
        "start_time": "14:00",
        "duration_hours": 3,
        "party_size": 12,
        "notes": "A rope workshop for twelve.",
        "photoshoot_acknowledged": False,
        "website": "",
    }
    data.update(overrides)
    return data


def make_inquiry(**overrides):
    values = {
        "contact_name": "Robin Planner",
        "contact_email": "robin@private.example",
        "type": RentalInquiry.Type.WORKSHOP,
        "preferred_date": timezone.localdate() + timedelta(days=10),
        "start_time": time(14, 0),
        "duration_hours": 3,
        "party_size": 12,
    }
    values.update(overrides)
    return RentalInquiry.objects.create(**values)


def test_inquiry_is_stored_and_answered_neutrally(csrf_client):
    response = csrf_client.post(URL, payload(), format="json")
    assert response.status_code == 201
    body = response.content.decode()
    assert "robin@private.example" not in body and "rope" not in body
    inquiry = RentalInquiry.objects.get()
    assert inquiry.status == "new" and inquiry.user is None
    subjects = sorted(m.subject for m in mail.outbox)
    assert subjects == ["New request received", "We received your request"]
    staff = next(m for m in mail.outbox if m.subject == "New request received")
    assert "Robin" not in staff.body and "rope" not in staff.body
    assert staff.to == ["staff-inbox@example.org"]


def test_signed_in_inquiries_are_linked_to_the_account(signed_in):
    client, user = signed_in()
    assert client.post(URL, payload(), format="json").status_code == 201
    assert RentalInquiry.objects.get().user == user


def test_photoshoots_need_the_acknowledgement(csrf_client):
    response = csrf_client.post(URL, payload(type="photoshoot"), format="json")
    assert response.status_code == 400
    assert "photoshoot_acknowledged" in response.json()
    ok = csrf_client.post(
        URL, payload(type="photoshoot", photoshoot_acknowledged=True), format="json"
    )
    assert ok.status_code == 201
    assert RentalInquiry.objects.get().photoshoot_acknowledged is True


@pytest.mark.parametrize(
    "overrides",
    [
        {"preferred_date": timezone.localdate().isoformat()},
        {"duration_hours": 13},
        {"party_size": 0},
        {"contact_email": "not-an-email"},
        {"type": "concert"},
    ],
)
def test_bad_inquiries_are_refused(csrf_client, overrides):
    assert csrf_client.post(URL, payload(**overrides), format="json").status_code == 400
    assert not RentalInquiry.objects.exists()


def test_alternate_must_differ_from_the_first_choice(csrf_client):
    data = payload()
    data["alternate_date"] = data["preferred_date"]
    assert csrf_client.post(URL, data, format="json").status_code == 400


def test_honeypot_looks_successful_and_stores_nothing(csrf_client):
    response = csrf_client.post(URL, payload(website="http://spam"), format="json")
    assert response.status_code == 201
    assert not RentalInquiry.objects.exists() and mail.outbox == []


def test_inquiries_are_rate_limited(csrf_client, settings):
    settings.RENTAL_INQUIRY_RATE_LIMIT = "2/h"
    for _ in range(2):
        assert csrf_client.post(URL, payload(), format="json").status_code == 201
    assert csrf_client.post(URL, payload(), format="json").status_code == 429


# Clash detection


def test_conflict_with_a_published_event_on_either_date(make_event):
    day = timezone.localdate() + timedelta(days=10)
    starts = timezone.make_aware(datetime.combine(day, time(15, 0)))
    event = make_event(starts_at=starts)
    clash = make_inquiry(preferred_date=day)
    assert services.conflicts(clash)["preferred"] == [event]
    # The event runs 15:00 to 18:00; an evening booking after it does not clash.
    late = make_inquiry(preferred_date=day, start_time=time(19, 0), duration_hours=1)
    assert services.conflicts(late)["preferred"] == []
    # Without a start time the whole day counts.
    unsure = make_inquiry(preferred_date=day, start_time=None, duration_hours=None)
    assert services.conflicts(unsure)["preferred"] == [event]
    other = make_inquiry(preferred_date=day + timedelta(days=1), alternate_date=day)
    found = services.conflicts(other)
    assert found["preferred"] == [] and found["alternate"] == [event]


def test_unpublished_events_do_not_clash(make_event):
    day = timezone.localdate() + timedelta(days=10)
    make_event(
        starts_at=timezone.make_aware(datetime.combine(day, time(14, 0))), is_published=False
    )
    assert services.conflicts(make_inquiry(preferred_date=day))["preferred"] == []


def test_admin_flags_the_clash(admin_client, make_event):
    day = timezone.localdate() + timedelta(days=10)
    make_event(
        title="Rope Night", starts_at=timezone.make_aware(datetime.combine(day, time(15, 0)))
    )
    inquiry = make_inquiry(preferred_date=day)
    page = admin_client.get(reverse("admin:rentals_pipeline")).content.decode()
    assert "Clash:" in page and "Rope Night" in page
    change = admin_client.get(
        reverse("admin:rentals_rentalinquiry_change", args=[inquiry.pk])
    ).content.decode()
    assert "First choice overlaps" in change and "Rope Night" in change


def test_pipeline_groups_by_status(admin_client):
    make_inquiry(status="quoted", contact_name="Quoted Person")
    make_inquiry(status="new")
    page = admin_client.get(reverse("admin:rentals_pipeline")).content.decode()
    for label in ("New", "In discussion", "Quoted", "Confirmed", "Declined", "Cancelled"):
        assert f">{label} <span" in page
    assert "Quoted Person" not in page  # cards never show who asked


# Status changes, the private hold and the audit log


def test_status_changes_are_audited(admin_client, admin_user):
    inquiry = make_inquiry()
    admin_client.post(
        reverse("admin:rentals_status", args=[inquiry.pk]),
        {"status": "in_discussion", "reason": "Called back"},
    )
    inquiry.refresh_from_db()
    assert inquiry.status == "in_discussion"
    entry = AuditLog.objects.get(category="rentals", action="status_in_discussion")
    assert entry.actor == admin_user and entry.target_ref == str(inquiry.pk)
    assert "New to In discussion" in entry.reason
    assert "Robin" not in entry.target_label


def test_confirming_can_hold_the_date_privately(admin_client, api_client):
    inquiry = make_inquiry()
    admin_client.post(
        reverse("admin:rentals_confirm", args=[inquiry.pk]),
        {"create_hold": "on", "reason": "Deposit received"},
    )
    inquiry.refresh_from_db()
    assert inquiry.status == "confirmed" and inquiry.hold is not None
    hold = inquiry.hold
    assert hold.is_private_hold and not hold.is_published
    start, end = inquiry.window()
    assert (hold.starts_at, hold.ends_at) == (start, end)
    # Never public: not in any list, calendar or detail.
    assert not Event.objects.published().filter(pk=hold.pk).exists()
    assert hold.slug not in api_client.get("/api/events/").content.decode()
    assert api_client.get(f"/api/events/{hold.slug}/").status_code == 404
    # It does stop another booking for the same time.
    other = make_inquiry(preferred_date=inquiry.preferred_date)
    assert services.conflicts(other)["preferred"] == [hold]
    actions = set(AuditLog.objects.filter(category="rentals").values_list("action", flat=True))
    assert {"status_confirmed", "calendar_hold"} <= actions


def test_a_hold_can_never_be_published(make_event):
    inquiry = make_inquiry()
    services.confirm(None, inquiry, create_hold=True)
    hold = Event.objects.get(is_private_hold=True)
    hold.is_published = True
    hold.save()
    hold.refresh_from_db()
    assert hold.is_published is False


def test_declining_removes_the_hold(make_event):
    inquiry = make_inquiry()
    services.confirm(None, inquiry, create_hold=True)
    services.change_status(None, inquiry, RentalInquiry.Status.DECLINED)
    inquiry.refresh_from_db()
    assert inquiry.hold is None and inquiry.closed_at is not None
    assert not Event.objects.filter(is_private_hold=True).exists()


# Retention


def test_closed_inquiries_keep_only_type_date_and_status(settings):
    settings.RENTAL_RETENTION_DAYS = 90
    old = make_inquiry(status="declined", notes="private notes", staff_notes="staff only")
    RentalInquiry.objects.filter(pk=old.pk).update(closed_at=timezone.now() - timedelta(days=91))
    recent = make_inquiry(status="cancelled")
    RentalInquiry.objects.filter(pk=recent.pk).update(closed_at=timezone.now() - timedelta(days=10))
    confirmed = make_inquiry(status="confirmed", preferred_date=timezone.localdate())
    assert purge_closed_inquiries() == 1
    old.refresh_from_db()
    assert (old.type, old.status) == ("workshop", "declined")
    assert old.preferred_date is not None
    for field in ("contact_name", "contact_email", "contact_phone", "notes", "staff_notes"):
        assert getattr(old, field) == ""
    assert old.party_size is None and old.start_time is None and old.contact_purged_at
    recent.refresh_from_db()
    confirmed.refresh_from_db()
    assert recent.contact_email and confirmed.contact_email


def test_forgotten_open_inquiries_are_purged_after_their_dates(settings):
    stale = make_inquiry(preferred_date=timezone.localdate() - timedelta(days=100))
    assert purge_closed_inquiries() == 1
    stale.refresh_from_db()
    assert stale.contact_email == "" and stale.status == "new"


def test_retention_runs_on_beat(settings):
    tasks = {entry["task"] for entry in settings.CELERY_BEAT_SCHEDULE.values()}
    assert "apps.rentals.tasks.purge_closed_inquiries" in tasks


def test_deleting_an_account_strips_its_inquiries(signed_in):
    client, user = signed_in()
    client.post(URL, payload(), format="json")
    response = client.post("/api/account/delete/", {"password": PASSWORD}, format="json")
    assert response.status_code == 200
    inquiry = RentalInquiry.objects.get()
    assert inquiry.contact_email == "" and inquiry.user is None
