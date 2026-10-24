"""Fill staging with clearly sample content, and no people (apps.pages.samples).

    python manage.py load_staging_samples            # dry run: what would be made
    python manage.py load_staging_samples --commit   # make or update the samples
    python manage.py load_staging_samples --purge    # delete every sample and its pictures

Runs where DEBUG is on or DJANGO_ENV is staging, and never in production (whose start-up
checks also refuse a database holding samples, rose.E014). Running it again updates the
samples, puts back any picture missing from storage, and leaves rows staff made alone.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.pages import samples


def samples_allowed():
    return settings.DEBUG or settings.DJANGO_ENV == "staging"


class Command(BaseCommand):
    help = "Load (or purge) sample events, education, FAQs, journal posts and an announcement."

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--commit", action="store_true", help="Make or update the samples.")
        mode.add_argument("--purge", action="store_true", help="Delete every sample row.")

    def handle(self, *args, commit, purge, **options):
        if settings.DJANGO_ENV == "production" or not samples_allowed():
            raise CommandError(
                f"load_staging_samples runs on staging or with DEBUG on, not in "
                f"{settings.DJANGO_ENV}."
            )
        if purge:
            removed = samples.purge()
            for label, count in sorted(removed.items()):
                self.stdout.write(f"  Removed {count} {label}")
            self.stdout.write(self.style.SUCCESS("Sample content removed, with its pictures."))
            return
        if commit:
            report = samples.load()
        else:
            # Pictures are files, outside the transaction, so a dry run draws none.
            with transaction.atomic():
                report = samples.load(with_pictures=False)
                transaction.set_rollback(True)
        for line in report.lines():
            self.stdout.write(f"  {line}")
        if not commit:
            self.stdout.write(self.style.WARNING("Dry run: nothing was written. Add --commit."))
            return
        self.stdout.write(self.style.SUCCESS("Sample content loaded."))
