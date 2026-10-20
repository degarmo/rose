"""Club content inside the member app: journal posts shown as the club's own account in
the home feed, and the stories tray (upcoming events, journal posts, announcements).

All of it is staff-made and already public or member-visible elsewhere; nothing here
reveals anything about other members.
"""

import base64
import binascii
import json
from datetime import datetime, timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.branding import site_name
from apps.core.consent_images import consent_image_payload
from apps.events.models import Event
from apps.journal.models import Post as JournalPost
from apps.journal.serializers import PostSerializer as JournalPostSerializer

from .models import Announcement, FeedLike, SavedPost, StorySeen
from .serializers import FeedPostSerializer, posted
from .visibility import feed_posts

HOME_PAGE_SIZE = 10
JOURNAL_STORY_DAYS = 14
STORY_LIMIT = 6
STORY_KEYS_MAX = 50
STORY_KEY_MAX_LENGTH = 80


def club_handle():
    """The club's account in the feed carries the site's name (apps.core.branding)."""
    return site_name()


# The home feed


def club_post_payload(post, request):
    """A journal post in the same shape as a member post, authored by the club."""
    data = JournalPostSerializer(post, context={"request": request}).data
    if data["event"]:
        link = {"label": "RSVP", "url": f"/events/{data['event']['slug']}"}
    elif data["cta"]:
        link = data["cta"]
    else:
        link = {"label": "Read on the website", "url": f"/journal/{post.slug}"}
    return {
        "kind": "club",
        "id": f"club-{post.slug}",
        "slug": post.slug,
        "author": {"handle": club_handle(), "avatar": None},
        "caption_html": data["caption_html"],
        "posted": posted(post.published_at),
        "images": [
            {
                "id": f"{post.slug}-{index}",
                "url": image["url"],
                "srcset": image["srcset"],
                "alt": image["alt"],
                "width": image["width"],
                "height": image["height"],
            }
            for index, image in enumerate(data["images"])
        ],
        "link": link,
    }


def decode_cursor(raw):
    """{"m": [iso, [public ids]], "c": [iso, [slugs]]}: where each source left off.

    Positions hold a timestamp and the items already shown at exactly that time, so
    no database id ever reaches the browser.
    """
    if not raw:
        return {}
    try:
        data = json.loads(base64.urlsafe_b64decode(raw.encode()).decode())
        cursor = {}
        for source in ("m", "c"):
            if source in data:
                moment, seen = data[source]
                cursor[source] = (datetime.fromisoformat(moment), [str(item) for item in seen])
        return cursor
    except (ValueError, TypeError, KeyError, binascii.Error, json.JSONDecodeError) as error:
        raise ValidationError({"cursor": "Invalid cursor."}) from error


def encode_cursor(cursor):
    data = {source: [moment.isoformat(), seen] for source, (moment, seen) in cursor.items()}
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()


def _after(queryset, field, id_field, position):
    if position is None:
        return queryset
    moment, seen = position
    return queryset.filter(
        Q(**{f"{field}__lt": moment}) | (Q(**{field: moment}) & ~Q(**{f"{id_field}__in": seen}))
    )


def _advance(position, moment, item_id):
    if position is not None and position[0] == moment:
        return (moment, [*position[1], item_id])
    return (moment, [item_id])


def home_page(request, tab, raw_cursor):
    """Member posts and club journal posts, newest first, interleaved by date."""
    viewer = request.user
    cursor = decode_cursor(raw_cursor)
    size = HOME_PAGE_SIZE
    members = list(
        _after(feed_posts(viewer, tab), "created_at", "public_id", cursor.get("m"))
        .select_related("author", "author__profile")
        .prefetch_related("images")
        .order_by("-created_at", "-pk")[: size + 1]
    )
    club = list(
        _after(JournalPost.objects.live(), "published_at", "slug", cursor.get("c"))
        .select_related("event")
        .prefetch_related("images")
        .order_by("-published_at", "-pk")[: size + 1]
    )
    merged = sorted(
        [(post.created_at, "m", post) for post in members]
        + [(post.published_at, "c", post) for post in club],
        key=lambda row: row[0],
        reverse=True,
    )
    shown = merged[:size]

    liked = set(
        FeedLike.objects.filter(user=viewer, post__in=members).values_list("post_id", flat=True)
    )
    saved = set(
        SavedPost.objects.filter(user=viewer, post__in=members).values_list("post_id", flat=True)
    )
    context = {"viewer": viewer, "liked_ids": liked, "saved_ids": saved}
    results = []
    for moment, source, post in shown:
        if source == "m":
            results.append({"kind": "member", **FeedPostSerializer(post, context=context).data})
            cursor["m"] = _advance(cursor.get("m"), moment, post.public_id)
        else:
            results.append(club_post_payload(post, request))
            cursor["c"] = _advance(cursor.get("c"), moment, post.slug)

    next_url = None
    if len(merged) > size:
        query = request.GET.copy()
        query["cursor"] = encode_cursor(cursor)
        next_url = request.build_absolute_uri(f"{request.path}?{query.urlencode()}")
    return {"next": next_url, "previous": None, "results": results}


