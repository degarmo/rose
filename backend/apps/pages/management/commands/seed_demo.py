"""Load placeholder content so every page has something real to show (development only).

The events, education, FAQ, journal posts and announcement are the shared samples
(apps.pages.samples, the same ones load_staging_samples puts on staging), and the page
copy is the committed site copy. On top of those come what only development has: made-up
staff profiles, demo accounts, evenings tied to membership tiers with RSVPs, more journal
posts and, with DEBUG on, the member feed, memberships, the team and a year of activity.

Safe to run repeatedly: rows are matched on slug, question or email and updated. With
DEBUG on, every demo account gets DEMO_PASSWORD and the logins are printed at the end
(they are also listed in the README). With DEBUG off the passwords are random and nothing
is printed.
"""

import secrets
from datetime import datetime, time, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import SeedMarker
from apps.events.models import RSVP, Event, EventTag
from apps.journal.models import Post, PostImage
from apps.pages import samples
from apps.pages.models import SiteSettings
from apps.pages.site_content import SITE_COPY_DIR, load, read_files

from .demo_media import sample_image

# Made-up staff profiles for the staff page: people, so development only.
DEMO_CONTENT_DIR = Path(__file__).resolve().parents[2] / "demo_content"

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
    "nonprofit_status_text": "A volunteer-run 501(c)(3) nonprofit.",
    "check_payable_to": "Placeholder Organisation Name",
    "mailing_address": "PO Box 0000\nChicago, IL 60600",
    "legal_name": "Placeholder Organisation Name",
    "ein": "00-0000000",
}


def upcoming_weekday(weekday, weeks_ahead, at):
    """The next given weekday (0 = Monday) after today, plus N weeks, at a local time."""
    today = timezone.localdate()
    days_until = (weekday - today.weekday()) % 7 or 7
    date = today + timedelta(days=days_until + 7 * weeks_ahead)
    return timezone.make_aware(datetime.combine(date, at))


def next_first_friday(at):
    """The first Friday of a month that is still ahead, at a local time."""
    today = timezone.localdate()
    first = today.replace(day=1)
    for _ in range(2):
        friday = first + timedelta(days=(4 - first.weekday()) % 7)
        if friday > today:
            return timezone.make_aware(datetime.combine(friday, at))
        first = (first + timedelta(days=32)).replace(day=1)
    raise AssertionError("A first Friday always falls within two months.")


DEMO_USERS = [
    ("demo.verified@example.org", "demo_verified", True),
    ("demo.unverified@example.org", "demo_unverified", False),
]

