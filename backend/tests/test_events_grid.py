"""The public Events grid's data: 15 a page with a count, card images with their sizes,
fallbacks, alt text, and a list that costs the same number of queries however long."""

import importlib
from datetime import timedelta
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.core.images import variant_name
from apps.events.models import HERO_WIDTHS, Event

pytestmark = pytest.mark.django_db

LIST = "/api/events/"


def photo(width=1600, height=1200):
    buffer = BytesIO()
    Image.new("RGB", (width, height), (180, 120, 140)).save(buffer, format="JPEG")
    return SimpleUploadedFile("hero.jpg", buffer.getvalue(), content_type="image/jpeg")


@pytest.fixture
def many(make_event):
    now = timezone.now()
    return [
        make_event(slug=f"evening-{n:02d}", starts_at=now + timedelta(days=n + 1))
        for n in range(20)
    ]


def test_fifteen_a_page_with_a_count(api_client, many):
    first = api_client.get(LIST).json()
    assert first["count"] == 20 and len(first["results"]) == 15
    assert [item["slug"] for item in first["results"]] == [e.slug for e in many[:15]]
    assert first["next"].endswith("?page=2") and first["previous"] is None
    second = api_client.get(LIST, {"page": 2}).json()
    assert [item["slug"] for item in second["results"]] == [e.slug for e in many[15:]]
    assert second["next"] is None
    assert len(api_client.get(LIST, {"page_size": 50}).json()["results"]) == 20
    assert api_client.get(LIST, {"page_size": 500}).json()["count"] == 20
    assert api_client.get(LIST, {"page": 3}).status_code == 404


def test_only_upcoming_and_happening_now_soonest_first(api_client, make_event):
    now = timezone.now()
    make_event(slug="over", starts_at=now - timedelta(days=1))
    make_event(slug="later", starts_at=now + timedelta(days=4))
    make_event(slug="on-now", starts_at=now - timedelta(hours=1))
    results = api_client.get(LIST).json()["results"]
    assert [item["slug"] for item in results] == ["on-now", "later"]
    assert {item["timing"] for item in results} == {"happening", "upcoming"}


def test_a_picture_gets_webp_copies_for_srcset(api_client, make_event, settings):
    event = make_event(slug="pictured", hero_image=photo(), hero_image_alt="The hall, lit")
    event.refresh_from_db()
    assert (event.hero_image_width, event.hero_image_height) == (1600, 1200)
    for width in HERO_WIDTHS:
        assert event.hero_image.storage.exists(variant_name(event.hero_image.name, width))
    image = api_client.get(LIST).json()["results"][0]["hero_image"]
    assert image["alt"] == "The hall, lit"
    assert (image["width"], image["height"]) == (1600, 1200)
    widths = [entry.rsplit(" ", 1)[1] for entry in image["srcset"].split(", ")]
    assert widths == ["400w", "800w", "1200w", "1600w"]
    assert all(".webp" in entry for entry in image["srcset"].split(", "))


def test_a_small_picture_is_never_scaled_up(make_event):
    event = make_event(hero_image=photo(600, 450), hero_image_alt="Small")
    event.refresh_from_db()
    storage = event.hero_image.storage
    assert storage.exists(variant_name(event.hero_image.name, 400))
    assert not storage.exists(variant_name(event.hero_image.name, 800))


def test_no_picture_or_unconsented_faces_fall_back_to_the_category(api_client, make_event):
    make_event(slug="plain", category="workshop", starts_at=timezone.now() + timedelta(days=1))
    make_event(
        slug="faces",
        category="social",
        starts_at=timezone.now() + timedelta(days=2),
        hero_image=photo(),
        hero_image_alt="A crowd",
        hero_image_faces_visible=True,
    )
    results = {item["slug"]: item for item in api_client.get(LIST).json()["results"]}
    assert results["plain"]["hero_image"] is None
    assert results["plain"]["image_fallback"] == "workshop"
    assert results["faces"]["hero_image"] is None
    assert results["faces"]["image_fallback"] == "social"
    detail = api_client.get(f"{LIST}faces/").json()
    assert detail["hero_image"] is None


def test_missing_alt_text_falls_back_to_the_title(api_client, make_event):
    make_event(slug="no-alt", title="Spring social", hero_image=photo(), hero_image_alt="")
    image = api_client.get(LIST).json()["results"][0]["hero_image"]
    assert image["alt"] == "Spring social"


def test_the_summary_is_plain_text(api_client, make_event):
    make_event(summary="<b>Bring</b> a friend<script>x()</script>")
    assert api_client.get(LIST).json()["results"][0]["summary"] == "Bring a friendx()"


