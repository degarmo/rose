"""Load the site copy (YAML) into the database.

    python manage.py load_site_content            # dry run: report what would change
    python manage.py load_site_content --commit   # write it
    python manage.py load_site_content --commit --allow-draft about.yaml

By default it loads the committed page copy (apps/pages/site_copy) and then the club's
own files in /content when there are any; --dir loads one folder instead. Idempotent and
never deletes. Copy staff have edited in the admin is kept unless --overwrite is given,
and the report lists what was kept. In production, files still marked as drafts (the
committed copy is, until the club approves it) are refused unless --allow-draft is
given, and that use is written to the audit log. Superusers can do the same from the
admin (Page copy > Load site content).
"""

from django.core.management.base import BaseCommand, CommandError

from apps.pages.site_content import ContentError, load_guarded, read_files, read_sources


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
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Replace copy staff have edited in the admin.",
        )
        parser.add_argument("--dir", default=None, help="Load only this folder of YAML files.")

    def handle(self, *args, files, commit, allow_draft, overwrite, dir, **options):
        try:
            contents = read_files(dir, files) if dir else read_sources(files)
            report = load_guarded(
                contents, commit=commit, allow_draft=allow_draft, overwrite=overwrite
            )
        except ContentError as exc:
            raise CommandError(f"{exc} Nothing was written.") from exc
        for line in report.lines():
            self.stdout.write(f"  {line}")
        if not commit:
            self.stdout.write(self.style.WARNING("Dry run: nothing was written. Add --commit."))
            return
        self.stdout.write(self.style.SUCCESS("Site content loaded."))
