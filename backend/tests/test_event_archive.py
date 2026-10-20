"""Past events: one definition (Event.timing and the queryset helpers), the admin's main
list and its archive, duplicating, editing anyway, and the public site."""

import re
from datetime import UTC, datetime, timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.core.models import AuditLog
from apps.events.models import DEFAULT_LENGTH, RSVP, Event, EventTag, Timing
from apps.safety import roles
from tests.conftest import staff_login

pytestmark = pytest.mark.django_db

MAIN = "/admin/events/event/"
ARCHIVE = "/admin/events/pastevent/"


def chicago(year, month, day, hour, minute=0):
    return timezone.make_aware(datetime(year, month, day, hour, minute))


def timings(now):
    """Each event's timing by the queryset helpers, to check they agree with the property."""
    return {
        **{e.slug: Timing.UPCOMING for e in Event.objects.upcoming(now)},
        **{e.slug: Timing.HAPPENING for e in Event.objects.happening(now)},
        **{e.slug: Timing.PAST for e in Event.objects.past(now)},
    }


# The one definition


def test_the_edges_of_upcoming_happening_and_past(make_event):
    start = chicago(2026, 11, 6, 19)
    event = make_event(slug="edges", starts_at=start, ends_at=chicago(2026, 11, 6, 22))
    second = timedelta(seconds=1)
    for now, expected in (
        (start - second, Timing.UPCOMING),
        (start, Timing.HAPPENING),
        (event.ends_at, Timing.HAPPENING),
        (event.ends_at + second, Timing.PAST),
    ):
        assert event.timing_at(now) == expected, now
        assert timings(now)["edges"] == expected, now


def test_an_event_ending_after_midnight_is_happening_until_it_ends(make_event):
    event = make_event(
        slug="late", starts_at=chicago(2026, 11, 6, 21), ends_at=chicago(2026, 11, 7, 1)
    )
    after_midnight = chicago(2026, 11, 7, 0, 30)
    assert timezone.localtime(after_midnight).date() > timezone.localtime(event.starts_at).date()
    assert event.timing_at(after_midnight) == Timing.HAPPENING
    assert timings(after_midnight)["late"] == Timing.HAPPENING
    assert event.timing_at(chicago(2026, 11, 7, 1, 1)) == Timing.PAST


def test_with_no_end_time_it_is_over_six_hours_after_it_starts(make_event):
    start = chicago(2026, 11, 6, 20)
    event = make_event(slug="open-ended", starts_at=start, ends_at=None)
    assert event.effective_end == start + DEFAULT_LENGTH == chicago(2026, 11, 7, 2)
    assert event.timing_at(start + timedelta(hours=5, minutes=59)) == Timing.HAPPENING
    assert timings(start + DEFAULT_LENGTH)["open-ended"] == Timing.HAPPENING
    later = start + DEFAULT_LENGTH + timedelta(minutes=1)
    assert event.timing_at(later) == Timing.PAST
    assert timings(later)["open-ended"] == Timing.PAST


def test_times_are_instants_shown_in_chicago(make_event):
    """9 pm in Chicago is 3 am the next day in UTC: still the same evening, same answer."""
    event = make_event(
        slug="utc", starts_at=chicago(2026, 11, 6, 21), ends_at=chicago(2026, 11, 6, 23)
    )
    utc_moment = datetime(2026, 11, 7, 4, 0, tzinfo=UTC)  # 10 pm in Chicago
    assert event.timing_at(utc_moment) == Timing.HAPPENING
    assert timezone.localtime(event.starts_at).hour == 21


# The admin: the main list and the archive


@pytest.fixture
def events(make_event):
    now = timezone.now()
    return {
        "next": make_event(title="Next social", starts_at=now + timedelta(days=2)),
        "now": make_event(
            title="On right now",
            starts_at=now - timedelta(hours=1),
            ends_at=now + timedelta(hours=2),
        ),
        "draft": make_event(
            title="Draft night", starts_at=now + timedelta(days=5), is_published=False
        ),
        "old": make_event(title="Old social", starts_at=now - timedelta(days=20)),
        "older": make_event(title="Older class", starts_at=now - timedelta(days=60)),
    }


def test_the_main_list_shows_what_is_coming_soonest_first(admin_client, events):
    page = admin_client.get(MAIN).content.decode()
    for name in ("Next social", "On right now", "Draft night"):
        assert name in page
    assert "Old social" not in page and "Older class" not in page
    assert page.index("On right now") < page.index("Next social") < page.index("Draft night")
    for badge in ("Upcoming", "Happening now", "Draft"):
        assert badge in page
    assert "2 past events in the archive" in page and ARCHIVE in page
    assert "Repeat weekly" in page


