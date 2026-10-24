"""Put back the page pictures the site starts with, wherever they are missing.

    python manage.py store_site_image_seeds

pages migration 0009 stores them once, in whatever storage is set when it runs. A staging
preview keeps them on the container's disk, so they are gone after a redeploy, and moving
to object storage starts with an empty bucket. This stores any that are missing under the
same names (with their narrower copies), then lists each page slot whose own picture is
still missing, to upload again in Admin > Content > Page images. Safe to repeat.
"""

import importlib

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from apps.pages.models import SiteImage

seeds = importlib.import_module("apps.pages.migrations.0009_fill_site_images")


class Command(BaseCommand):
    help = "Store the starting page pictures where missing, and list slots with missing pictures."

    def handle(self, *args, **options):
        stored = 0
        for seed in sorted({data["seed"] for data in seeds.SLOTS}):
            name = f"site-images/{seed}"
            missing = not default_storage.exists(name)
            seeds.store(seed)
            if missing:
                stored += 1
                self.stdout.write(f"Stored {name}")
        self.stdout.write(f"{stored} starting picture(s) stored; the others were in place.")
        lost = [
            image.slot
            for image in SiteImage.objects.exclude(image="").order_by("sort_order")
            if not default_storage.exists(image.image.name)
        ]
        if lost:
            self.stdout.write(
                self.style.WARNING(
                    "Missing, upload again in Admin > Content > Page images: " + ", ".join(lost)
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("Every page slot's picture is in storage."))
