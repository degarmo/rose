"""One slot for every fixed picture on the public pages (docs/page-images.md), filled with
the picture each showed from frontend/public/images, which these slots replace. The
pictures are kept in apps/pages/site_image_seeds so a new environment starts with them."""

from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import migrations

from apps.core.consent_images import PUBLIC_VARIANT_WIDTHS
from apps.core.images import encode_webp, open_clean, save_variants

SEEDS = Path(__file__).resolve().parent.parent / "site_image_seeds"
PAGE_HEADER = "Beside the page title, on computers only (1024px and wider)."
PEXELS = "Pexels License (free to use, no attribution required)"

SLOTS = [
    {
        "page": "home",
        "slot": "home.hero",
        "label": "Home: top banner",
        "help_text": "Beside the headline. At least 1600×1280. Computers show it 5:4 and "
        "phones 4:5, so set the focal point on what must stay in view.",
        "aspect_ratio": "5/4",
        "phone_aspect_ratio": "4/5",
        "seed": "dance-floor.webp",
        "image_alt": "Black-and-white photograph of people dancing under stage lights and "
        "haze, seen from behind",
        "credit": "Supplied by the club; rights to confirm before launch (launch checklist)",
    },
    {
        "page": "about",
        "slot": "about.hero",
        "label": "About: header picture",
        "help_text": f"{PAGE_HEADER} At least 1600×1280, shown 5:4.",
        "aspect_ratio": "5/4",
        "seed": "pride-flag.webp",
        "image_alt": "A rainbow pride flag draped over a leather armchair against a warm "
        "ochre wall",
        "credit": f"{PEXELS}; Anthony Shkraba (shkrabaanthony), pexels.com/photo/8191755",
    },
    {
        "page": "visit",
        "slot": "visit.hero",
        "label": "Plan your visit: header picture",
        "help_text": f"{PAGE_HEADER} At least 1600×1067, shown 3:2.",
        "aspect_ratio": "3/2",
        "seed": "hand-on-back.webp",
        "image_alt": "Black-and-white close-up of a hand resting on a bare back in low light",
        "credit": "Supplied by the site owner (Plan.jpeg, turned 90° counter-clockwise); "
        "rights and the subject's consent to confirm before launch",
    },
    {
        "page": "guests",
        "slot": "guests.hero",
        "label": "Guests: header picture",
        "help_text": f"{PAGE_HEADER} At least 1600×1067, shown 3:2.",
        "aspect_ratio": "3/2",
        "seed": "archway.webp",
        "image_alt": "A red-lit archway with graffiti-covered brick walls and a disco ball",
        "credit": f"{PEXELS}; myatezhny39, pexels.com/photo/2121663",
    },
    {
        "page": "rentals",
        "slot": "rentals.hero",
        "label": "Rentals: header picture",
        "help_text": f"{PAGE_HEADER} At least 1600×1067, shown 3:2.",
        "aspect_ratio": "3/2",
        "seed": "archway.webp",
        "image_alt": "A red-lit archway with graffiti-covered brick walls and a disco ball",
        "credit": f"{PEXELS}; myatezhny39, pexels.com/photo/2121663",
    },
    {
        "page": "volunteer",
        "slot": "volunteer.hero",
        "label": "Volunteer: header picture",
        "help_text": f"{PAGE_HEADER} At least 1600×1067, shown 3:2.",
        "aspect_ratio": "3/2",
        "seed": "pride-flag.webp",
        "image_alt": "A rainbow pride flag draped over a leather armchair against a warm "
        "ochre wall",
        "credit": f"{PEXELS}; Anthony Shkraba (shkrabaanthony), pexels.com/photo/8191755",
    },
    {
        "page": "donate",
        "slot": "donate.hero",
        "label": "Donate: header picture",
        "help_text": f"{PAGE_HEADER} At least 1600×1067, shown 3:2.",
        "aspect_ratio": "3/2",
        "seed": "cuffs-and-strawberries.webp",
        "image_alt": "Leather cuffs, a blindfold and a flogger among strawberries on dark fabric",
        "credit": f"{PEXELS}; Pexels user 31299941, pexels.com/photo/8587259",
    },
]


def store(seed):
    """Save a seed picture and its narrower copies once, under a fixed name."""
    name = f"site-images/{seed}"
    with (SEEDS / seed).open("rb") as source:
        clean = open_clean(source)
    data, (width, height) = encode_webp(clean)
    if not default_storage.exists(name):
        default_storage.save(name, ContentFile(data))
    save_variants(default_storage, name, clean, PUBLIC_VARIANT_WIDTHS, missing_only=True)
    return name, width, height


def fill(apps, schema_editor):
    SiteImage = apps.get_model("pages", "SiteImage")
    stored = {}
    for order, data in enumerate(SLOTS):
        values = {key: value for key, value in data.items() if key != "seed"}
        seed = data["seed"]
        if seed not in stored:
            stored[seed] = store(seed)
        name, width, height = stored[seed]
        SiteImage.objects.update_or_create(
            slot=values.pop("slot"),
            defaults={
                **values,
                "sort_order": order,
                "image": name,
                "image_width": width,
                "image_height": height,
                # Every picture was checked: no identifiable face (the manifest's flags).
                "image_faces_visible": False,
                "image_consent_confirmed": False,
            },
        )


def empty(apps, schema_editor):
    apps.get_model("pages", "SiteImage").objects.filter(
        slot__in=[data["slot"] for data in SLOTS]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("pages", "0008_site_images")]

    operations = [migrations.RunPython(fill, empty)]
