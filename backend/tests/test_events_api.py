from datetime import UTC, timedelta

import pytest
from django.utils import timezone

from apps.events.ics import build_ics, default_title
from apps.events.services import submit_rsvp
from apps.pages.models import SiteSettings

pytestmark = pytest.mark.django_db


def slugs(response):
    """The list is paginated; the calendar is not."""
    data = response.json()
    return [item["slug"] for item in (data["results"] if isinstance(data, dict) else data)]


def test_list_is_upcoming_published_and_ordered(api_client, make_event):
    later = make_event(slug="later", starts_at=timezone.now() + timedelta(days=5))
    sooner = make_event(slug="sooner", starts_at=timezone.now() + timedelta(days=1))
    make_event(slug="draft", is_published=False)
    past = make_event(slug="past", starts_at=timezone.now() + timedelta(days=1))
    past.starts_at = timezone.now() - timedelta(days=2)
    past.ends_at = timezone.now() - timedelta(days=2) + timedelta(hours=3)
    past.save()
    assert slugs(api_client.get("/api/events/")) == [sooner.slug, later.slug]
    assert slugs(api_client.get("/api/events/?past=1")) == ["past"]


def test_event_running_now_still_listed(api_client, make_event):
    make_event(slug="now", starts_at=timezone.now() - timedelta(hours=1))
    assert slugs(api_client.get("/api/events/")) == ["now"]


def test_category_filter(api_client, make_event):
    make_event(slug="edu", category="education")
    make_event(slug="soc", category="social")
    assert slugs(api_client.get("/api/events/?category=education")) == ["edu"]
    assert api_client.get("/api/events/?category=nope").status_code == 400


def test_account_audience_hidden_from_visitors(api_client, signed_in, make_event):
    make_event(slug="open")
    make_event(slug="accounts", audience="account")
    make_event(slug="members", audience="members")
    assert slugs(api_client.get("/api/events/")) == ["open", "members"]
    assert api_client.get("/api/events/accounts/").status_code == 404
    client, _ = signed_in()
    assert "accounts" in slugs(client.get("/api/events/"))


def test_rsvp_states(api_client, signed_in, make_event, make_user):
    full = make_event(slug="full", capacity=1)
    submit_rsvp(make_user(), full, 1)
    closed_full = make_event(slug="no-waitlist", capacity=1, waitlist_enabled=False)
    submit_rsvp(make_user(), closed_full, 1)
    make_event(slug="members", audience="members")
    make_event(slug="soon", rsvp_opens_at=timezone.now() + timedelta(days=1))
    make_event(slug="open")
    states = {
        item["slug"]: item["rsvp"] for item in api_client.get("/api/events/").json()["results"]
    }
    assert states["full"]["state"] == "waitlist"
    assert states["no-waitlist"]["state"] == "full"
    assert states["members"]["state"] == "members_only"
    assert states["soon"]["state"] == "not_open_yet"
    assert states["open"]["state"] == "open"
    assert states["open"]["reason"] == "login_required"
    assert states["open"]["mine"] is None


def test_waitlisted_state_for_self(signed_in, make_event, make_user):
    event = make_event(capacity=1)
    submit_rsvp(make_user(), event, 1)
    client, user = signed_in()
    submit_rsvp(user, event, 1)
    assert client.get(f"/api/events/{event.slug}/").json()["rsvp"]["state"] == "waitlisted"


def test_attendee_count_only_when_enabled(api_client, make_event, make_user):
    hidden = make_event(slug="hidden-count")
    shown = make_event(slug="shown-count", show_attendee_count=True)
    for event in (hidden, shown):
        submit_rsvp(make_user(), event, 2)
    assert api_client.get("/api/events/hidden-count/").json()["attendee_count"] is None
    assert api_client.get("/api/events/shown-count/").json()["attendee_count"] == 2


def test_detail_includes_sanitized_body_and_published_opportunity(api_client, make_event):
    from apps.education.models import Opportunity

    opportunity = Opportunity.objects.create(
        title="Class", slug="class", summary="s", body="b", is_published=True
    )
    event = make_event(
        body='<p onclick="x()">Hello<script>bad()</script></p>', opportunity=opportunity
    )
    data = api_client.get(f"/api/events/{event.slug}/").json()
    assert data["body"] == "<p>Hello</p>"
    assert data["opportunity"] == {"slug": "class", "title": "Class"}
    Opportunity.objects.filter(pk=opportunity.pk).update(is_published=False)
    assert api_client.get(f"/api/events/{event.slug}/").json()["opportunity"] is None


def test_calendar_range(api_client, make_event):
    today = timezone.localdate()
    inside = make_event(slug="inside", starts_at=timezone.now() + timedelta(days=2))
    make_event(slug="outside", starts_at=timezone.now() + timedelta(days=40))
    start = today.isoformat()
    end = (today + timedelta(days=10)).isoformat()
    response = api_client.get(f"/api/events/calendar/?start={start}&end={end}")
    assert slugs(response) == [inside.slug]


@pytest.mark.parametrize(
    "query",
    [
        "",
        "?start=2026-01-01",
        "?start=bad&end=2026-01-02",
        "?start=2026-01-10&end=2026-01-01",
        "?start=2026-01-01&end=2026-06-01",
    ],
)
def test_calendar_validation(api_client, query):
    assert api_client.get(f"/api/events/calendar/{query}").status_code == 400


# Calendar files


def test_ics_default_is_discreet(api_client, make_event):
    SiteSettings.objects.update_or_create(
        pk=1,
        defaults={
            "address_text": "123 Hidden St\nChicago",
            "hours_text": "",
            "tagline": "",
            "contact_email": "a@example.org",
        },
    )
    event = make_event(title="Very Specific Title", location_label="The Library")
    response = api_client.get(f"/api/events/{event.slug}/calendar.ics")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/calendar")
    assert response["Content-Disposition"] == 'attachment; filename="evening.ics"'
    body = response.content.decode()
    assert f"SUMMARY:{default_title()}" in body
    assert default_title() == "Rose - Evening"
    assert "LOCATION:\r\n" in body
    assert "Very Specific Title" not in body
    assert "Hidden St" not in body
    assert "Library" not in body
    assert "google" not in body.lower()


def test_ics_with_details_opt_in(api_client, make_event):
    SiteSettings.objects.update_or_create(
        pk=1,
        defaults={
            "address_text": "123 Hidden St\nChicago",
            "hours_text": "",
            "tagline": "",
            "contact_email": "a@example.org",
        },
    )
    event = make_event(title="Very Specific Title", location_label="The Library")
    body = api_client.get(f"/api/events/{event.slug}/calendar.ics?details=1").content.decode()
    assert "SUMMARY:Very Specific Title" in body
    assert "LOCATION:The Library\\, 123 Hidden St\\, Chicago" in body


def test_ics_structure_and_times(make_event):
    event = make_event()
    body = build_ics(event)
    assert body.startswith("BEGIN:VCALENDAR\r\n")
    assert body.endswith("END:VCALENDAR\r\n")
    assert f"DTSTART:{event.starts_at.astimezone(UTC):%Y%m%dT%H%M%SZ}" in body
    assert all(len(line.encode()) <= 75 for line in body.split("\r\n"))


def test_ics_hidden_for_account_events_when_signed_out(api_client, make_event):
    event = make_event(audience="account")
    assert api_client.get(f"/api/events/{event.slug}/calendar.ics").status_code == 404