# Development's own journal posts, beside the three samples.
JOURNAL_POSTS = [
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
        if settings.DJANGO_ENV in settings.DEPLOYED_ENVS:
            raise CommandError(f"seed_demo never runs in {settings.DJANGO_ENV}.")
        SeedMarker.objects.get_or_create(pk=1)
        site_settings = SiteSettings.load()
        for field, value in SITE_SETTINGS.items():
            setattr(site_settings, field, value)
        site_settings.save()

        sample_report = samples.load(adopt=True)
        load(read_files(SITE_COPY_DIR) + read_files(DEMO_CONTENT_DIR), commit=True)
        self.logins = []
        users = self.seed_users()
        events = self.seed_events(users)
        post_count = self.seed_journal()
        if settings.DEBUG:
            self.seed_member_feed(users["verified"])
            self.seed_memberships()
            self.seed_team()
            self.seed_parity()
            self.seed_safety()

        made = sum(sample_report.created.values()) + sum(sample_report.updated.values())
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded site settings, {made} sample rows (events, education, FAQs, journal "
                f"and an announcement), {len(events)} development evenings, {post_count} more "
                f"journal posts and {len(users)} demo accounts."
            )
        )
        if settings.DEBUG:
            # After the commit, so the summary comes after anything sent on commit (emails).
            transaction.on_commit(self.print_logins)

    def demo_password(self):
        return settings.DEMO_PASSWORD if settings.DEBUG else secrets.token_urlsafe(12)

    def seed_users(self):
        users = {}
        for email, display_name, verified in DEMO_USERS:
            password = self.demo_password()
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
            label = "plain account" if verified else "plain account, email not confirmed"
            self.logins.append((label, email))
        return users

    def seed_member_feed(self, demo_verified):
        from apps.feed.demo import seed_feed

        demo_member = seed_feed(demo_verified)
        demo_member.set_password(self.demo_password())
        demo_member.save(update_fields=["password"])
        self.logins.append(("member with the member app open (feed joined)", demo_member.email))

    def seed_memberships(self):
        from apps.memberships.demo import seed_memberships

        accounts = seed_memberships(self.demo_password())
        labels = {
            "desk_volunteer": "staff: door desk volunteer (no team role)",
            "demo_active": "active member, feed included but not joined yet",
            "demo_community": "member without feed access (Community, waiting for ID check)",
            "demo_limited": "active Limited member",
        }
        for display_name, email in accounts.items():
            self.logins.append((labels.get(display_name, f"membership: {display_name}"), email))

    def seed_team(self):
        from apps.safety.demo import seed_team

        for label, email in seed_team(self.demo_password()):
            self.logins.append((label, email))

    def seed_safety(self):
        from apps.pages.demo_activity import seed_activity
        from apps.safety.demo import seed_safety

        seed_safety()
        added = seed_activity()
        if added:
            self.stdout.write(
                f"A year of club life: {added} members with payments, past evenings with "
                "check-ins, gifts, posts, reports and email subscribers (DEBUG only)."
            )

    def print_logins(self):
        self.stdout.write("")
        self.stdout.write("Demo accounts (DEBUG only). Every password is DEMO_PASSWORD:")
        self.stdout.write(f"  password: {settings.DEMO_PASSWORD}")
        width = max(len(email) for _, email in self.logins)
        for label, email in self.logins:
            self.stdout.write(f"  {email.ljust(width)}  {label}")
        self.stdout.write(
            "  Team accounts set up an authenticator on their first visit to /members/staff."
        )

    def seed_parity(self):
        """Guests come with the membership demo; this adds rentals, volunteers,
        gifts and the email list. DEBUG only."""
        from apps.donations.demo import seed_donations
        from apps.newsletter.demo import seed_newsletter
        from apps.rentals.demo import seed_rentals
        from apps.volunteers.demo import seed_volunteers

        staff = User.objects.filter(email="desk.volunteer@example.org").first()
        seed_rentals()
        seed_volunteers()
        seed_donations(staff)
        seed_newsletter()
        self.stdout.write(
            "Rentals, volunteers, gifts, the email list and placeholder acknowledgement "
            "wording (DEBUG only)."
        )

    def upsert_event(self, slug, **values):
        values.setdefault("is_published", True)
        event, _ = Event.objects.update_or_create(slug=slug, defaults=values)
        return event

    def seed_events(self, users):
        """Development's own evenings, beside the samples: two for the free tiers' tags,
        and a full one with an RSVP and a waitlist."""
        community_start = upcoming_weekday(6, 1, time(18, 0))
        first_friday = next_first_friday(time(20, 0))
        community = self.upsert_event(
            "community-evening",
            title="Community Evening",
            summary="An open evening for every member, including Community members.",
            body="<p>A relaxed evening with hosts on hand. Bring a valid photo ID.</p>",
            category=Event.Category.MEMBER_NIGHT,
            audience=Event.Audience.MEMBERS,
            starts_at=community_start,
            ends_at=community_start + timedelta(hours=3),
            location_label="Main floor",
            capacity=60,
        )
        community.access_tags.set(EventTag.objects.filter(slug="community"))
        first = self.upsert_event(
            "first-friday",
            title="First Friday",
            summary="The month's welcome evening, open to First Fridays members.",
            body="<p>A welcoming evening for newcomers, with a short tour at 8:30 pm.</p>",
            category=Event.Category.SPECIAL,
            audience=Event.Audience.MEMBERS,
            starts_at=first_friday,
            ends_at=first_friday + timedelta(hours=3),
            location_label="Main floor",
            capacity=60,
        )
        first.access_tags.set(EventTag.objects.filter(slug="first_friday"))

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
        return [community, first, full_event]

    def seed_journal(self):
        """Development's journal posts, linked to the sample evenings."""
        author = User.objects.filter(is_staff=True).order_by("pk").first()
        upcoming = Event.objects.upcoming().order_by("starts_at")
        by_kind = {
            "social": upcoming.filter(slug__startswith="friday-social").first(),
            "saturday": upcoming.filter(slug__startswith="saturday-social").first(),
            "members": upcoming.filter(slug__startswith="members-night").first(),
        }
        now = timezone.now()
        for index, (slug, image_count, caption, link) in enumerate(JOURNAL_POSTS, start=1):
            post, created = Post.objects.update_or_create(
                slug=slug,
                defaults={
                    "caption": caption,
                    "published_at": now - timedelta(days=index * 4 + 1, hours=index),
                    "is_published": True,
                    "author": author,
                    "event": by_kind.get(link),
                    "cta_label": "",
                    "cta_url": "",
                },
            )
            if created or not post.images.exists():
                post.images.all().delete()
                for order in range(image_count):
                    picture = sample_image(index * 3 + order + 30)
                    PostImage.objects.create(
                        post=post, image=picture.file, image_alt=picture.alt, sort_order=order
                    )
        return len(JOURNAL_POSTS)
