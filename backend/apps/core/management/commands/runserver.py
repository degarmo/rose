"""The development server, which keeps the database in step with the code.

With DEBUG on, every start and every reload after a code change first applies any
unapplied migrations, so a new migration file can never leave the API failing on a
missing column. Anything still unapplied afterwards (a migration that failed) is
reported loudly, as is an empty tier table, before the server starts.
"""

from django.conf import settings
from django.contrib.staticfiles.management.commands.runserver import Command as StaticRunserver
from django.core.management import call_command
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.migrations.executor import MigrationExecutor


def pending_migrations():
    """(app, name) for every migration not yet applied to the default database."""
    executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    return [(migration.app_label, migration.name) for migration, _ in plan]


def migrate_for_development(stdout, stderr, style):
    """Apply pending migrations. Returns how many are still unapplied; never raises."""
    pending = pending_migrations()
    if not pending:
        return 0
    stdout.write(f"Applying {len(pending)} unapplied migration(s) before starting.")
    try:
        call_command("migrate", interactive=False, verbosity=1, stdout=stdout)
    except Exception as exc:  # noqa: BLE001 - the server still starts, with a loud warning
        stderr.write(style.ERROR(f"Migrations failed: {exc}"))
    remaining = pending_migrations()
    if remaining:
        names = ", ".join(f"{app}.{name}" for app, name in remaining)
        stderr.write(
            style.ERROR(
                f"WARNING: {len(remaining)} migration(s) are still unapplied ({names}). "
                "Pages that use those tables will fail until they are applied."
            )
        )
    return len(remaining)


def warn_if_no_tiers(stderr, style):
    from apps.memberships.join import offered_tiers

    if not offered_tiers().exists():
        stderr.write(
            style.WARNING(
                "No membership tiers are on offer, so /membership is empty. "
                "Run `manage.py seed_demo` or `manage.py load_site_content --commit`."
            )
        )


class Command(StaticRunserver):
    help = (
        "Starts the development server. With DEBUG on it applies unapplied migrations "
        "first, on every start and reload."
    )

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--skip-migrate",
            action="store_true",
            help="Do not apply migrations before starting (they are still reported).",
        )

    def inner_run(self, *args, **options):
        if settings.DEBUG and not options.get("skip_migrate"):
            if migrate_for_development(self.stdout, self.stderr, self.style) == 0:
                warn_if_no_tiers(self.stderr, self.style)
        super().inner_run(*args, **options)
