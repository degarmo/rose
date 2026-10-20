"""Give an account everything the member feed needs, in one step. DEBUG only.

    python manage.py make_feed_member you@test.local
    python manage.py make_feed_member you@test.local --tier rose --display-name you

It creates the account if needed and confirms its email; starts an active membership on
the tier, recorded as a door desk activation by the system account "system_dev"; records
an ID check; accepts the current guidelines and joins the feed. A new account (or one with
no password yet) is sent a link to choose a password, which lands in Mailpit.

Idempotent: run it again and it does only what is missing, printing each step either way.
It refuses to run unless DEBUG is on, never runs in staging or production, and leaves the
demo seed marker behind, so a deployed site refuses to start on a database it touched.
"""

import re
from smtplib import SMTPException

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts import tasks as account_tasks
from apps.accounts.models import Profile, User, display_name_validator
from apps.core.models import SeedMarker
from apps.feed import access as feed_access
from apps.feed import services as feed_services
from apps.feed.models import Guidelines

from ... import desk
from ...access import is_age_verified
from ...age import AgeCheckError, record_id_check
from ...models import Membership, Payment, Tier
from ...system import system_user

SYSTEM_EMAIL = "system.dev@localhost.invalid"
SYSTEM_NAME = "system_dev"
NOTE = "Development account (make_feed_member)"
MAILPIT_URL = "http://localhost:8025"


