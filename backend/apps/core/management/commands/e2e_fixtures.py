"""Known data for the end-to-end tests. Runs only when DJANGO_ENV is "e2e".

    python manage.py e2e_fixtures [--json]

Creates (or resets) the tiers and agreement, a staff account with a known
authenticator secret, feed members for each test viewport, events for
the RSVP flows and a filled-in member app for the screenshot tests, then prints
what the tests need as JSON. It refuses to run in
any other environment, so none of this can exist in staging or production.
"""

import base64
import json
from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.accounts.models import User
from apps.donations.models import AcknowledgementTemplate
from apps.events.models import Event
from apps.feed import services as feed_services
from apps.feed.models import Announcement, FeedImage, FeedPost, Guidelines, GuidelinesAcceptance
from apps.journal.models import Post as JournalPost
from apps.journal.models import PostImage as JournalImage
from apps.memberships.age import seed_check
from apps.memberships.demo import upsert_tiers
from apps.memberships.models import IdCheck, Membership, MembershipAgreement, Tier
from apps.pages.demo_activity import seed_activity
from apps.pages.management.commands.demo_media import sample_image
from apps.pages.management.commands.seed_demo import DEMO_CONTENT_DIR
from apps.pages.models import SiteSettings
from apps.pages.site_content import load, read_files
from apps.safety import roles

PASSWORD = "e2e-only-password-0123"
# 20 bytes, so the authenticator secret below is fixed and known to the tests.
TOTP_KEY_HEX = "3132333435363738393031323334353637383930"
# The team's own keys, so two staff logins in one test never share a 30-second code.
TEAM_KEYS = {
    "moderator": "4142434445464748494a4b4c4d4e4f5051525354",
    "admin": "6162636465666768696a6b6c6d6e6f7071727374",
}
OWNER_KEY = "7a797877767574737271706f6e6d6c6b6a696867"
VIEWPORTS = ("phone", "desktop")
SHOWCASE_AUTHORS = ("e2e_amber_glow", "e2e_low_lamp", "e2e_velvet_rope")
SHOWCASE_CAPTIONS = [
    "Candlelight and a good book after the Thursday class.",
    "The parlor after everyone left. My favourite hour.",
    "Practising the knots from the workshop at home.",
    "Rain on the window, music on low.",
    "A small ritual: one lamp, one chair, one evening to myself.",
    "Textures I keep coming back to.",
    "Rain on the window and the good chair by it.",
    "Fresh flowers for the front room.",
    "Morning light before anyone else is up.",
    "New table linen, very pleased with it.",
    "Notes from the Thursday class, written up.",
    "Two candles, one book, no rush.",
]
DESK_PERMISSIONS = ("view_membership", "change_membership", "view_payment")


def reset_user(email, display_name, **extra):
    User.objects.filter(email=email).delete()
    user = User.objects.create_user(
        email=email, display_name=display_name, password=PASSWORD, **extra
    )
    user.mark_email_verified()
    return user


