"""Development-only gifts by every method, and placeholder acknowledgement wording."""

from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from .models import ANONYMOUS, AcknowledgementTemplate, Donation

PLACEHOLDER_WORDING = (
    "PLACEHOLDER WORDING FOR DEVELOPMENT. The club's accountant reviews the real text "
    "before launch.\n\n"
    "Dear {donor_name},\n\n"
    "Thank you for your gift of {amount} on {date} ({method}, reference {reference}).\n\n"
    "{legal_name} is a 501(c)(3) nonprofit organization, EIN {ein}. No goods or services "
    "were provided in exchange for this contribution.\n"
)

DEMO_GIFTS = [
    ("DON-DEMO01", 2500, Donation.Method.CASH, ANONYMOUS, 40),
    ("DON-DEMO02", 10000, Donation.Method.CARD_IN_PERSON, "A friend of the house", 25),
    ("DON-DEMO03", 5000, Donation.Method.ONLINE, ANONYMOUS, 12),
    ("DON-DEMO04", 25000, Donation.Method.CHECK, ANONYMOUS, 3),
]


def seed_donations(staff=None):
    if not settings.DEBUG:
        raise ImproperlyConfigured("Donation demo data is for development only.")
    if not AcknowledgementTemplate.objects.filter(pk=1).exists():
        template = AcknowledgementTemplate(body=PLACEHOLDER_WORDING)
        template.is_placeholder = True
        template.save()
    now = timezone.now()
    created = 0
    for reference, cents, method, name, days_ago in DEMO_GIFTS:
        if Donation.objects.filter(reference=reference).exists():
            continue
        Donation.objects.create(
            reference=reference,
            amount_cents=cents,
            method=method,
            donor_display=name,
            provider="sandbox" if method == Donation.Method.ONLINE else "",
            provider_payment_ref=f"sbx_pay_demo_{reference.lower()}"
            if method == Donation.Method.ONLINE
            else None,
            recorded_by=None if method == Donation.Method.ONLINE else staff,
            created_at=now - timedelta(days=days_ago),
            note="Demo gift for development.",
        )
        created += 1
    return created
