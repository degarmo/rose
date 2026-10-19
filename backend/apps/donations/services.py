"""Giving: online checkouts, provider events, gifts recorded at the door, and
acknowledgements.

Online gifts go through the same provider layer as memberships
(PaymentProvider.create_one_time_checkout). The provider event service stores
and deduplicates every webhook, then calls apply_provider_event for events
whose purpose starts with "donation:".
"""

import logging

from django.conf import settings
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from apps.core.email import send_neutral_mail
from apps.core.models import AuditLog, audit
from apps.memberships.providers import registry
from apps.memberships.providers.base import (
    PAYMENT_FAILED,
    PAYMENT_SUCCEEDED,
    REFUNDED,
    ProviderError,
)
from apps.pages.models import SiteSettings

from .models import ANONYMOUS, Acknowledgement, AcknowledgementTemplate, Donation, DonationCheckout

logger = logging.getLogger(__name__)

DESK_METHODS = (Donation.Method.CASH, Donation.Method.CARD_IN_PERSON, Donation.Method.CHECK)


class DonationError(Exception):
    """A gift could not be started or recorded; the message is shown to the person."""


def online_provider():
    """The provider that takes online gifts, or None. The sandbox exists only with DEBUG on."""
    providers = registry.online()
    return providers[0] if providers else None


def check_amount(amount_cents):
    if not isinstance(amount_cents, int) or amount_cents < settings.DONATION_MINIMUM_CENTS:
        minimum = settings.DONATION_MINIMUM_CENTS / 100
        raise DonationError(f"The smallest gift we can take online is ${minimum:,.0f}.")
    if amount_cents > settings.DONATION_MAXIMUM_CENTS:
        maximum = settings.DONATION_MAXIMUM_CENTS / 100
        raise DonationError(
            f"For gifts over ${maximum:,.0f}, please get in touch so we can thank you properly."
        )


def start_online_checkout(amount_cents, email="", show_name=False, user=None):
    """Create the pending gift and return the processor's hosted checkout URL."""
    provider = online_provider()
    if provider is None:
        raise DonationError("Online giving is not available. Please give in person or by check.")
    check_amount(amount_cents)
    show = bool(show_name and user is not None and user.is_authenticated)
    checkout = DonationCheckout.objects.create(
        amount_cents=amount_cents,
        donor=user if show else None,
        donor_display=user.display_name if show else ANONYMOUS,
        acknowledgement_email=email,
        provider=provider.key,
    )
    base = settings.SITE_URL
    try:
        session = provider.create_one_time_checkout(
            amount_cents,
            checkout.purpose,
            f"{base}/get-involved/donate?thanks=1",
            f"{base}/get-involved/donate?cancelled=1",
        )
    except ProviderError as exc:
        checkout.delete()
        raise DonationError(str(exc)) from exc
    checkout.provider_checkout_ref = session.provider_ref
    checkout.save(update_fields=["provider_checkout_ref"])
    return session.redirect_url


def _checkout_for(event):
    reference = event.purpose.partition(":")[2]
    checkout = DonationCheckout.objects.select_for_update().filter(reference=reference).first()
    if checkout is None:
        raise LookupError(f"No online gift for event {event.event_id}")
    return checkout


def apply_provider_event(provider_key, event):
    """Called by the provider event service, inside its transaction, once per event."""
    if event.type == PAYMENT_SUCCEEDED:
        checkout = _checkout_for(event)
        donation = Donation.objects.create(
            reference=checkout.reference,
            donor=checkout.donor,
            donor_display=checkout.donor_display,
            amount_cents=event.amount_cents or checkout.amount_cents,
            method=Donation.Method.ONLINE,
            status=Donation.Status.SUCCEEDED,
            provider=provider_key,
            provider_payment_ref=event.payment_ref,
            acknowledgement_requested=bool(checkout.acknowledgement_email),
        )
        if checkout.acknowledgement_email:
            acknowledgement = Acknowledgement.objects.create(
                donation=donation, email=checkout.acknowledgement_email
            )
            transaction.on_commit(lambda: send_acknowledgement_safely(acknowledgement.pk))
        checkout.acknowledgement_email = ""
        checkout.completed_at = timezone.now()
        checkout.save(update_fields=["acknowledgement_email", "completed_at"])
    elif event.type == PAYMENT_FAILED:
        checkout = _checkout_for(event)
        Donation.objects.create(
            reference=checkout.reference,
            amount_cents=event.amount_cents or checkout.amount_cents,
            method=Donation.Method.ONLINE,
            status=Donation.Status.FAILED,
            provider=provider_key,
            provider_payment_ref=event.payment_ref,
            note="Declined by the payment provider",
        )
    elif event.type == REFUNDED:
        original = Donation.objects.filter(
            provider_payment_ref=event.payment_ref, status=Donation.Status.SUCCEEDED
        ).first()
        if original is None:
            raise LookupError(f"No gift for refund event {event.event_id}")
        Donation.objects.create(
            reference=original.reference,
            amount_cents=event.amount_cents or original.amount_cents,
            method=Donation.Method.ONLINE,
            status=Donation.Status.REFUNDED,
            provider=provider_key,
            refund_of=original,
            note="Refunded through the payment provider",
        )
    # checkout_completed needs nothing: the payment event records the gift.