class Command(BaseCommand):
    help = "Create the end-to-end test data (DJANGO_ENV=e2e only)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json", action="store_true", dest="as_json", help="Print the data as JSON."
        )

    @transaction.atomic
    def handle(self, *args, as_json, **options):
        if settings.DJANGO_ENV != "e2e":
            raise CommandError("e2e_fixtures only runs with DJANGO_ENV=e2e.")
        now = timezone.now()
        # The membership page's seven tiers and the door guest pass, as development has them.
        upsert_tiers(placeholder=False)
        # The pages' words: the same placeholder copy development uses.
        load(read_files(DEMO_CONTENT_DIR), commit=True)
        site = SiteSettings.load()
        site.nonprofit_status_text = "A volunteer-run 501(c)(3) nonprofit."
        site.check_payable_to = "Test Organisation"
        site.mailing_address = "PO Box 0000\nChicago, IL 60600"
        site.save()
        AcknowledgementTemplate.objects.update_or_create(
            pk=1,
            defaults={
                "subject": "Thank you for your gift",
                "body": "Dear {donor_name}, thank you for {amount} on {date} ({reference}).",
            },
        )
        if not MembershipAgreement.objects.filter(published_at__isnull=False).exists():
            MembershipAgreement.objects.create(
                title="Membership agreement",
                body="<p>I agree to follow the community agreements.</p>" * 12,
                published_at=now,
            )
        if Guidelines.current() is None:
            raise CommandError("No published community guidelines; run migrate first.")

        staff = reset_user("e2e.desk@example.org", "e2e_desk", is_staff=True)
        staff.user_permissions.set(Permission.objects.filter(codename__in=DESK_PERMISSIONS))
        TOTPDevice.objects.create(user=staff, name="e2e", key=TOTP_KEY_HEX, confirmed=True)

        data = {
            "password": PASSWORD,
            "admin_path": f"/{settings.ADMIN_PATH.strip('/')}/",
            "staff": {
                "email": staff.email,
                "totp_secret": base64.b32encode(bytes.fromhex(TOTP_KEY_HEX)).decode(),
            },
            "viewports": {},
            "team": {},
        }
        guidelines = Guidelines.current()
        # The owner's superuser, as `createsuperuser` makes it (email not confirmed, not
        # in the app), with an authenticator; and the same year of activity as seed_demo,
        # so the dashboard has numbers to show.
        User.objects.filter(email="e2e.owner@example.org").delete()
        owner = User.objects.create_superuser(
            email="e2e.owner@example.org", display_name="e2e_owner", password=PASSWORD
        )
        TOTPDevice.objects.create(user=owner, name="e2e", key=OWNER_KEY, confirmed=True)
        # The owner's own ID check, as the team would record it at the door.
        seed_check(owner)
        data["owner"] = {
            "email": owner.email,
            "totp_secret": base64.b32encode(bytes.fromhex(OWNER_KEY)).decode(),
        }
        seed_activity()
        for role, key in TEAM_KEYS.items():
            member = reset_user(f"e2e.{role}@example.org", f"e2e_{role}")
            roles.set_role(member, role)
            seed_check(member)
            feed_services.join_feed(member, guidelines.version)
            TOTPDevice.objects.create(user=member, name="e2e", key=key, confirmed=True)
            data["team"][role] = {
                "email": member.email,
                "totp_secret": base64.b32encode(bytes.fromhex(key)).decode(),
            }
        for viewport in VIEWPORTS:
            people = {}
            for role in ("poster", "friend"):
                user = reset_user(f"e2e.{viewport}.{role}@example.org", f"e2e_{viewport}_{role}")
                user.profile.feed_access_granted = True
                user.profile.save()
                seed_check(user)
                feed_services.join_feed(user, guidelines.version)
                people[role] = user.email
            # May join the feed (a staff grant) but has not: the app opens only after joining.
            joiner = reset_user(f"e2e.{viewport}.joiner@example.org", f"e2e_{viewport}_joiner")
            joiner.profile.feed_access_granted = True
            joiner.profile.save()
            seed_check(joiner)
            people["joiner"] = joiner.email
            events = {}
            starts = now + timedelta(days=5)
            members = {"audience": Event.Audience.MEMBERS, "capacity": 40}
            day = timezone.localtime(starts).date()
            for kind, extra in {
                "open": {"capacity": 40},
                "waitlist": {"capacity": 1, "waitlist_enabled": True, "max_party_size": 1},
                "members": members,
                # Two members-only evenings on one day, so always in the same month:
                # a one-event-a-month membership can RSVP to the first and not the second.
                "members_early": {
                    **members,
                    "starts_at": timezone.make_aware(datetime.combine(day, time(18, 0))),
                },
                "members_late": {
                    **members,
                    "starts_at": timezone.make_aware(datetime.combine(day, time(21, 0))),
                },
            }.items():
                slug = f"e2e-{viewport}-{kind.replace('_', '-')}"
                begins = extra.pop("starts_at", starts)
                Event.objects.filter(slug=slug).delete()
                Event.objects.create(
                    slug=slug,
                    title=f"Test evening ({kind.replace('_', ' ')})",
                    summary="An evening used by the automated tests.",
                    body="<p>An evening used by the automated tests.</p>",
                    starts_at=begins,
                    ends_at=begins + timedelta(hours=3),
                    is_published=True,
                    **extra,
                )
                events[kind] = slug
            data["viewports"][viewport] = {
                "feed": people,
                "events": events,
                "moderation": self.moderation_subjects(viewport, guidelines, now),
                "age_check": self.unchecked_member(viewport, guidelines, now),
                "user_actions": self.action_subjects(viewport, guidelines, now),
            }

        data["showcase"] = self.showcase(now, guidelines)
        data["grid"] = self.grid_events(now)

        if as_json:
            self.stdout.write(json.dumps(data))
        else:
            self.stdout.write(self.style.SUCCESS("End-to-end test data is ready."))

    def unchecked_member(self, viewport, guidelines, now):
        """A paid member who joined the feed before it asked for an ID check, and has none:
        the verify card, a 404 on the feed, then the door desk's check opens it."""
        user = reset_user(f"e2e.{viewport}.unchecked@example.org", f"e2e_{viewport}_unchecked")
        membership = Membership.objects.create(
            user=user, tier=Tier.objects.get(slug="rose"), status=Membership.Status.ACTIVE
        )
        membership.start_new_period(now)
        membership.save()
        GuidelinesAcceptance.objects.create(user=user, guidelines=guidelines)
        profile = user.profile
        profile.joined_feed_at = now
        profile.save(update_fields=["joined_feed_at", "updated_at"])
        profile.set_feed_participation(True)
        return {"email": user.email, "handle": user.display_name, "code": membership.reference_code}

    def action_subjects(self, viewport, guidelines, now):
        """Three members in the feed, each with a running membership, for the admin's
        Members actions: suspended together, lifted together, then one banned."""
        subjects = []
        for n in range(1, 4):
            user = reset_user(
                f"e2e.{viewport}.subject{n}@example.org", f"e2e_{viewport}_subject{n}"
            )
            membership = Membership.objects.create(
                user=user, tier=Tier.objects.get(slug="rose"), status=Membership.Status.ACTIVE
            )
            membership.start_new_period(now)
            membership.save()
            IdCheck.objects.create(user=user, membership=membership)
            feed_services.join_feed(user, guidelines.version)
            subjects.append(
                {
                    "email": user.email,
                    "handle": user.display_name,
                    "code": membership.reference_code,
                }
            )
        return subjects

    def moderation_subjects(self, viewport, guidelines, now):
        """A member who reports, a member with a post to report, and one with a membership
        to ban. The reporter is the flow's own, so other tests leaving the feed cannot
        affect it."""
        reporter = reset_user(f"e2e.{viewport}.reporter@example.org", f"e2e_{viewport}_reporter")
        reporter.profile.feed_access_granted = True
        reporter.profile.save()
        seed_check(reporter)
        feed_services.join_feed(reporter, guidelines.version)
        author = reset_user(f"e2e.{viewport}.author@example.org", f"e2e_{viewport}_author")
        author.profile.feed_access_granted = True
        author.profile.save()
        seed_check(author)
        feed_services.join_feed(author, guidelines.version)
        post = FeedPost.objects.create(
            author=author,
            caption="A post the tests report.",
            status=FeedPost.Status.PUBLISHED,
            consent_attested_at=now,
            first_published_at=now,
        )
        banned = reset_user(f"e2e.{viewport}.banned@example.org", f"e2e_{viewport}_banned")
        membership = Membership.objects.create(
            user=banned, tier=Tier.objects.get(slug="rose"), status=Membership.Status.ACTIVE
        )
        membership.start_new_period(now)
        membership.save()
        IdCheck.objects.create(user=membership.user, membership=membership)
        return {
            "reporter": reporter.email,
            "author": author.email,
            "author_handle": author.display_name,
            "post": post.public_id,
            "banned_handle": banned.display_name,
            "banned_code": membership.reference_code,
        }

    def grid_events(self, now):
        """Enough upcoming evenings for the Events grid to need "Load more": every category,
        most with a picture, some without, and one whose faces have no consent (shown as
        the category's fallback)."""
        Event.objects.filter(slug__startswith="e2e-grid-").delete()
        categories = list(Event.Category.values)
        slugs = []
        for n in range(18):
            starts = timezone.localtime(now + timedelta(days=40 + n)).replace(
                hour=19, minute=0, second=0, microsecond=0
            )
            values = {
                "slug": f"e2e-grid-{n:02d}",
                "title": f"Grid evening {n + 1}",
                "summary": "An evening the Events grid tests count.",
                "category": categories[n % len(categories)],
                "starts_at": starts,
                "ends_at": starts + timedelta(hours=3),
                "is_published": True,
                "audience": Event.Audience.MEMBERS if n % 6 == 5 else Event.Audience.PUBLIC,
                # The banner at the top of /events and Home.
                "is_featured": n == 1,
            }
            if n % 3 != 2:
                picture = sample_image(60 + n)
                values.update(
                    hero_image=picture.file,
                    hero_image_alt=picture.alt,
                    hero_image_faces_visible=n == 4,
                )
            Event.objects.create(**values)
            slugs.append(values["slug"])
        return {"slugs": slugs, "featured": "Grid evening 2"}

    def showcase(self, now, guidelines):
        """A lived-in member app for the screenshot tests: photos, comments, likes,
        saves, notifications, club journal posts, an announcement and events tonight
        and this week. Images are generated gradients, never photographs."""

        def member(display_name):
            user = reset_user(f"{display_name}@example.org", display_name)
            user.profile.feed_access_granted = True
            user.profile.bio = "Here for the classes, staying for the people."
            user.profile.save()
            seed_check(user)
            feed_services.join_feed(
                user, guidelines.version, bio=user.profile.bio, hide_from_directory=False
            )
            return user

        viewer = member("e2e_night_owl")
        authors = [member(name) for name in SHOWCASE_AUTHORS]
        posts = []
        picture_index = 0
        for index, caption in enumerate(SHOWCASE_CAPTIONS):
            author = ([viewer] + authors)[index % 4]
            created = now - timedelta(hours=index * 5 + 2)
            post = FeedPost.objects.create(
                author=author,
                caption=caption,
                status=FeedPost.Status.PUBLISHED,
                consent_attested_at=created,
                first_published_at=created,
            )
            FeedPost.objects.filter(pk=post.pk).update(created_at=created)
            # Twelve posts, sixteen different pictures: no tile repeats in the feed or grids.
            for position in range((1, 2, 1, 3, 1, 1)[index % 6]):
                picture = sample_image(picture_index, width=720)
                picture_index += 1
                FeedImage.objects.create(
                    post=post,
                    position=position,
                    image=picture.file,
                    image_alt=picture.alt,
                    width=picture.width,
                    height=picture.height,
                )
            posts.append(post)
        for index, post in enumerate(posts):
            for liker in [viewer, *authors][: index % 4 + 1]:
                if liker != post.author:
                    feed_services.like(liker, post.public_id)
            commenter = authors[(index + 1) % len(authors)]
            if commenter != post.author:
                feed_services.add_comment(commenter, post.public_id, "Beautiful light.")
        for post in posts[1:3]:
            if post.author != viewer:
                feed_services.save_post(viewer, post.public_id)

        for index, (slug, caption) in enumerate(
            [
                ("e2e-shot-autumn", "The autumn season of Thursday classes begins this week."),
                ("e2e-shot-parlor", "Our volunteers spent the weekend repainting the parlor."),
            ]
        ):
            post, _ = JournalPost.objects.update_or_create(
                slug=slug,
                defaults={
                    "caption": caption,
                    "published_at": now - timedelta(hours=index * 9 + 4),
                    "is_published": True,
                },
            )
            post.images.all().delete()
            picture = sample_image(30 + index)
            JournalImage.objects.create(
                post=post, image=picture.file, image_alt=picture.alt, sort_order=0
            )

        Announcement.objects.filter(title__startswith="[e2e]").delete()
        Announcement.objects.create(
            title="[e2e] Coat check is back",
            body="Bring a small bag for the evening; the coat room opens at seven.",
            link_label="Plan your visit",
            link_url="/visit",
            starts_at=now - timedelta(hours=1),
            ends_at=now + timedelta(days=7),
            is_published=True,
        )
        local = timezone.localtime(now)
        tonight = max(
            local.replace(hour=22, minute=0, second=0, microsecond=0), local + timedelta(minutes=30)
        )
        for slug, title, starts in [
            ("e2e-shot-tonight", "Late lounge", tonight),
            ("e2e-shot-week", "Thursday class: communication", now + timedelta(days=2)),
        ]:
            Event.objects.filter(slug=slug).delete()
            Event.objects.create(
                slug=slug,
                title=title,
                summary="An evening for members and their guests.",
                body="<p>An evening for members and their guests.</p>",
                starts_at=starts,
                ends_at=starts + timedelta(hours=3),
                is_published=True,
                capacity=40,
            )
        return {
            "viewer": viewer.email,
            "viewer_handle": viewer.display_name,
            "other_handle": authors[0].display_name,
        }