# Stories


def _event_item(event, request):
    return {
        "key": f"event:{event.slug}",
        "kind": "event",
        "title": event.title,
        "text": event.summary,
        "starts_at": event.starts_at.isoformat(),
        "image": consent_image_payload(event, "hero_image", request),
        "link": {"label": "RSVP", "url": f"/events/{event.slug}"},
    }


def _journal_item(post, request):
    images = [
        payload
        for payload in (
            consent_image_payload(image, "image", request) for image in post.images.all()
        )
        if payload
    ]
    return {
        "key": f"journal:{post.slug}",
        "kind": "journal",
        "title": "From the journal",
        # Captions are plain text already; line breaks fold into spaces for the story.
        "text": " ".join(post.caption.split())[:200],
        "starts_at": None,
        "image": images[0] if images else None,
        "link": {"label": "Learn more", "url": f"/journal/{post.slug}"},
    }


def _announcement_item(announcement):
    link = None
    if announcement.link_label and announcement.link_url:
        link = {"label": announcement.link_label, "url": announcement.link_url}
    return {
        "key": f"announcement:{announcement.pk}",
        "kind": "announcement",
        "title": announcement.title,
        "text": announcement.body,
        "starts_at": None,
        "image": None,
        "link": link,
    }


def stories(request, now=None):
    """Staff-made story circles, each marked seen once the viewer has opened every item."""
    viewer = request.user
    now = now or timezone.now()
    end_of_today = timezone.localtime(now).replace(
        hour=23, minute=59, second=59, microsecond=999999
    )
    upcoming = (
        Event.objects.visible_to(viewer)
        .upcoming(now)
        .filter(starts_at__lte=now + timedelta(days=7))
    ).order_by("starts_at")
    tonight = [event for event in upcoming if event.starts_at <= end_of_today][:STORY_LIMIT]
    week = [event for event in upcoming if event.starts_at > end_of_today][:STORY_LIMIT]
    journal = (
        JournalPost.objects.live(now)
        .filter(published_at__gte=now - timedelta(days=JOURNAL_STORY_DAYS))
        .prefetch_related("images")
        .order_by("-published_at")[:STORY_LIMIT]
    )
    notices = Announcement.objects.filter(
        is_published=True, starts_at__lte=now, ends_at__gt=now
    ).order_by("-starts_at")[:STORY_LIMIT]

    groups = [
        ("tonight", "Tonight", [_event_item(event, request) for event in tonight]),
        ("this-week", "This week", [_event_item(event, request) for event in week]),
        ("journal", "Journal", [_journal_item(post, request) for post in journal]),
        ("news", "News", [_announcement_item(notice) for notice in notices]),
    ]
    keys = [item["key"] for _, _, items in groups for item in items]
    seen = set(StorySeen.objects.filter(user=viewer, key__in=keys).values_list("key", flat=True))
    results = []
    for group_id, title, items in groups:
        if not items:
            continue
        for item in items:
            item["seen"] = item["key"] in seen
        results.append(
            {
                "id": group_id,
                "title": title,
                "seen": all(item["seen"] for item in items),
                "items": items,
            }
        )
    return results


def clean_story_keys(raw):
    if not isinstance(raw, list) or not raw or len(raw) > STORY_KEYS_MAX:
        raise ValidationError({"keys": "Send a list of story keys."})
    keys = []
    for key in raw:
        if not isinstance(key, str) or not key or len(key) > STORY_KEY_MAX_LENGTH:
            raise ValidationError({"keys": "Invalid story key."})
        keys.append(key)
    return keys
