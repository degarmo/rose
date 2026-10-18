import re
from datetime import timedelta

from django.utils import timezone

from .models import Event

DATE_SUFFIX = re.compile(r"-\d{4}-\d{2}-\d{2}$")
COPIED_FIELDS = [
    "title",
    "summary",
    "body",
    "category",
    "location_label",
    "is_published",
    "audience",
    "capacity",
    "waitlist_enabled",
    "max_party_size",
    "show_attendee_count",
    "opportunity_id",
    "hero_image",
    "hero_image_alt",
    "hero_image_faces_visible",
    "hero_image_consent_confirmed",
]
SHIFTED_FIELDS = ["starts_at", "ends_at", "rsvp_opens_at", "rsvp_closes_at"]


def _shift(moment, weeks):
    """Same wall-clock time N weeks later, even across a daylight-saving change."""
    if moment is None:
        return None
    local = timezone.localtime(moment)
    return timezone.make_aware(local.replace(tzinfo=None) + timedelta(weeks=weeks))


def dated_slug(event, starts_at):
    base = DATE_SUFFIX.sub("", event.slug)
    return f"{base}-{timezone.localtime(starts_at):%Y-%m-%d}"


def repeat_weekly(event, weeks):
    """Clone an event forward 1..N weeks. RSVPs are never copied.

    Returns (created, skipped) where skipped lists slugs that already existed.
    """
    created, skipped = [], []
    for week in range(1, weeks + 1):
        values = {name: getattr(event, name) for name in COPIED_FIELDS}
        values.update({name: _shift(getattr(event, name), week) for name in SHIFTED_FIELDS})
        slug = dated_slug(event, values["starts_at"])
        if Event.objects.filter(slug=slug).exists():
            skipped.append(slug)
            continue
        created.append(Event.objects.create(slug=slug, **values))
    return created, skipped