def test_the_archive_shows_only_past_events_newest_first(admin_client, events):
    page = admin_client.get(ARCHIVE).content.decode()
    assert "Old social" in page and "Older class" in page
    assert page.index("Old social") < page.index("Older class")
    for name in ("Next social", "On right now", "Draft night"):
        assert name not in page
    for title in ("year", "month", "category", "tags"):
        assert f"By {title}" in page, title


def test_the_archive_shows_final_counts_through_the_metrics_rule(admin_client, events):
    old = events["old"]
    old.final_going_count, old.final_checked_in_count = 12, 3
    old.rsvps_purged_at = timezone.now()
    old.save()
    page = admin_client.get(ARCHIVE).content.decode()
    going = re.search(r'class="field-going[^"]*">([^<]+)</td>', page)
    checked_in = re.search(r'class="field-checked_in[^"]*">(.*?)</td>', page)
    assert going.group(1) == "12"
    assert 'title="fewer than 5"' in checked_in.group(1)


def test_editing_the_dates_moves_an_event_between_the_lists(admin_client, events):
    old = events["old"]
    old.starts_at = timezone.now() + timedelta(days=3)
    old.ends_at = old.starts_at + timedelta(hours=3)
    old.save()
    assert "Old social" in admin_client.get(MAIN).content.decode()
    assert "Old social" not in admin_client.get(ARCHIVE).content.decode()
    nxt = events["next"]
    nxt.starts_at = timezone.now() - timedelta(days=4)
    nxt.ends_at = nxt.starts_at + timedelta(hours=3)
    nxt.save()
    assert "Next social" in admin_client.get(ARCHIVE).content.decode()
    assert "Next social" not in admin_client.get(MAIN).content.decode()


def test_duplicate_as_new_event_makes_a_clean_draft(admin_client, events, make_user):
    old = events["old"]
    old.capacity = 40
    old.guest_allowance = 1
    old.final_going_count = 30
    old.rsvps_purged_at = timezone.now()
    old.save()
    tag = EventTag.objects.create(name="Tasting", slug="tasting")
    old.access_tags.add(tag)
    RSVP.objects.create(event=old, user=make_user(), status=RSVP.Status.GOING)

    form = admin_client.post(
        ARCHIVE, {"action": "duplicate_action", "_selected_action": [old.pk]}
    ).content.decode()
    assert "Duplicate as new event" in form and 'type="datetime-local"' in form

    new_start = timezone.localtime(timezone.now() + timedelta(days=14)).replace(
        hour=20, minute=0, second=0, microsecond=0
    )
    admin_client.post(
        ARCHIVE,
        {
            "action": "duplicate_action",
            "_selected_action": [old.pk],
            "apply": "1",
            f"start_{old.pk}": new_start.strftime("%Y-%m-%dT%H:%M"),
        },
    )
    copy = Event.objects.exclude(pk__in=[e.pk for e in events.values()]).get()
    assert copy.title == old.title and copy.body == old.body and copy.capacity == 40
    assert copy.guest_allowance == 1 and list(copy.access_tags.all()) == [tag]
    assert copy.starts_at == new_start
    assert copy.ends_at - copy.starts_at == old.ends_at - old.starts_at
    assert copy.is_published is False and copy.slug != old.slug
    assert copy.rsvps.count() == 0
    assert copy.final_going_count is None and copy.rsvps_purged_at is None
    assert copy.timing == Timing.UPCOMING
    assert AuditLog.objects.filter(action="duplicate_event", target_ref=copy.slug).exists()


def test_a_duplicate_needs_a_time_in_the_future(admin_client, events):
    old = events["old"]
    page = admin_client.post(
        ARCHIVE,
        {
            "action": "duplicate_action",
            "_selected_action": [old.pk],
            "apply": "1",
            f"start_{old.pk}": "2020-01-01T20:00",
        },
    ).content.decode()
    assert "Choose a time in the future." in page
    assert Event.objects.count() == len(events)


def test_unpublish_in_the_archive(admin_client, events):
    admin_client.post(
        ARCHIVE, {"action": "unpublish_action", "_selected_action": [events["old"].pk]}
    )
    events["old"].refresh_from_db()
    assert events["old"].is_published is False
    assert AuditLog.objects.filter(action="unpublish_event").exists()


