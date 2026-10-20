"""Make the 400, 800 and 1200 px copies for event pictures uploaded before those widths,
so every srcset entry points at a file that exists. Copies already there are kept."""

from django.db import migrations

WIDTHS = (400, 800, 1200)


def make_variants(apps, schema_editor):
    from apps.core.images import open_clean, save_variants

    Event = apps.get_model("events", "Event")
    for event in Event.objects.exclude(hero_image="").iterator():
        image = event.hero_image
        if not image.storage.exists(image.name):
            continue
        with image.storage.open(image.name, "rb") as source:
            clean = open_clean(source)
        save_variants(image.storage, image.name, clean, WIDTHS, missing_only=True)


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0007_hero_image_widths"),
    ]

    operations = [
        migrations.RunPython(make_variants, migrations.RunPython.noop),
    ]