class Command(BaseCommand):
    help = "DEBUG only: give an account a membership, an ID check and the joined member feed."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("--tier", default="rose", help="A tier slug. Defaults to rose.")
        parser.add_argument(
            "--display-name",
            help="For a new account. Defaults to the part of the email before the @.",
        )

    def say(self, step, what):
        self.stdout.write(f"  {step}: {what}")

    def handle(self, *args, email, tier, display_name=None, **options):
        if not settings.DEBUG or settings.DJANGO_ENV in settings.DEPLOYED_ENVS:
            raise CommandError("make_feed_member runs only with DEBUG on, in development.")
        email = User.objects.normalize_email(email.strip()).lower()
        if "@" not in email:
            raise CommandError("Give an email address.")
        plan = Tier.objects.filter(slug=tier).first()
        if plan is None:
            raise CommandError(f"No tier {tier!r}. Run seed_demo or load_site_content first.")
        if plan.is_guest_pass or not plan.grants_feed_access:
            raise CommandError(f"The {plan.name} tier does not include the member feed.")
        guidelines = Guidelines.current()
        if guidelines is None:
            raise CommandError("No community guidelines are published.")

        self.stdout.write(f"make_feed_member {email}")
        with transaction.atomic():
            SeedMarker.objects.get_or_create(pk=1)
            user = self.account(email, display_name)
            checked_before = is_age_verified(user)
            membership = self.membership(user, plan)
            self.id_check(user, membership, checked_before)
            self.join(user, guidelines)
            if not feed_access.can_view_feed(user):
                raise CommandError("The feed still does not open for this account.")
        # After the commit, so the link is never for an account that was rolled back.
        if user.has_usable_password():
            self.say("Password", "unchanged")
        else:
            try:
                account_tasks.send_password_reset_email(user.pk)
            except (OSError, SMTPException) as exc:
                raise CommandError(
                    f"Everything else is done, but the link to choose a password was not sent "
                    f"({exc}). Is Mailpit running? Run the command again to resend it."
                ) from exc
            self.say("Password", f"a link to choose one was sent to {email} ({MAILPIT_URL})")
        self.stdout.write(
            self.style.SUCCESS(f"Done: {email} opens the member feed at /members/feed.")
        )

    def account(self, email, wanted_name):
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            name = self.display_name(email, wanted_name)
            user = User.objects.create_user(email=email, display_name=name)
            user.set_unusable_password()
            user.save()
            self.say("Account", f"created, display name {name}")
        else:
            if not user.is_active:
                raise CommandError(f"{email} is deactivated.")
            self.say("Account", f"already there, display name {user.display_name}")
        if user.email_verified:
            self.say("Email", "already confirmed")
        else:
            user.email_verified_at = timezone.now()
            user.save(update_fields=["email_verified_at"])
            self.say("Email", "confirmed")
        _profile, created = Profile.objects.get_or_create(user=user)
        self.say("Profile", "created" if created else "already there")
        return user

    def display_name(self, email, wanted):
        if wanted:
            candidates = [wanted]
        else:
            base = re.sub(r"[^A-Za-z0-9._-]", "_", email.split("@")[0])[:26].ljust(3, "_")
            candidates = [base, *(f"{base}_{n}" for n in range(2, 100))]
        for name in candidates:
            try:
                display_name_validator(name)
            except ValidationError as exc:
                raise CommandError(f"Display name {name!r}: {' '.join(exc.messages)}") from exc
            if not User.objects.filter(display_name__iexact=name).exists():
                return name
        raise CommandError(f"The display name {candidates[0]!r} is taken. Pass --display-name.")

    def membership(self, user, plan):
        system = system_user(SYSTEM_EMAIL, SYSTEM_NAME)
        membership = (
            Membership.objects.non_terminal().filter(user=user).select_related("tier").first()
        )
        if membership is not None and membership.is_entitled:
            if not membership.tier.grants_feed_access:
                raise CommandError(
                    f"{user.email} already has an active {membership.tier.name} membership, "
                    "which leaves out the feed. End it in the admin first."
                )
            self.say(
                "Membership",
                f"{membership.reference_code} already active on {membership.tier.name}",
            )
            return membership
        if membership is not None and membership.status == Membership.Status.SUSPENDED:
            raise CommandError(f"Membership {membership.reference_code} is suspended.")
        try:
            if membership is not None and membership.paid_awaiting_id_check:
                membership = desk.activate_paid_online(system, membership, id_checked=True)
                how = "already paid"
            else:
                if membership is None:
                    membership = Membership.objects.create(user=user, tier=plan)
                elif membership.tier_id != plan.pk:
                    self.say(
                        "Membership",
                        f"{membership.reference_code} moved from {membership.tier.name}",
                    )
                    membership.tier = plan
                    membership.save(update_fields=["tier", "updated_at"])
                membership = desk.record_payment_and_activate(
                    system,
                    membership,
                    Payment.Method.CASH,
                    plan.price_cents,
                    note=NOTE,
                    id_checked=True,
                )
                how = f"cash ${plan.price_cents / 100:,.2f}"
        except desk.DeskError as exc:
            raise CommandError(str(exc)) from exc
        self.say(
            "Membership",
            f"{membership.reference_code} activated on {membership.tier.name} at the door desk "
            f"by {SYSTEM_NAME} ({how})",
        )
        return membership

    def id_check(self, user, membership, checked_before):
        if checked_before:
            self.say("ID check", "already on file")
            return
        if is_age_verified(user):
            self.say("ID check", f"recorded by {SYSTEM_NAME} with the activation")
            return
        try:
            record_id_check(system_user(SYSTEM_EMAIL, SYSTEM_NAME), user, membership)
        except AgeCheckError as exc:
            raise CommandError(str(exc)) from exc
        self.say("ID check", f"recorded by {SYSTEM_NAME}")

    def join(self, user, guidelines):
        profile = user.profile
        if feed_access.has_accepted_current_guidelines(user):
            self.say("Guidelines", f"version {guidelines.version} already accepted")
        else:
            feed_services.accept_guidelines(user, guidelines.version)
            self.say("Guidelines", f"version {guidelines.version} accepted")
        if profile.participates_in_feed:
            self.say("Feed", "already joined")
            return
        try:
            # Keeps any bio and directory choice they already made.
            feed_services.join_feed(
                user,
                guidelines.version,
                bio=profile.bio,
                hide_from_directory=profile.hide_from_directory,
            )
        except feed_services.FeedError as exc:
            raise CommandError(f"Could not join the feed: {exc.message}") from exc
        self.say("Feed", "joined")
