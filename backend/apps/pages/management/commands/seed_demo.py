"""Load placeholder content so every page has something real to show.

Safe to run repeatedly: rows are matched on slug, question or email and
updated. Demo account passwords are regenerated on every run and printed
only when DEBUG is on.
"""

import secrets
from datetime import datetime, time, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.education.models import Opportunity
from apps.events.models import RSVP, Event
from apps.journal.models import Post, PostImage
from apps.pages.models import FAQItem, SiteSettings

from .demo_media import gradient_image

SITE_SETTINGS = {
    "tagline": "A members' house for learning, connection and consent-first community.",
    "hours_text": (
        "Thursday education nights: 7:00 pm to 10:00 pm\n"
        "Friday and Saturday socials: 9:00 pm to 1:00 am\n"
        "Closed Sunday through Wednesday"
    ),
    "address_text": (
        "West Loop, Chicago, Illinois\nThe street address is shared with confirmed visitors."
    ),
    "directions_text": (
        "A short walk from the nearest L station, with street parking that is usually easy "
        "after 7 pm. The entrance is discreet and unmarked; your host will share exact "
        "directions with your confirmation."
    ),
    "contact_email": "hello@example.org",
    "quick_exit_url": "",
}

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
        "Do I need to be a member to visit?",
        "No. Guests are welcome on education nights after completing a newcomer orientation. "
        "Membership adds access to weekend socials and members' events.",
    ),
    (
        "What should I bring on my first visit?",
        "A valid, government-issued photo ID showing you are 18 or older. We check it at the "
        "door and do not photograph or copy it.",
    ),
    (
        "Is there a dress code?",
        "Come as you are. Most people wear what they would wear to a nice dinner out. Some "
        "themed nights have suggestions, which are always optional.",
    ),
    (
        "Will anyone expect me to take part in anything?",
        "Never. Watching, listening and simply being in the room are all completely welcome. "
        "Nobody here will pressure you, and our hosts will step in if anyone tries.",
    ),
    (
        "How do you protect my privacy?",
        "Photos and recordings are not allowed anywhere in the house. Members are known by a "
        "display name they choose, and we never share your legal name, email or phone number.",
    ),
    (
        "Can I come on my own?",
        "Absolutely. Many people do, especially on their first visit. Let a host know it is "
        "your first time and they will make sure you are introduced around.",
    ),
    (
        "Is the space accessible?",
        "The main floor, the Parlor and one restroom are step-free. If you have access needs, "
        "send us a note before you visit and we will make arrangements.",
    ),
    (
        "Who runs the house?",
        "We are a volunteer-run 501(c)(3) nonprofit. Every host, teacher and board member "
        "gives their time because they care about this community.",
    ),
]


def upcoming_weekday(weekday, weeks_ahead, at):
    """The next given weekday (0 = Monday) after today, plus N weeks, at a local time."""
    today = timezone.localdate()
    days_until = (weekday - today.weekday()) % 7 or 7
    date = today + timedelta(days=days_until + 7 * weeks_ahead)
    return timezone.make_aware(datetime.combine(date, at))


def upcoming_thursday_evening(weeks_ahead):
    return upcoming_weekday(3, weeks_ahead, time(19, 0))


EDUCATION_NIGHT_TOPICS = [
    "newcomer-orientation",
    "consent-and-negotiation-foundations",
    "communication-and-aftercare",
    "risk-aware-planning",
]

SOCIAL_BODY = (
    "<p>An unhurried evening of conversation and connection. Volunteer hosts are on the "
    "floor all night, the bar serves soft drinks and mocktails, and the quiet room is "
    "always open.</p><p>Please bring a valid photo ID. First time? Let the host at the "
    "door know and they will introduce you around.</p>"
)

DEMO_USERS = [
    ("demo.verified@example.org", "demo_verified", True),
    ("demo.unverified@example.org", "demo_unverified", False),
]