def test_the_admin_warns_about_a_picture_without_alt_text(admin_client, make_event):
    event = make_event(hero_image=photo(), hero_image_alt="")
    page = admin_client.get(reverse("admin:events_event_change", args=(event.pk,)))
    assert "has no alt text" in page.content.decode()
    event.hero_image_alt = "The hall"
    event.save()
    page = admin_client.get(reverse("admin:events_event_change", args=(event.pk,)))
    assert "has no alt text" not in page.content.decode()


def test_older_pictures_get_their_copies_from_the_migration(make_event):
    from django.apps import apps

    event = make_event(hero_image=photo(), hero_image_alt="Old")
    storage, name = event.hero_image.storage, event.hero_image.name
    for width in HERO_WIDTHS:
        storage.delete(variant_name(name, width))
    migration = importlib.import_module("apps.events.migrations.0008_make_hero_variants")
    migration.make_variants(apps, None)
    for width in HERO_WIDTHS:
        assert storage.exists(variant_name(name, width))


def queries_for(client, count, make_event, **kwargs):
    Event.objects.all().delete()
    now = timezone.now()
    for n in range(count):
        make_event(starts_at=now + timedelta(days=n + 1), **kwargs)
    with CaptureQueriesContext(connection) as captured:
        assert client.get(LIST).status_code == 200
    return len(captured)


@pytest.mark.parametrize("audience", ["public", "members"])
def test_the_list_costs_the_same_however_many_events(
    api_client, signed_in, make_event, make_membership, audience
):
    assert queries_for(api_client, 2, make_event, audience=audience) == queries_for(
        api_client, 12, make_event, audience=audience
    )
    client, member = signed_in()
    make_membership(user=member)
    assert queries_for(client, 2, make_event, audience=audience) == queries_for(
        client, 12, make_event, audience=audience
    )


# The featured event


def test_only_one_event_is_featured_at_a_time(make_event):
    from django.db import IntegrityError, transaction

    first = make_event(slug="first", is_featured=True)
    second = make_event(slug="second", is_featured=True)
    first.refresh_from_db()
    assert not first.is_featured and second.is_featured
    with pytest.raises(IntegrityError), transaction.atomic():
        Event.objects.filter(pk=first.pk).update(is_featured=True)


def test_the_admin_names_the_event_losing_the_feature_and_asks_first(make_event):
    from apps.events.admin import EventAdminForm

    current = make_event(slug="current", title="Friday Social", is_featured=True)
    other = make_event(slug="other", title="Saturday Social")
    form = EventAdminForm(data={"is_featured": "on"}, instance=other)
    assert form.fields["take_feature"].help_text.startswith("Featured now: Friday Social")
    assert not form.is_valid()
    assert "Friday Social" in form.errors["is_featured"][0]
    confirmed = EventAdminForm(data={"is_featured": "on", "take_feature": "on"}, instance=other)
    assert confirmed.is_valid(), confirmed.errors
    confirmed.save()
    current.refresh_from_db()
    assert not current.is_featured and Event.objects.get(pk=other.pk).is_featured


def test_featuring_ends_by_itself_once_the_event_is_over(api_client, make_event):
    now = timezone.now()
    event = make_event(slug="soon", starts_at=now + timedelta(days=1), is_featured=True)
    assert api_client.get(f"{LIST}featured/").json()["event"]["slug"] == "soon"
    event.starts_at = now - timedelta(days=2)
    event.ends_at = event.starts_at + timedelta(hours=3)
    event.save()
    assert list(Event.objects.featured()) == []
    assert api_client.get(f"{LIST}featured/").json() == {"event": None}
    # An expired feature needs no confirmation to replace.
    from apps.events.admin import EventAdminForm

    other = make_event(slug="next")
    assert EventAdminForm(data={"is_featured": "on"}, instance=other).is_valid()


def test_the_featured_event_is_not_repeated_in_the_grid(api_client, many):
    featured = many[3]
    featured.is_featured = True
    featured.save()
    page = api_client.get(LIST).json()
    assert page["count"] == 19 and len(page["results"]) == 15
    assert featured.slug not in [item["slug"] for item in page["results"]]
    assert api_client.get(f"{LIST}featured/").json()["event"]["slug"] == featured.slug


def test_a_category_that_leaves_the_featured_event_out_hides_it(api_client, make_event):
    make_event(slug="star", category="social", is_featured=True)
    make_event(slug="class", category="education")
    assert (
        api_client.get(f"{LIST}featured/", {"category": "social"}).json()["event"]["slug"] == "star"
    )
    assert api_client.get(f"{LIST}featured/", {"category": "education"}).json() == {"event": None}
    assert [
        e["slug"] for e in api_client.get(LIST, {"category": "education"}).json()["results"]
    ] == ["class"]


def test_copies_never_take_the_feature(make_event):
    from apps.events.recurrence import duplicate

    event = make_event(is_featured=True)
    copy = duplicate(event, event.starts_at + timedelta(days=7))
    assert not copy.is_featured and Event.objects.get(pk=event.pk).is_featured
