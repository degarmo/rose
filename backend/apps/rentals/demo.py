"""Development-only rental inquiries: one in every status, one clashing with an event."""

from datetime import time, timedelta

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from apps.events.models import Event

from .models import RentalInquiry

DEMO_INQUIRIES = [
    ("demo-rental-new", RentalInquiry.Type.WORKSHOP, RentalInquiry.Status.NEW, 12),
    ("demo-rental-discussion", RentalInquiry.Type.PRIVATE_SESSION, "in_discussion", 16),
    ("demo-rental-quoted", RentalInquiry.Type.GROUP_EVENT, RentalInquiry.Status.QUOTED, 20),
    ("demo-rental-confirmed", RentalInquiry.Type.OTHER, RentalInquiry.Status.CONFIRMED, 24),
    ("demo-rental-declined", RentalInquiry.Type.GROUP_EVENT, RentalInquiry.Status.DECLINED, 9),
    ("demo-rental-cancelled", RentalInquiry.Type.PRIVATE_SESSION, "cancelled", 11),
]


def seed_rentals():
    if not settings.DEBUG:
        raise ImproperlyConfigured("Rental demo data is for development only.")
    now = timezone.now()
    created = 0
    for label, kind, status, days_ahead in DEMO_INQUIRIES:
        if RentalInquiry.objects.filter(contact_email=f"{label}@example.org").exists():
            continue
        RentalInquiry.objects.create(
            contact_name=label.replace("-", " ").title(),
            contact_email=f"{label}@example.org",
            type=kind,
            preferred_date=timezone.localdate() + timedelta(days=days_ahead),
            start_time=time(14, 0),
            duration_hours=3,
            party_size=12,
            notes="Demo inquiry for development.",
            status=status,
            quoted_amount_cents=30000 if status in ("quoted", "confirmed") else None,
            closed_at=now if status in RentalInquiry.CLOSED else None,
        )
        created += 1

    # One that asks for the same evening as a published event, to show the clash warning.
    event = Event.objects.published().filter(starts_at__gt=now).order_by("starts_at").first()
    clash_email = "demo-rental-clash@example.org"
    if event and not RentalInquiry.objects.filter(contact_email=clash_email).exists():
        local = timezone.localtime(event.starts_at)
        RentalInquiry.objects.create(
            contact_name="Demo Rental Clash",
            contact_email=clash_email,
            type=RentalInquiry.Type.PHOTOSHOOT,
            photoshoot_acknowledged=True,
            preferred_date=local.date(),
            start_time=local.time().replace(second=0, microsecond=0),
            duration_hours=2,
            party_size=4,
            notes="Demo inquiry that overlaps a published event.",
        )
        created += 1
    return created
