"""Load the drafted site copy (YAML) into the database.

    python manage.py load_site_content            # dry run: report what would change
    python manage.py load_site_content --commit   # write it
    python manage.py load_site_content --commit --allow-draft about.yaml

Idempotent and never deletes. In production, files still marked as drafts are
refused unless --allow-draft is given, and that use is written to the audit log.
Superusers can do the same from the admin (Page copy > Load site content).
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.pages.site_content import ContentError, load_guarded, read_files


class Command(BaseCommand):
    help = "Load site copy, FAQs, staff profiles, tiers and redirects from YAML files."

    def add_arguments(self, parser):
        parser.add_argument("files", nargs="*", help="Only these files (default: every .yaml).")
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--dry-run", action="store_true", help="Report only (the default).")
        mode.add_argument("--commit", action="store_true", help="Write the changes.")
        parser.add_argument(
            "--allow-draft",
            action="store_true",
            help="In production, load files still marked as drafts (logged).",
        )
        parser.add_argument("--dir", default=None, help="Folder of YAML files.")

    def handle(self, *args, files, commit, allow_draft, dir, **options):
        try:
            contents = read_files(dir or settings.SITE_CONTENT_DIR, files)
            report = load_guarded(contents, commit=commit, allow_draft=allow_draft)
        except ContentError as exc:
            raise CommandError(f"{exc} Nothing was written.") from exc
        for line in report.lines():
            self.stdout.write(f"  {line}")
        if not commit:
            self.stdout.write(self.style.WARNING("Dry run: nothing was written. Add --commit."))
            return
        self.stdout.write(self.style.SUCCESS("Site content loaded."))
