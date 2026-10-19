"""A member's own controls: cancel, auto-renew, and closing on account deletion."""

from django.db import transaction

from .models import Membership
from .providers import registry
from .providers.base import ProviderError


class AccountError(Exception):
    """A member's own action was refused; the message is shown to them."""


def _provider_for(membership):
    if membership.source != Membership.Source.PROVIDER or not membership.provider:
        return None
    return registry.get(membership.provider)


@transaction.atomic
def cancel(membership):
    """Pending: cancelled now. Running: ends at period end, with no more reminders."""
    membership = (
        Membership.objects.select_for_update(of=("self",))
        .select_related("tier")
        .get(pk=membership.pk)
    )
    # Nothing has been paid on an unpaid code or a free tier waiting for its ID check.
    if membership.status == Membership.Status.PENDING_PAYMENT and (
        not membership.paid_awaiting_id_check or membership.tier.is_free
    ):
        membership.end(Membership.Status.CANCELLED)
        membership.save()
        return membership
    if membership.status not in (Membership.Status.ACTIVE, Membership.Status.GRACE):
        raise AccountError("This membership cannot be cancelled.")
    provider = _provider_for(membership)
    if provider is not None and membership.provider_subscription_ref:
        provider.cancel_subscription(membership)
    membership.cancel_at_period_end = True
    membership.auto_renew = False
    membership.save()
    return membership


@transaction.atomic
def set_auto_renew(membership, enabled):
    membership = Membership.objects.select_for_update().get(pk=membership.pk)
    provider = _provider_for(membership)
    if provider is None or not membership.provider_subscription_ref:
        raise AccountError("Automatic renewal is only for online memberships.")
    if membership.status not in (Membership.Status.ACTIVE, Membership.Status.GRACE):
        raise AccountError("This membership is not running.")
    try:
        if enabled:
            provider.resume_subscription(membership)
        else:
            provider.cancel_subscription(membership)
    except ProviderError as exc:
        raise AccountError(str(exc)) from exc
    membership.auto_renew = enabled
    membership.cancel_at_period_end = not enabled
    membership.save()
    return membership


def close_for_deleted_account(user):
    """Stop online renewals and end any open membership. Payment records stay, detached."""
    for membership in Membership.objects.non_terminal().filter(user=user):
        provider = _provider_for(membership)
        if provider is not None and membership.provider_subscription_ref:
            provider.cancel_subscription(membership)
        membership.end(Membership.Status.CANCELLED)
        membership.save()
