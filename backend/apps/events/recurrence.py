"""Copying events: "Repeat weekly" on the main list, "Duplicate as new event" in the archive.

A copy takes everything the event says about itself (words, picture, audience, capacity,
tags, its RSVP window relative to the start) and never its RSVPs, final counts or slug.
"""

import re
from datetime import timedelta

from django.utils import timezone

from .models import Event

DATE_SUFFIX = re.compile(r"-\d{4}-\d{2}-\d{2}(-\d+)?$")
SHIFTED_FIELDS = ["starts_at", "ends_at", "rsvp_opens_at", "rsvp_closes_at"]
# What a copy never takes: its identity, the times (shifted instead) and what happened.
NOT_COPIED = {
    "id",
    "slug",
    *SHIFTED_FIELDS,
    "is_private_hold",
    "is_featured",
    "final_going_count",
    "final_checked_in_count",
    "rsvps_purged_at",
    "created_at",
    "updated_at",
}


def _shift(moment, weeks):
    """Same wall-clock time N weeks later, even across a daylight-saving change."""
    if moment is None:
        return None
    local = timezone.localtime(moment)
    return timezone.make_aware(local.replace(tzinfo=None) + timedelta(weeks=weeks))


def dated_slug(event, starts_at):
    base = DATE_SUFFIX.sub("", event.slug)
    return f"{base}-{timezone.localtime(starts_at):%Y-%m-%d}"


def _copy(event, slug, shift, **overrides):
    values = {
        field.attname: getattr(event, field.attname)
        for field in Event._meta.concrete_fields
        if field.name not in NOT_COPIED
    }
    values.update({name: shift(getattr(event, name)) for name in SHIFTED_FIELDS})
    values.update(overrides)
    copy = Event.objects.create(slug=slug, **values)
    copy.access_tags.set(event.access_tags.all())
    return copy


def repeat_weekly(event, weeks):
    """Clone an event forward 1..N weeks. RSVPs are never copied.

    Returns (created, skipped) where skipped lists slugs that already existed.
    """
    created, skipped = [], []
    for week in range(1, weeks + 1):
        starts_at = _shift(event.starts_at, week)
        slug = dated_slug(event, starts_at)
        if Event.objects.filter(slug=slug).exists():
            skipped.append(slug)
            continue
        created.append(_copy(event, slug, lambda moment, week=week: _shift(moment, week)))
    return created, skipped


def duplicate(event, starts_at):
    """A new, unpublished draft of the event starting at `starts_at`, its end and RSVP window
    moved by the same amount."""
    moved = starts_at - event.starts_at
    slug = base = dated_slug(event, starts_at)
    number = 2
    while Event.objects.filter(slug=slug).exists():
        slug = f"{base}-{number}"
        number += 1
    return _copy(
        event,
        slug,
        lambda moment: None if moment is None else moment + moved,
        is_published=False,
    )