JOURNAL_POSTS = [
    (
        "autumn-season-opens",
        2,
        "The autumn season of Thursday education nights begins this "
        "week. Orientation runs first, every week, for anyone new.",
        "orientation",
    ),
    (
        "the-parlor-refresh",
        3,
        "Our volunteers spent the weekend repainting the parlor. "
        "Deep red, low lamps, more seating.\n\nThank you to everyone who came with a brush.",
        None,
    ),
    (
        "mentorship-circle-returns",
        1,
        "Mentorship circles are back. Leave a note through the "
        "contact form and we will make a thoughtful match.",
        "cta",
    ),
    (
        "friday-social",
        1,
        "Fridays are for unhurried conversation. Hosts on the floor all "
        "night, quiet room always open.",
        "social",
    ),
    (
        "volunteer-thanks",
        2,
        "A thank you to the door team, who welcomed more first-time "
        "guests this month than ever before.",
        None,
    ),
    (
        "consent-class-recap",
        1,
        "Last week's consent class filled the library. Notes and "
        "reading suggestions are available at the front desk.",
        None,
    ),
    ("candlelight", 1, "Saturday, after dark.", "saturday"),
    (
        "accessibility-update",
        2,
        "The main floor, the parlor and one restroom are step-free. "
        "Tell us what else would help: https://example.org/access",
        None,
    ),
    ("member-night-preview", 1, "Member night is coming. Members, watch your inbox.", "members"),
]


