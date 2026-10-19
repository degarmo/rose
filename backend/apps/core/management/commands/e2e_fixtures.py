"""Known data for the end-to-end tests. Runs only when DJANGO_ENV is "e2e".

    python manage.py e2e_fixtures [--json]

Creates (or resets) a tier and agreement, a staff account with a known
authenticator secret, feed members for each test viewport, and events for
the RSVP flows, then prints what the tests need as JSON. It refuses to run in
any other environment, so none of this can exist in staging or production.
"""

import base64
import json
from datetime import timedelta

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
from apps.feed.models import Guidelines
from apps.memberships.models import MembershipAgreement, Tier
from apps.pages.management.commands.seed_demo import DEMO_CONTENT_DIR
from apps.pages.models import SiteSettings
from apps.pages.site_content import load, read_files

PASSWORD = "e2e-only-password-0123"
# 20 bytes, so the authenticator secret below is fixed and known to the tests.
TOTP_KEY_HEX = "3132333435363738393031323334353637383930"
VIEWPORTS = ("phone", "desktop")
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
        Tier.objects.update_or_create(
            slug="e2e-monthly",
            defaults={
                "name": "Monthly",
                "description": "Renews every month.",
                "benefits": ["Members-only nights", "The member community"],
                "price_cents": 2500,
                "interval": Tier.Interval.MONTH,
            },
        )
        Tier.objects.update_or_create(
            slug="e2e-guest",
            defaults={
                "name": "Guest night pass",
                "description": "One evening, paid at the door.",
                "price_cents": 1500,
                "interval": Tier.Interval.ONCE,
                "duration_days": 1,
                "grants_feed_access": False,
                "grants_members_events": False,
                "grants_members_education": False,
                "is_guest_pass": True,
                "sort_order": 90,
            },
        )
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
        }
        guidelines = Guidelines.current()
        for viewport in VIEWPORTS:
            people = {}
            for role in ("poster", "friend"):
                user = reset_user(f"e2e.{viewport}.{role}@example.org", f"e2e_{viewport}_{role}")
                user.profile.feed_access_granted = True
                user.profile.save()
                feed_services.join_feed(user, guidelines.version)
                people[role] = user.email
            events = {}
            starts = now + timedelta(days=5)
            for kind, extra in {
                "open": {"capacity": 40},
                "waitlist": {"capacity": 1, "waitlist_enabled": True, "max_party_size": 1},
                "members": {"audience": Event.Audience.MEMBERS, "capacity": 40},
            }.items():
                slug = f"e2e-{viewport}-{kind}"
                Event.objects.filter(slug=slug).delete()
                Event.objects.create(
                    slug=slug,
                    title=f"Test evening ({kind})",
                    summary="An evening used by the automated tests.",
                    body="<p>An evening used by the automated tests.</p>",
                    starts_at=starts,
                    ends_at=starts + timedelta(hours=3),
                    is_published=True,
                    **extra,
                )
                events[kind] = slug
            data["viewports"][viewport] = {"feed": people, "events": events}

        if as_json:
            self.stdout.write(json.dumps(data))
        else:
            self.stdout.write(self.style.SUCCESS("End-to-end test data is ready."))
