import csv
import io
from datetime import datetime, time, timedelta

import pytest
from django.contrib.auth.models import Permission
from django.utils import timezone

from apps.events.models import RSVP, AttendeeExport, Event
from apps.events.recurrence import repeat_weekly
from apps.events.services import submit_rsvp
from tests.conftest import staff_login

pytestmark = pytest.mark.django_db

CHANGELIST = "/admin/events/event/"


def chicago(year, month, day, hour):
    return timezone.make_aware(datetime.combine(datetime(year, month, day).date(), time(hour)))


def test_repeat_weekly_action_shows_intermediate_form(admin_client, make_event):
    event = make_event()
    response = admin_client.post(
        CHANGELIST, {"action": "repeat_weekly_action", "_selected_action": [event.pk]}
    )
    assert response.status_code == 200
    assert b"How many weeks forward" in response.content
    assert Event.objects.count() == 1


def test_repeat_weekly_action_creates_dated_copies_without_rsvps(
    admin_client, make_event, make_user
):
    event = make_event(slug="thursday-class", capacity=20)
    submit_rsvp(make_user(), event, 1)
    response = admin_client.post(
        CHANGELIST,
        {
            "action": "repeat_weekly_action",
            "_selected_action": [event.pk],
            "apply": "1",
            "weeks": "3",
        },
        follow=True,
    )
    assert response.status_code == 200
    copies = Event.objects.exclude(pk=event.pk).order_by("starts_at")
    assert copies.count() == 3
    for week, copy in enumerate(copies, start=1):
        expected_start = event.starts_at + timedelta(weeks=week)
        assert copy.slug == f"thursday-class-{timezone.localtime(expected_start):%Y-%m-%d}"
        assert copy.capacity == 20
        assert copy.rsvps.count() == 0
    assert RSVP.objects.count() == 1


def test_repeat_weekly_keeps_wall_clock_across_dst(make_event):
    # 2026-10-29 19:00 CDT; the next week is after the switch to CST on 2026-11-01.
    event = make_event(slug="dst-test", starts_at=chicago(2026, 10, 29, 19))
    created, _ = repeat_weekly(event, 1)
    local = timezone.localtime(created[0].starts_at)
    assert (local.hour, local.minute) == (19, 0)
    assert local.date().isoformat() == "2026-11-05"


def test_repeat_weekly_replaces_existing_date_suffix_and_skips_duplicates(make_event):
    event = make_event(slug="social-2026-11-06", starts_at=chicago(2026, 11, 6, 21))
    created, skipped = repeat_weekly(event, 2)
    assert [c.slug for c in created] == ["social-2026-11-13", "social-2026-11-20"]
    created, skipped = repeat_weekly(event, 2)
    assert created == [] and skipped == ["social-2026-11-13", "social-2026-11-20"]


def test_door_list_shows_reminder_and_display_names(admin_client, make_event, make_user):
    event = make_event()
    submit_rsvp(make_user(display_name="door_guest", email="hidden@example.org"), event, 2)
    response = admin_client.get(f"/admin/events/event/{event.pk}/door/")
    content = response.content.decode()
    assert response.status_code == 200
    assert "Verify 18+ photo ID at the door" in content
    assert "door_guest" in content
    assert "hidden@example.org" not in content


def test_door_list_check_in_toggle(admin_client, make_event, make_user):
    event = make_event()
    rsvp = submit_rsvp(make_user(), event, 1).rsvp
    admin_client.post(f"/admin/events/event/{event.pk}/door/", {"rsvp": rsvp.pk, "checked_in": "1"})
    rsvp.refresh_from_db()
    assert rsvp.checked_in is True
    admin_client.post(f"/admin/events/event/{event.pk}/door/", {"rsvp": rsvp.pk, "checked_in": "0"})
    rsvp.refresh_from_db()
    assert rsvp.checked_in is False


def test_csv_export_is_logged_and_formula_safe(admin_client, admin_user, make_event, make_user):
    event = make_event()
    submit_rsvp(make_user(display_name="=cmd", email="a@example.org"), event, 1)
    submit_rsvp(make_user(display_name="plain_name"), event, 2)
    response = admin_client.get(f"/admin/events/event/{event.pk}/door/export/")
    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(response.content.decode())))
    assert rows[0] == ["Display name", "Party size", "Checked in", "Note to hosts"]
    assert ["'=cmd", "1", "no", ""] in rows
    assert "a@example.org" not in response.content.decode()

    log = AttendeeExport.objects.get()
    assert log.exported_by == admin_user
    assert log.exported_by_label == "house_admin"
    assert log.row_count == 2
    assert log.event == event


def test_door_list_requires_permissions(client, make_user, make_event):
    event = make_event()
    staff = make_user(is_staff=True)
    staff_login(client, staff)
    assert client.get(f"/admin/events/event/{event.pk}/door/").status_code == 403
    staff.user_permissions.add(Permission.objects.get(codename="view_rsvp"))
    # A permission change ends existing sessions; sign in again.
    assert client.get(f"/admin/events/event/{event.pk}/door/").status_code == 302
    staff_login(client, staff)
    assert client.get(f"/admin/events/event/{event.pk}/door/").status_code == 200
    assert client.get(f"/admin/events/event/{event.pk}/door/export/").status_code == 403
    assert AttendeeExport.objects.count() == 0


def test_admin_blocks_publishing_unconsented_faces(admin_client, gps_image_path):
    from django.core.files.uploadedfile import SimpleUploadedFile

    start = timezone.localtime(timezone.now() + timedelta(days=2))
    end = start + timedelta(hours=3)
    upload = SimpleUploadedFile("x.jpg", gps_image_path.read_bytes(), content_type="image/jpeg")
    data = {
        "title": "With faces",
        "slug": "with-faces",
        "summary": "s",
        "body": "",
        "category": "social",
        "starts_at_0": start.strftime("%Y-%m-%d"),
        "starts_at_1": start.strftime("%H:%M:%S"),
        "ends_at_0": end.strftime("%Y-%m-%d"),
        "ends_at_1": end.strftime("%H:%M:%S"),
        "location_label": "",
        "audience": "public",
        "waitlist_enabled": "on",
        "max_party_size": "2",
        "guest_allowance": "0",
        "hero_image": upload,
        "hero_image_alt": "People at the bar",
        "hero_image_faces_visible": "on",
        "is_published": "on",
    }
    response = admin_client.post("/admin/events/event/add/", data)
    assert response.status_code == 200
    assert "cannot be published" in response.content.decode()
    assert not Event.objects.exists()

    upload.seek(0)
    data["hero_image"] = upload
    data["hero_image_consent_confirmed"] = "on"
    response = admin_client.post("/admin/events/event/add/", data)
    assert response.status_code == 302
    assert Event.objects.get().image_is_displayable("hero_image")


def test_event_validation(make_event):
    from django.core.exceptions import ValidationError

    event = make_event()
    event.ends_at = event.starts_at - timedelta(hours=1)
    event.slug = "calendar"
    event.capacity = 0
    with pytest.raises(ValidationError) as exc:
        event.full_clean()
    assert {"ends_at", "slug", "capacity"} <= set(exc.value.message_dict)
