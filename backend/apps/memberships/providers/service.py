"""Applies normalised provider events to memberships and payments.

This is the only code that changes membership state because of a payment
provider. Every event is stored in WebhookEvent first; an event id seen before
is never applied twice. Events may arrive in any order: each one finds its
membership by our reference code (or the subscription) and does only its part.

One-time payments that are not memberships (donations) carry a `purpose`
instead. They are stored and deduplicated here in exactly the same way, then
handed to the handler registered for the purpose's prefix.
"""

import logging

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from ..access import is_age_verified
from ..models import Membership, Payment, WebhookEvent
from .base import (
    CHECKOUT_COMPLETED,
    PAYMENT_FAILED,
    PAYMENT_SUCCEEDED,
    REFUNDED,
    SUBSCRIPTION_CANCELLED,
)

logger = logging.getLogger(__name__)

# purpose prefix -> callable(provider_key, event) that applies the event.
PURPOSE_HANDLERS = {
    "donation": "apps.donations.services.apply_provider_event",
}


def _apply_purpose(provider_key, event):
    prefix = event.purpose.partition(":")[0]
    if prefix not in PURPOSE_HANDLERS:
        raise LookupError(f"No handler for payment purpose {prefix!r}")
    import_string(PURPOSE_HANDLERS[prefix])(provider_key, event)


def _find_membership(event):
    memberships = Membership.objects.select_for_update(of=("self",)).select_related("tier", "user")
    if event.membership_ref:
        found = memberships.filter(reference_code=event.membership_ref).first()
        if found:
            return found
    if event.subscription_ref:
        return memberships.filter(provider_subscription_ref=event.subscription_ref).first()
    return None


def _attach_provider(membership, provider_key, event):
    membership.source = Membership.Source.PROVIDER
    membership.provider = provider_key
    if event.customer_ref:
        membership.provider_customer_ref = event.customer_ref
    if event.subscription_ref:
        membership.provider_subscription_ref = event.subscription_ref
        membership.auto_renew = not membership.cancel_at_period_end


def activate_or_extend(membership):
    """Start a period after a payment, or extend one. Activation needs an ID check."""
    now = timezone.now()
    if membership.status in (Membership.Status.ACTIVE, Membership.Status.GRACE):
        start = max(now, membership.current_period_end or now)
        end = membership.tier.period_end_from(start)
        membership.current_period_end = end
        membership.status = Membership.Status.ACTIVE
        membership.reminded_14_at = membership.reminded_3_at = membership.grace_started_at = None
        return
    if membership.user is not None and is_age_verified(membership.user):
        membership.start_new_period(now)
        membership.status = Membership.Status.ACTIVE
        membership.paid_awaiting_id_check = False
    else:
        membership.paid_awaiting_id_check = True


def _apply(provider_key, event):
    if event.purpose:
        _apply_purpose(provider_key, event)
        return
    membership = _find_membership(event)
    if membership is None:
        raise LookupError(f"No membership for event {event.event_id}")

    if event.type == CHECKOUT_COMPLETED:
        _attach_provider(membership, provider_key, event)

    elif event.type == PAYMENT_SUCCEEDED:
        _attach_provider(membership, provider_key, event)
        Payment.objects.create(
            membership=membership,
            amount_cents=event.amount_cents or 0,
            method=Payment.Method.ONLINE,
            status=Payment.Status.SUCCEEDED,
            provider_payment_ref=event.payment_ref,
        )
        activate_or_extend(membership)

    elif event.type == PAYMENT_FAILED:
        Payment.objects.create(
            membership=membership,
            amount_cents=event.amount_cents or 0,
            method=Payment.Method.ONLINE,
            status=Payment.Status.FAILED,
            provider_payment_ref=event.payment_ref,
            note="Declined by the payment provider",
        )

    elif event.type == SUBSCRIPTION_CANCELLED:
        membership.auto_renew = False
        membership.cancel_at_period_end = True

    elif event.type == REFUNDED:
        original = Payment.objects.filter(
            provider_payment_ref=event.payment_ref, status=Payment.Status.SUCCEEDED
        ).first()
        Payment.objects.create(
            membership=membership,
            amount_cents=event.amount_cents or (original.amount_cents if original else 0),
            method=Payment.Method.ONLINE,
            status=Payment.Status.REFUNDED,
            refund_of=original,
            note="Refunded through the payment provider",
        )

    membership.save()


def handle_events(provider_key, events):
    """Store, then apply, each event exactly once. Returns how many were new."""
    new = 0
    for event in events:
        try:
            with transaction.atomic():
                stored = WebhookEvent.objects.create(
                    provider=provider_key, event_id=event.event_id, payload=event.payload
                )
        except IntegrityError:
            continue  # Already received: never applied twice.
        new += 1
        try:
            with transaction.atomic():
                _apply(provider_key, event)
            stored.processed_at = timezone.now()
            stored.save(update_fields=["processed_at"])
        except Exception as exc:  # stored for staff to see; the provider still gets a 200
            logger.exception("Payment event %s could not be applied", event.event_id)
            stored.error = f"{type(exc).__name__}: {exc}"[:2000]
            stored.save(update_fields=["error"])
    return new
