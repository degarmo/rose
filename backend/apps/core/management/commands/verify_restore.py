"""Check a restored database before putting it back into service. Read-only.

    python manage.py verify_restore [--counts-file before.json] [--write-counts after.json]

- Migrations: every migration in the code is applied, and none is missing.
- Rows: counts every table; with --counts-file, compares against counts taken
  from the source (for example with --write-counts before the backup).
- Integrity: every profile has its account, every membership's payments and
  every feed image's file are where the database says.
- The application: public endpoints, a member's own membership and the feed
  answer as they should, called as restored users without creating sessions.

Nothing is written to the database or to storage.
"""

import json

from django.apps import apps
from django.contrib.auth.models import AnonymousUser
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import RequestFactory
from django.urls import resolve


def table_counts():
    counts = {}
    for model in apps.get_models(include_auto_created=True):
        if model._meta.managed and not model._meta.proxy:
            counts[model._meta.db_table] = model._base_manager.count()
    return dict(sorted(counts.items()))


def call(path, user):
    request = RequestFactory().get(path, HTTP_HOST="localhost")
    request.user = user
    request.session = {}
    match = resolve(path)
    response = match.func(request, *match.args, **match.kwargs)
    if hasattr(response, "render"):
        response.render()
    return response


class Command(BaseCommand):
    help = "Read-only checks of a restored database."

    def add_arguments(self, parser):
        parser.add_argument("--counts-file", help="JSON row counts from the source, to compare.")
        parser.add_argument("--write-counts", help="Write this database's row counts to a file.")

    def handle(self, *args, counts_file, write_counts, **options):
        problems = []

        executor = MigrationExecutor(connection)
        pending = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if pending:
            problems.append(f"{len(pending)} migrations are not applied")
        self.report("migrations", not pending)

        counts = table_counts()
        if write_counts:
            with open(write_counts, "w") as handle:
                json.dump(counts, handle, indent=2)
        if counts_file:
            with open(counts_file) as handle:
                expected = json.load(handle)
            differ = {
                table: (expected.get(table), counts.get(table))
                for table in sorted(set(expected) | set(counts))
                if expected.get(table) != counts.get(table)
            }
            for table, (before, after) in differ.items():
                problems.append(f"{table}: {before} rows before, {after} after")
            self.report(f"row counts match the source ({len(counts)} tables)", not differ)
        else:
            self.stdout.write(f"  {sum(counts.values())} rows in {len(counts)} tables")

        problems += self.integrity()
        # Some views create a missing singleton (site settings) when read; roll
        # back whatever the checks touch, so the command never writes.
        with transaction.atomic():
            problems += self.application()
            transaction.set_rollback(True)

        if problems:
            for problem in problems:
                self.stdout.write(self.style.ERROR(f"  {problem}"))
            raise CommandError(f"{len(problems)} problems found.")
        self.stdout.write(self.style.SUCCESS(f"Restore verified on database '{DEFAULT_DB_ALIAS}'."))

    def report(self, label, ok):
        mark = self.style.SUCCESS("ok") if ok else self.style.ERROR("FAILED")
        self.stdout.write(f"  {label}: {mark}")

    def integrity(self):
        from apps.accounts.models import Profile, User
        from apps.core.private_media import private_media
        from apps.feed.models import FeedImage
        from apps.memberships.models import Membership, Payment

        problems = []
        without_profile = User.objects.exclude(pk__in=Profile.objects.values("user_id")).count()
        if without_profile:
            problems.append(f"{without_profile} accounts have no profile")
        orphan_payments = Payment.objects.exclude(
            membership_id__in=Membership.objects.values("pk")
        ).count()
        if orphan_payments:
            problems.append(f"{orphan_payments} payments have no membership")
        media = private_media()
        missing = [
            image.image.name
            for image in FeedImage.objects.exclude(image="")
            if not media.exists(image.image.name)
        ]
        if missing:
            problems.append(f"{len(missing)} feed images are missing from storage")
        self.report("integrity (profiles, payments, stored files)", not problems)
        return problems

    def application(self):
        from apps.accounts.models import User
        from apps.feed.access import can_view_feed
        from apps.memberships.access import active_membership

        problems = []
        for path in ("/api/site-settings/", "/api/faqs/", "/api/events/", "/api/journal/posts/"):
            status = call(path, AnonymousUser()).status_code
            if status != 200:
                problems.append(f"{path} answered {status}")
        member = next(
            (u for u in User.objects.filter(is_active=True) if active_membership(u) is not None),
            None,
        )
        if member is not None:
            data = json.loads(call("/api/membership/me/", member).content)
            if data["membership"] is None or data["membership"]["status"] not in (
                "active",
                "grace",
            ):
                problems.append("an active member's membership did not load")
        reader = next((u for u in User.objects.filter(is_active=True) if can_view_feed(u)), None)
        if reader is not None and call("/api/members/feed/", reader).status_code != 200:
            problems.append("the feed did not load for a member who can see it")
        self.report("application answers as restored users", not problems)
        return problems