class Command(BaseCommand):
    help = "Load placeholder education opportunities, FAQs and site settings."

    @transaction.atomic
    def handle(self, *args, **options):
        site_settings = SiteSettings.load()
        for field, value in SITE_SETTINGS.items():
            setattr(site_settings, field, value)
        site_settings.save()

        for item in OPPORTUNITIES:
            data = dict(item)
            weeks_ahead = data.pop("weeks_ahead")
            slug = data.pop("slug")
            data["starts_at"] = (
                upcoming_thursday_evening(weeks_ahead) if weeks_ahead is not None else None
            )
            data["is_published"] = True
            Opportunity.objects.update_or_create(slug=slug, defaults=data)

        for index, (question, answer) in enumerate(FAQS, start=1):
            FAQItem.objects.update_or_create(
                question=question,
                defaults={"answer": answer, "sort_order": index * 10, "is_published": True},
            )

        users = self.seed_users()
        events = self.seed_events(users)
        post_count = self.seed_journal(events)
        if settings.DEBUG:
            self.seed_member_feed(users["verified"])
            self.seed_memberships()

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded site settings, {len(OPPORTUNITIES)} opportunities, {len(FAQS)} FAQs, "
                f"{len(events)} events, {post_count} journal posts and "
                f"{len(users)} demo accounts."
            )
        )

    def seed_users(self):
        users = {}
        credentials = []
        for email, display_name, verified in DEMO_USERS:
            password = secrets.token_urlsafe(12)
            user = User.objects.filter(email=email).first()
            if user is None:
                user = User.objects.create_user(
                    email=email, display_name=display_name, password=password
                )
            else:
                user.set_password(password)
            user.email_verified_at = timezone.now() if verified else None
            user.save()
            users["verified" if verified else "unverified"] = user
            credentials.append((email, password, verified))

        if settings.DEBUG:
            self.stdout.write("Demo accounts (DEBUG only, passwords change on every run):")
            for email, password, verified in credentials:
                label = "verified" if verified else "not verified"
                self.stdout.write(f"  {email}  {password}  ({label})")
        return users

    def seed_member_feed(self, demo_verified):
        from apps.feed.demo import seed_feed

        demo_member = seed_feed(demo_verified)
        password = secrets.token_urlsafe(12)
        demo_member.set_password(password)
        demo_member.save(update_fields=["password"])
        self.stdout.write("Member feed demo account (DEBUG only):")
        self.stdout.write(f"  {demo_member.email}  {password}  (feed member)")

    def seed_memberships(self):
        from apps.memberships.demo import seed_memberships

        accounts = seed_memberships()
        self.stdout.write(
            "Membership demo accounts (DEBUG only; placeholder tiers, prices and agreement):"
        )
        for display_name, (email, password) in accounts.items():
            self.stdout.write(f"  {email}  {password}  ({display_name})")

    def upsert_event(self, slug, **values):
        values.setdefault("is_published", True)
        event, _ = Event.objects.update_or_create(slug=slug, defaults=values)
        return event

    def seed_events(self, users):
        events = {}
        for week, topic_slug in enumerate(EDUCATION_NIGHT_TOPICS):
            opportunity = Opportunity.objects.get(slug=topic_slug)
            starts = upcoming_weekday(3, week, time(19, 0))
            event = self.upsert_event(
                f"education-night-{timezone.localtime(starts):%Y-%m-%d}",
                title=f"Education Night: {opportunity.title}",
                summary=opportunity.summary,
                body=f"<p>{opportunity.summary}</p><p>Doors open at 6:45 pm. Orientation "
                "for newcomers starts at 7:00 pm in the parlor.</p>",
                category=Event.Category.EDUCATION,
                starts_at=starts,
                ends_at=starts + timedelta(hours=3),
                location_label=opportunity.location_label,
                capacity=40,
                opportunity=opportunity,
                show_attendee_count=True,
            )
            events.setdefault("education", []).append(event)

        for week in range(4):
            for weekday, name in ((4, "Friday"), (5, "Saturday")):
                starts = upcoming_weekday(weekday, week, time(21, 0))
                event = self.upsert_event(
                    f"{name.lower()}-social-{timezone.localtime(starts):%Y-%m-%d}",
                    title=f"{name} Social",
                    summary="An unhurried evening of conversation, with hosts on the floor.",
                    body=SOCIAL_BODY,
                    category=Event.Category.SOCIAL,
                    starts_at=starts,
                    ends_at=starts + timedelta(hours=4),
                    location_label="Main floor",
                    capacity=80,
                )
                events.setdefault(name.lower(), []).append(event)

        member_start = upcoming_weekday(2, 1, time(19, 30))
        events["members"] = [
            self.upsert_event(
                "member-night",
                title="Member Night",
                summary="A quieter evening for members: drinks, conversation and house news.",
                body="<p>Members only. Bring your questions for the board.</p>",
                category=Event.Category.MEMBER_NIGHT,
                audience=Event.Audience.MEMBERS,
                starts_at=member_start,
                ends_at=member_start + timedelta(hours=3),
                location_label="The Parlor",
            )
        ]

        full_start = upcoming_weekday(6, 0, time(15, 0))
        full_event = self.upsert_event(
            "intimate-salon",
            title="Intimate Salon: Small Group Discussion",
            summary="A small, seated discussion circle. Space is deliberately limited.",
            body="<p>A host-led conversation for a handful of people. The waitlist is open "
            "and places are offered in order.</p>",
            category=Event.Category.SPECIAL,
            starts_at=full_start,
            ends_at=full_start + timedelta(hours=2),
            location_label="The Library",
            capacity=2,
            waitlist_enabled=True,
            show_attendee_count=True,
        )
        RSVP.objects.update_or_create(
            event=full_event,
            user=users["verified"],
            defaults={"status": RSVP.Status.GOING, "party_size": 2, "waitlisted_at": None},
        )
        events["full"] = [full_event]
        return [event for group in events.values() for event in group]

    def seed_journal(self, events):
        author = User.objects.filter(is_staff=True).order_by("pk").first()
        by_kind = {
            "orientation": next(e for e in events if e.category == Event.Category.EDUCATION),
            "social": next(e for e in events if e.slug.startswith("friday-social")),
            "saturday": next(e for e in events if e.slug.startswith("saturday-social")),
            "members": next(e for e in events if e.slug == "member-night"),
        }
        now = timezone.now()
        for index, (slug, image_count, caption, link) in enumerate(JOURNAL_POSTS):
            post, created = Post.objects.update_or_create(
                slug=slug,
                defaults={
                    "caption": caption,
                    "published_at": now - timedelta(days=index * 4, hours=index),
                    "is_published": True,
                    "author": author,
                    "event": by_kind.get(link),
                    "cta_label": "Request a mentor" if link == "cta" else "",
                    "cta_url": "/contact" if link == "cta" else "",
                },
            )
            if created or not post.images.exists():
                post.images.all().delete()
                for order in range(image_count):
                    PostImage.objects.create(
                        post=post,
                        image=gradient_image(index * 3 + order),
                        image_alt="Abstract candlelight in deep red and brass",
                        sort_order=order,
                    )
        return len(JOURNAL_POSTS)
