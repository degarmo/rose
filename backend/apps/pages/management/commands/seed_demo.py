"""Load placeholder content so every page has something real to show.

Safe to run repeatedly: rows are matched on slug or question and updated.
"""

from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.education.models import Opportunity
from apps.pages.models import FAQItem, SiteSettings

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


def upcoming_thursday_evening(weeks_ahead):
    today = timezone.localdate()
    days_until = (3 - today.weekday()) % 7 or 7
    date = today + timedelta(days=days_until + 7 * weeks_ahead)
    return timezone.make_aware(datetime.combine(date, time(19, 0)))


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

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded site settings, {len(OPPORTUNITIES)} opportunities and {len(FAQS)} FAQs."
            )
        )