@transaction.atomic
def record_desk_donation(
    staff, amount_cents, method, donor_display="", acknowledgement_email="", note=""
):
    """A gift handed over at the door (cash, card or a check). Logged."""
    if method not in DESK_METHODS:
        raise DonationError("Choose cash, card or check.")
    if amount_cents <= 0:
        raise DonationError("Enter an amount.")
    email = acknowledgement_email.strip()
    if email:
        try:
            validate_email(email)
        except Exception as exc:
            raise DonationError("That email address does not look right.") from exc
    donation = Donation.objects.create(
        donor_display=" ".join(donor_display.split())[:60] or ANONYMOUS,
        amount_cents=amount_cents,
        method=method,
        recorded_by=staff,
        acknowledgement_requested=bool(email),
        note=note[:300],
    )
    if email:
        acknowledgement = Acknowledgement.objects.create(donation=donation, email=email)
        transaction.on_commit(lambda: send_acknowledgement_safely(acknowledgement.pk))
    audit(
        AuditLog.Category.DONATIONS,
        "record_donation",
        staff,
        f"Donation {donation.reference}",
        "donation",
        target_ref=donation.reference,
        reason=f"{donation.amount_display} {donation.get_method_display()}",
    )
    return donation


def render_acknowledgement(donation, template=None):
    """(subject, body) for one gift, from the staff-edited wording."""
    template = template or AcknowledgementTemplate.current()
    if template is None:
        raise DonationError("There is no acknowledgement wording yet. Add it in the admin.")
    site = SiteSettings.load()
    local = timezone.localtime(donation.created_at)
    values = {
        "legal_name": site.legal_name or "",
        "ein": site.ein or "",
        "donor_name": donation.donor_display,
        "amount": donation.amount_display,
        "date": f"{local:%B} {local.day}, {local.year}",
        "reference": donation.reference,
        "method": donation.get_method_display(),
    }

    class Blank(dict):
        def __missing__(self, key):
            return "{" + key + "}"

    return template.subject, template.body.format_map(Blank(values))


def send_acknowledgement(acknowledgement, staff=None):
    """Email the acknowledgement, then forget the address. Neutral subject."""
    if acknowledgement.emailed_at or not acknowledgement.email:
        return False
    donation = acknowledgement.donation
    if donation.status != Donation.Status.SUCCEEDED:
        return False
    subject, body = render_acknowledgement(donation)
    send_neutral_mail(subject, body, to=[acknowledgement.email])
    acknowledgement.email = ""
    acknowledgement.emailed_at = timezone.now()
    acknowledgement.save(update_fields=["email", "emailed_at"])
    audit(
        AuditLog.Category.DONATIONS,
        "acknowledgement_emailed",
        staff,
        f"Donation {donation.reference}",
        "donation",
        target_ref=donation.reference,
    )
    return True


def send_acknowledgement_safely(acknowledgement_pk):
    """After a gift: send if the wording is ready; otherwise staff send it later."""
    acknowledgement = (
        Acknowledgement.objects.select_related("donation").filter(pk=acknowledgement_pk).first()
    )
    if acknowledgement is None or AcknowledgementTemplate.current() is None:
        return False
    try:
        return send_acknowledgement(acknowledgement)
    except Exception:  # the gift is recorded either way; staff can send it from the admin
        logger.exception("Acknowledgement %s could not be sent", acknowledgement_pk)
        return False
