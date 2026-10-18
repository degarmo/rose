"""Development only: pretend days have passed, then run the daily lifecycle.

Every date on the chosen memberships moves back by --days, which is the same
as the calendar moving forward. Refuses to run with DEBUG off.
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import F

from ... import lifecycle
from ...models import Membership

DATE_FIELDS = [
    "created_at",
    "current_period_start",
    "current_period_end",
    "reminded_14_at",
    "reminded_3_at",
    "grace_started_at",
    "ended_at",
]


class Command(BaseCommand):
    help = "DEBUG only: move membership dates back N days and run the lifecycle."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, required=True)
        parser.add_argument("--member", help="Display name; default is every membership.")

    def handle(self, *args, days, member, **options):
        if not settings.DEBUG:
            raise CommandError("membership_clock is for development only.")
        if days < 1:
            raise CommandError("--days must be 1 or more.")
        memberships = Membership.objects.all()
        if member:
            memberships = memberships.filter(user__display_name__iexact=member)
            if not memberships.exists():
                raise CommandError(f"No membership for {member!r}.")
        shift = timedelta(days=days)
        moved = memberships.update(**{name: F(name) - shift for name in DATE_FIELDS})
        counts = lifecycle.run()
        summary = ", ".join(f"{key.replace('_', ' ')}: {n}" for key, n in counts.items())
        self.stdout.write(f"Moved {moved} memberships {days} days on. Lifecycle: {summary}.")