def test_past_events_are_read_only_until_edited_anyway_and_that_is_logged(admin_client, events):
    old = events["old"]
    change = reverse("admin:events_pastevent_change", args=(old.pk,))
    read_only = admin_client.get(change).content.decode()
    assert 'name="title"' not in read_only
    assert "Edit anyway" in read_only and "This event is over" in read_only
    # The main admin's page for it opens the archive's.
    assert (
        admin_client.get(reverse("admin:events_event_change", args=(old.pk,)))["Location"] == change
    )

    editing = admin_client.get(f"{change}?edit=1").content.decode()
    assert 'name="title"' in editing and "Saving is logged" in editing
    data = {
        "title": "Old social (corrected)",
        "slug": old.slug,
        "summary": old.summary,
        "body": old.body,
        "category": old.category,
        "starts_at_0": timezone.localtime(old.starts_at).strftime("%Y-%m-%d"),
        "starts_at_1": timezone.localtime(old.starts_at).strftime("%H:%M:%S"),
        "ends_at_0": timezone.localtime(old.ends_at).strftime("%Y-%m-%d"),
        "ends_at_1": timezone.localtime(old.ends_at).strftime("%H:%M:%S"),
        "location_label": "",
        "audience": old.audience,
        "max_party_size": old.max_party_size,
        "guest_allowance": 0,
        "waitlist_enabled": "on",
        "is_published": "on",
        "hero_image_alt": "",
    }
    response = admin_client.post(f"{change}?edit=1", data)
    assert response.status_code == 302, response.content.decode()[:2000]
    old.refresh_from_db()
    assert old.title == "Old social (corrected)"
    entry = AuditLog.objects.get(action="edit_past_event")
    assert entry.target_ref == old.slug and "title" in entry.reason


def test_without_edit_anyway_a_past_event_cannot_be_changed(admin_client, events):
    old = events["old"]
    change = reverse("admin:events_pastevent_change", args=(old.pk,))
    admin_client.post(change, {"title": "Sneaky"})
    old.refresh_from_db()
    assert old.title == "Old social"
    assert not AuditLog.objects.filter(action="edit_past_event").exists()


def team_member(make_user, role):
    from django.contrib.auth.models import Permission

    user = make_user(display_name=f"events_{role}")
    roles.set_role(user, role)
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="events",
            codename__in=["view_event", "change_event", "add_event", "delete_event"],
        )
    )
    return staff_login(Client(), user)


@pytest.mark.parametrize(("role", "may_delete"), [(roles.STAFF, False), (roles.ADMIN, True)])
def test_only_admins_delete_from_the_archive_after_confirming(events, make_user, role, may_delete):
    client = team_member(make_user, role)
    old = events["old"]
    page = client.get(ARCHIVE).content.decode()
    assert ("delete_selected" in page) is may_delete
    delete = reverse("admin:events_pastevent_delete", args=(old.pk,))
    assert client.get(delete).status_code == (200 if may_delete else 403)
    confirm = client.post(ARCHIVE, {"action": "delete_selected", "_selected_action": [old.pk]})
    assert Event.objects.filter(pk=old.pk).exists()
    if may_delete:
        assert "Are you sure" in confirm.content.decode()
        client.post(
            ARCHIVE, {"action": "delete_selected", "_selected_action": [old.pk], "post": "yes"}
        )
        assert not Event.objects.filter(pk=old.pk).exists()


# The public site


def test_the_public_list_and_calendar_leave_past_events_out(api_client, events):
    slugs = [e["slug"] for e in api_client.get("/api/events/").json()["results"]]
    assert events["next"].slug in slugs and events["now"].slug in slugs
    assert events["old"].slug not in slugs
    past = [e["slug"] for e in api_client.get("/api/events/?past=1").json()["results"]]
    assert past == [events["old"].slug, events["older"].slug]
    today = timezone.localdate()
    calendar = api_client.get(
        "/api/events/calendar/",
        {
            "start": (today - timedelta(days=25)).isoformat(),
            "end": (today + timedelta(days=5)).isoformat(),
        },
    )
    shown = [e["slug"] for e in calendar.json()]
    assert events["now"].slug in shown and events["old"].slug not in shown


def test_a_past_event_page_still_loads_without_rsvp(api_client, events, signed_in):
    old = events["old"]
    data = api_client.get(f"/api/events/{old.slug}/").json()
    assert data["timing"] == "past"
    assert data["rsvp"]["can_rsvp"] is False and data["rsvp"]["state"] == "past"
    client, _user = signed_in()
    response = client.post(f"/api/events/{old.slug}/rsvp/", {"party_size": 1}, format="json")
    assert response.status_code == 409
    assert response.json() == {"detail": "This event has passed.", "code": "past"}
    assert not RSVP.objects.filter(event=old).exists()


def test_past_event_pages_ask_not_to_be_indexed(client, events, settings, tmp_path):
    (tmp_path / "index.html").write_text("<html><head></head><body></body></html>")
    settings.FRONTEND_DIST = tmp_path
    past = client.get(f"/events/{events['old'].slug}")
    assert past.status_code == 200 and past["X-Robots-Tag"] == "noindex"
    assert "X-Robots-Tag" not in client.get(f"/events/{events['next'].slug}")
