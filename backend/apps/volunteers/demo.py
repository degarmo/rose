"""Development-only volunteer signups, one in each status."""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .models import VolunteerSignup

DEMO_SIGNUPS = [
    ("Demo Door Host", ["door", "events"], ["weekends"], VolunteerSignup.Status.NEW),
    ("Demo Teacher", ["teaching"], ["weeknights"], VolunteerSignup.Status.CONTACTED),
    ("Demo Fixer", ["maintenance", "setup"], ["daytime", "one_off"], VolunteerSignup.Status.ACTIVE),
    ("Demo Web Helper", ["admin_web"], ["one_off"], VolunteerSignup.Status.INACTIVE),
]


def seed_volunteers():
    if not settings.DEBUG:
        raise ImproperlyConfigured("Volunteer demo data is for development only.")
    created = 0
    for name, interests, availability, status in DEMO_SIGNUPS:
        email = f"{name.lower().replace(' ', '.')}@example.org"
        _, made = VolunteerSignup.objects.get_or_create(
            contact_email=email,
            defaults={
                "contact_name": name,
                "interests": interests,
                "availability": availability,
                "experience_note": "Demo signup for development.",
                "status": status,
            },
        )
        created += made
    return created
