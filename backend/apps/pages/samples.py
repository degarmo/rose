"""Sample content: realistic, clearly sample, and with no people in it.

One source for `load_staging_samples` (staging, or anywhere with DEBUG on) and `seed_demo`
(development). It makes the evenings of the next six weeks in the club's published
pattern, a featured workshop, six education opportunities, the FAQ, three journal posts and
an announcement. Pictures are drawn locally (demo_media) and saved through the normal image
fields, so they land in whatever storage is set. No accounts, staff profiles, reports,
payments, RSVPs or comments: journal posts carry no author.

Every row made here is listed in SampleRecord (apps.core.samples): the admin lists badge
them "Sample", and `purge()` deletes exactly those rows and their pictures. Running it again
updates the samples in place, puts back any picture missing from storage (a preview's
redeploy loses them) and never touches a row staff made, even with the same slug.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from apps.core.images import variant_name
from apps.core.models import SampleRecord
from apps.core.samples import is_sample, register
from apps.education.models import Opportunity
from apps.events.models import Event
from apps.feed.models import Announcement
from apps.journal.models import Post, PostImage

from .management.commands.demo_media import sample_image
from .models import FAQItem

WEEKS = 6
PICTURE_WIDTH = 1280

OPPORTUNITIES = [
    {
        "slug": "newcomer-orientation",
        "title": "Newcomer Orientation",
        "summary": (
            "Your first step through the door. Meet a few of our volunteers, tour the space "
            "and learn how our community agreements keep everyone comfortable."
        ),
        "body": (
            "Orientation is a relaxed, seated conversation for anyone who is new to us, "
            "whether you are new to community spaces in general or simply new to this one.\n\n"
            "We walk through our community agreements, explain how the house runs on a "
            "typical night, and answer every question you bring. Nothing is expected of you "
            "beyond listening and asking.\n\n"
            "Orientation is required before your first social night. It takes about an hour."
        ),
        "category": Opportunity.Category.CLASS,
        "level": Opportunity.Level.ALL,
        "weeks_ahead": 0,
        "location_label": "The Parlor",
        "cta_label": "Plan your visit",
        "cta_url": "/visit",
        "sort_order": 10,
    },
    {
        "slug": "consent-and-negotiation-foundations",
        "title": "Consent and Negotiation Foundations",
        "summary": (
            "Practical language for asking, offering, pausing and declining, so that every "
            "interaction starts from clarity."
        ),
        "body": (
            "Consent is a conversation, not a checkbox. In this class we practise how to "
            "talk about interests and limits, how to check in along the way, and how to "
            "hear a no gracefully.\n\n"
            "The session mixes short talks with optional paired exercises. You can take "
            "part or simply observe; both are completely welcome.\n\n"
            "Recommended for anyone in their first few months with us."
        ),
        "category": Opportunity.Category.CLASS,
        "level": Opportunity.Level.BEGINNER,
        "weeks_ahead": 1,
        "location_label": "The Library",
        "cta_label": "Ask about this class",
        "cta_url": "/contact",
        "sort_order": 20,
    },
    {
        "slug": "communication-and-aftercare",
        "title": "Communication and Aftercare",
        "summary": (
            "How to look after one another once the evening winds down, and how to talk "
            "honestly about what worked and what did not."
        ),
        "body": (
            "Care does not end when an activity does. This workshop covers emotional "
            "check-ins, recognising when someone needs space, and building a follow-up "
            "habit that strengthens trust.\n\n"
            "We share frameworks from experienced members and leave plenty of time for "
            "questions. Bring a notebook if you like to write things down."
        ),
        "category": Opportunity.Category.WORKSHOP,
        "level": Opportunity.Level.INTERMEDIATE,
        "weeks_ahead": 2,
        "location_label": "The Library",
        "cta_label": "Ask about this workshop",
        "cta_url": "/contact",
        "sort_order": 30,
    },
    {
        "slug": "risk-aware-planning",
        "title": "Risk-Aware Planning",
        "summary": (
            "For experienced members: thinking through risk, preparation and contingency "
            "plans with the same care you bring to everything else."
        ),
        "body": (
            "This advanced session is a structured discussion about assessing risk "
            "honestly, preparing the space and the people involved, and knowing what to do "
            "if plans change.\n\n"
            "It assumes you have completed Consent and Negotiation Foundations or have "
            "equivalent experience. Our education team is glad to talk through whether it "
            "is a good fit."
        ),
        "category": Opportunity.Category.WORKSHOP,
        "level": Opportunity.Level.ADVANCED,
        "weeks_ahead": None,
        "location_label": "The Parlor",
        "cta_label": "Talk to the education team",
        "cta_url": "/contact",
        "sort_order": 40,
    },
    {
        "slug": "mentorship-circle",
        "title": "Mentorship Circle",
        "summary": (
            "Pair with a seasoned member who can answer questions, make introductions and "
            "help you find your footing at your own pace."
        ),
        "body": (
            "Mentorship is informal, friendly and entirely led by you. Mentors are "
            "volunteers who have been part of the community for years and remember what "
            "it was like to be new.\n\n"
            "Circles meet once a month, and you can message your mentor between meetings. "
            "Leave a note through the contact form and we will make a thoughtful match."
        ),
        "category": Opportunity.Category.MENTORSHIP,
        "level": Opportunity.Level.ALL,
        "weeks_ahead": None,
        "location_label": "By arrangement",
        "cta_label": "Request a mentor",
        "cta_url": "/contact",
        "sort_order": 50,
    },
    {
        "slug": "door-and-hosting-team",
        "title": "Join the Door and Hosting Team",
        "summary": (
            "Everything here is run by volunteers. Greet guests, check IDs and help set the "
            "warm, attentive tone people remember."
        ),
        "body": (
            "Hosts are the first faces people see and the reason they feel at ease. "
            "Shifts run three to four hours, and every new volunteer shadows an experienced "
            "host before taking a shift alone.\n\n"
            "We train on welcoming newcomers, checking identification discreetly, and "
            "knowing when and how to step in. No previous experience is needed."
        ),
        "category": Opportunity.Category.VOLUNTEER,
        "level": Opportunity.Level.BEGINNER,
        "weeks_ahead": None,
        "location_label": "Front of house",
        "cta_label": "Volunteer with us",
        "cta_url": "/contact",
        "sort_order": 60,
    },
]

FAQS = [
    (
        "visit-without-membership",
        "Do I need to be a member to visit?",
        "No. Guests are welcome on education nights after completing a newcomer orientation. "
        "Membership adds access to weekend socials and members' events.",
    ),
    (
        "first-visit",
        "What should I bring on my first visit?",
        "A valid, government-issued photo ID showing you are 18 or older. We check it at the "
        "door and do not photograph or copy it.",
    ),
    (
        "dress-code",
        "Is there a dress code?",
        "Come as you are. Most people wear what they would wear to a nice dinner out. Some "
        "themed nights have suggestions, which are always optional.",
    ),
    (
        "taking-part",
        "Will anyone expect me to take part in anything?",
        "Never. Watching, listening and simply being in the room are all completely welcome. "
        "Nobody here will pressure you, and our hosts will step in if anyone tries.",
    ),
    (
        "privacy",
        "How do you protect my privacy?",
        "Photos and recordings are not allowed anywhere in the house. Members are known by a "
        "display name they choose, and we never share your legal name, email or phone number.",
    ),
    (
        "coming-alone",
        "Can I come on my own?",
        "Absolutely. Many people do, especially on their first visit. Let a host know it is "
        "your first time and they will make sure you are introduced around.",
    ),
    (
        "accessibility",
        "Is the space accessible?",
        "The main floor, the Parlor and one restroom are step-free. If you have access needs, "
        "send us a note before you visit and we will make arrangements.",
    ),
    (
        "who-runs-it",
        "Who runs the house?",
        "We are a volunteer-run 501(c)(3) nonprofit. Every host, teacher and board member "
        "gives their time because they care about this community.",
    ),
]

# The Thursday topics, in turn.
EDUCATION_TOPICS = [
    "newcomer-orientation",
    "consent-and-negotiation-foundations",
    "communication-and-aftercare",
    "risk-aware-planning",
]

EDUCATION_BODY = (
    "<p>{summary}</p><p>Doors open at 6:45 pm and the class starts at 7:00 pm; the house "
    "stays open for conversation until midnight. Education nights are alcohol-free.</p>"
    "<p>New here? Orientation runs first, every week, in the parlor.</p>"
)
SOCIAL_BODY = (
    "<p>An unhurried evening of conversation and connection, 9:00 pm to 2:00 am. Volunteer "
    "hosts are on the floor all night and the quiet room is always open.</p>"
    "<p>Bring your own drinks if you like (BYOB); we provide ice, cups and soft drinks. "
    "Please bring a valid photo ID. First time? Tell the host at the door.</p>"
)
WORKSHOP_BODY = (
    "<p>A three-hour afternoon workshop with time for questions and a break halfway. "
    "Seats are limited so everyone can take part in the discussion.</p>"
    "<p>No experience needed beyond an orientation. Alcohol-free.</p>"
)
MEMBERS_BODY = (
    "<p>A quieter evening for members: conversation, house news and a chance to meet the "
    "volunteers who run things. Bring your own drinks if you like (BYOB).</p>"
)

JOURNAL_POSTS = [
    {
        "slug": "autumn-season-opens",
        "caption": (
            "The autumn season of Thursday education nights begins this week. Orientation "
            "runs first, every week, for anyone new: an hour in the parlor, questions "
            "welcome, nothing expected."
        ),
        "images": 2,
        "link": "education",
    },
    {
        "slug": "the-parlor-refresh",
        "caption": (
            "Volunteers spent the weekend repainting the parlor. Deep red, low lamps and more "
            "seating.\n\nThank you to everyone who came with a brush."
        ),
        "images": 1,
        "link": None,
    },
    {
        "slug": "mentorship-circle-returns",
        "caption": (
            "Mentorship circles are back. Leave a note through the contact form and we will "
            "make a thoughtful match."
        ),
        "images": 1,
        "link": "cta",
    },
]

ANNOUNCEMENT = {
    "title": "New here? Start on Thursday",
    "body": (
        "Orientation runs every Thursday at 7 pm before the education night. It takes an "
        "hour and nothing is expected of you."
    ),
    "link_label": "Plan your visit",
    "link_url": "/visit",
    "days": 21,
}


@dataclass
class Report:
    created: dict = field(default_factory=dict)
    updated: dict = field(default_factory=dict)
    pictures: int = 0
    skipped: list = field(default_factory=list)

    def add(self, label, created):
        bucket = self.created if created else self.updated
        bucket[label] = bucket.get(label, 0) + 1

    def lines(self):
        labels = sorted(set(self.created) | set(self.updated))
        for label in labels:
            yield (
                f"{label}: {self.created.get(label, 0)} new, "
                f"{self.updated.get(label, 0)} already there (updated)"
            )
        yield f"Pictures drawn and stored (new or missing from storage): {self.pictures}"
        for line in self.skipped:
            yield f"Skipped: {line}"


def _at(day, hour, minute=0):
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


def _days_ahead(today):
    """The next six weeks of dates, starting tomorrow."""
    return [today + timedelta(days=offset) for offset in range(1, WEEKS * 7 + 1)]


def _first(days, weekday, week):
    """The given weekday (0 = Monday) in the given week (0 = the first seven days)."""
    return next(day for day in days[week * 7 : week * 7 + 7] if day.weekday() == weekday)


def event_plan(today: date):
    """The sample evenings of the next six weeks, as field values keyed by slug."""
    days = _days_ahead(today)
    topics = {item["slug"]: item for item in OPPORTUNITIES}
    plan = []
    thursdays = [day for day in days if day.weekday() == 3]
    for index, day in enumerate(thursdays):
        topic = topics[EDUCATION_TOPICS[index % len(EDUCATION_TOPICS)]]
        starts = _at(day, 19)
        plan.append(
            {
                "slug": f"education-night-{day:%Y-%m-%d}",
                "title": f"Education Night: {topic['title']}",
                "summary": topic["summary"],
                "body": EDUCATION_BODY.format(summary=topic["summary"]),
                "category": Event.Category.EDUCATION,
                "starts_at": starts,
                "ends_at": starts + timedelta(hours=5),
                "location_label": topic["location_label"],
                "capacity": 40,
                "show_attendee_count": True,
                "opportunity_slug": topic["slug"],
            }
        )
    for day in days:
        if day.weekday() not in (4, 5):
            continue
        name = "Friday" if day.weekday() == 4 else "Saturday"
        starts = _at(day, 21)
        plan.append(
            {
                "slug": f"{name.lower()}-social-{day:%Y-%m-%d}",
                "title": f"{name} Social",
                "summary": "An unhurried evening of conversation, with hosts on the floor. BYOB.",
                "body": SOCIAL_BODY,
                "category": Event.Category.SOCIAL,
                "starts_at": starts,
                "ends_at": starts + timedelta(hours=5),
                "location_label": "Main floor",
                "capacity": 80,
            }
        )
    workshop_day = _first(days, 5, 1)
    starts = _at(workshop_day, 13)
    plan.append(
        {
            "slug": f"aftercare-workshop-{workshop_day:%Y-%m-%d}",
            "title": "Workshop: Communication and Aftercare",
            "summary": topics["communication-and-aftercare"]["summary"],
            "body": WORKSHOP_BODY,
            "category": Event.Category.WORKSHOP,
            "starts_at": starts,
            "ends_at": starts + timedelta(hours=3),
            "location_label": "The Library",
            "capacity": 20,
            "opportunity_slug": "communication-and-aftercare",
            "featured": True,
        }
    )
    members_day = _first(days, 6, 2)
    starts = _at(members_day, 19)
    plan.append(
        {
            "slug": f"members-night-{members_day:%Y-%m-%d}",
            "title": "Members' Night",
            "summary": "A quieter evening for members: conversation and house news.",
            "body": MEMBERS_BODY,
            "category": Event.Category.MEMBER_NIGHT,
            "audience": Event.Audience.MEMBERS,
            "starts_at": starts,
            "ends_at": starts + timedelta(hours=4),
            "location_label": "The Parlor",
        }
    )
    return plan


class Loader:
    def __init__(self, report, with_pictures, adopt):
        self.report = report
        self.with_pictures = with_pictures
        self.adopt = adopt
        self.picture_index = 0

    def upsert(self, model, label, lookup, values, fallback=None):
        """Create or update a sample. A row staff made with the same key is left alone,
        except when adopting (seed_demo, whose older runs made these rows unregistered).
        `fallback` finds such an older row by another field when the key misses."""
        obj = model.objects.filter(**lookup).first()
        if obj is None and self.adopt and fallback:
            obj = model.objects.filter(**fallback).first()
            if obj is not None:
                for name, value in lookup.items():
                    setattr(obj, name, value)
        if obj is not None and not is_sample(obj) and not self.adopt:
            key = ", ".join(str(value) for value in lookup.values())
            self.report.skipped.append(f"{label} {key} exists and was not made here; left alone")
            return None
        created = obj is None
        if created:
            obj = model(**lookup)
        for name, value in values.items():
            setattr(obj, name, value)
        obj.save()
        register(obj)
        self.report.add(label, created)
        return obj

    def picture(self, obj, field):
        """Draw and save a picture when the row has none, or its file is gone from storage."""
        self.picture_index += 1
        current = getattr(obj, field)
        if current and current.storage.exists(current.name):
            return
        self.report.pictures += 1
        if not self.with_pictures:
            return
        sample = sample_image(self.picture_index, width=PICTURE_WIDTH)
        setattr(obj, field, sample.file)
        setattr(obj, f"{field}_alt", sample.alt)
        setattr(obj, f"{field}_faces_visible", False)
        setattr(obj, f"{field}_consent_confirmed", False)
        obj.save()


def load(today=None, with_pictures=True, adopt=False):
    """Make or update every sample. Returns the Report. `adopt` (seed_demo only) takes over
    rows with the same key that earlier demo seeds made, instead of leaving them alone."""
    today = today or timezone.localdate()
    loader = Loader(Report(), with_pictures, adopt)
    with transaction.atomic():
        opportunities = _load_opportunities(loader, today)
        events = _load_events(loader, today, opportunities)
        _load_faqs(loader)
        _load_journal(loader, events)
        _load_announcement(loader)
    return loader.report


def _load_opportunities(loader, today):
    found = {}
    for item in OPPORTUNITIES:
        values = {k: v for k, v in item.items() if k not in ("slug", "weeks_ahead")}
        weeks = item["weeks_ahead"]
        if weeks is not None:
            thursday = today + timedelta(days=(3 - today.weekday()) % 7 or 7)
            values["starts_at"] = _at(thursday + timedelta(weeks=weeks), 19)
        else:
            values["starts_at"] = None
        values["is_published"] = True
        opportunity = loader.upsert(
            Opportunity, "Education opportunities", {"slug": item["slug"]}, values
        )
        if opportunity is not None:
            loader.picture(opportunity, "hero_image")
            found[item["slug"]] = opportunity
    return found


def _load_events(loader, today, opportunities):
    events = []
    for item in event_plan(today):
        values = {
            k: v for k, v in item.items() if k not in ("slug", "opportunity_slug", "featured")
        }
        values["is_published"] = True
        values["opportunity"] = opportunities.get(item.get("opportunity_slug"))
        event = loader.upsert(Event, "Events", {"slug": item["slug"]}, values)
        if event is None:
            continue
        loader.picture(event, "hero_image")
        if item.get("featured"):
            _feature(loader, event)
        events.append(event)
    return events


def _feature(loader, event):
    """Feature the sample workshop, unless staff have featured an event of their own."""
    current = Event.objects.featured().exclude(pk=event.pk).first()
    if current is not None and not is_sample(current):
        loader.report.skipped.append(
            f"Featuring {event.slug}: {current.slug} is featured by staff; left as it is"
        )
        return
    if not event.is_featured:
        event.is_featured = True
        event.save()


def _load_faqs(loader):
    for index, (slug, question, answer) in enumerate(FAQS, start=1):
        loader.upsert(
            FAQItem,
            "FAQ questions",
            {"slug": slug},
            {
                "question": question,
                "answer": answer,
                "sort_order": index * 10,
                "is_published": True,
            },
            fallback={"question": question, "slug": None},
        )


def _load_journal(loader, events):
    education = next((e for e in events if e.category == Event.Category.EDUCATION), None)
    now = timezone.now()
    for index, item in enumerate(JOURNAL_POSTS):
        post = loader.upsert(
            Post,
            "Journal posts",
            {"slug": item["slug"]},
            {
                "caption": item["caption"],
                "published_at": now - timedelta(days=index * 5, hours=index),
                "is_published": True,
                "author": None,
                "event": education if item["link"] == "education" else None,
                "cta_label": "Request a mentor" if item["link"] == "cta" else "",
                "cta_url": "/contact" if item["link"] == "cta" else "",
            },
        )
        if post is None:
            continue
        images = list(post.images.all())
        for order in range(item["images"]):
            image = images[order] if order < len(images) else PostImage(post=post, sort_order=order)
            loader.picture(image, "image")


def _load_announcement(loader):
    now = timezone.now()
    loader.upsert(
        Announcement,
        "Announcements",
        {"title": ANNOUNCEMENT["title"]},
        {
            "body": ANNOUNCEMENT["body"],
            "link_label": ANNOUNCEMENT["link_label"],
            "link_url": ANNOUNCEMENT["link_url"],
            "starts_at": now,
            "ends_at": now + timedelta(days=ANNOUNCEMENT["days"]),
            "is_published": True,
        },
    )


# Purge

PICTURE_FIELDS = {
    Event: "hero_image",
    Opportunity: "hero_image",
    PostImage: "image",
}


def _delete_picture(obj, field_name):
    file = getattr(obj, field_name)
    if not file:
        return
    storage, name = file.storage, file.name
    widths = getattr(obj._meta.get_field(field_name), "variant_widths", ())
    for target in [name, *(variant_name(name, width) for width in widths)]:
        if storage.exists(target):
            storage.delete(target)


def purge():
    """Delete every sample row and its pictures; nothing else. Returns {label: count}."""
    removed = {}
    records = SampleRecord.objects.select_related("content_type")
    with transaction.atomic():
        for record in records:
            model = record.content_type.model_class()
            obj = model.objects.filter(pk=record.object_id).first() if model else None
            if obj is not None:
                if isinstance(obj, Post):
                    for image in obj.images.all():
                        _delete_picture(image, "image")
                elif model in PICTURE_FIELDS:
                    _delete_picture(obj, PICTURE_FIELDS[model])
                obj.delete()
                label = model._meta.verbose_name_plural
                removed[label] = removed.get(label, 0) + 1
        records.delete()
    return removed


def sample_counts():
    """{verbose name plural: count} of the samples now in the database."""
    counts = {}
    for record in SampleRecord.objects.values("content_type").distinct():
        content_type = ContentType.objects.get_for_id(record["content_type"])
        model = content_type.model_class()
        if model is None:
            continue
        ids = SampleRecord.objects.filter(content_type=content_type).values("object_id")
        counts[model._meta.verbose_name_plural] = model.objects.filter(pk__in=ids).count()
    return counts
