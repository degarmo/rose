"""Door desk actions. Every one of them is written to the audit log."""

from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone

from apps.core.models import AuditLog, audit

from . import usage
from .access import events_remaining, month_of, party_limit, tier_includes_event
from .models import IdCheck, Membership, Payment, has_id_check
from .providers import registry


class DeskError(Exception):
    """A door desk action was refused; the message is shown to staff."""


IN_PERSON_METHODS = (Payment.Method.CASH, Payment.Method.CARD_IN_PERSON)


def _log(staff, action, membership, reason=""):
    who = membership.user.display_name if membership.user else "deleted account"
    audit(
        AuditLog.Category.DOOR_DESK,
        action,
        staff,
        f"Membership {membership.reference_code} ({who})",
        "membership",
        target_user=membership.user,
        target_ref=membership.reference_code,
        reason=reason,
    )


def _lock(membership):
    return (
        Membership.objects.select_for_update(of=("self",))
        .select_related("tier", "user")
        .get(pk=membership.pk)
    )


def _ensure_id(staff, membership, id_checked):
    if has_id_check(membership.user):
        return
    if not id_checked:
        raise DeskError("Check a photo ID showing 18+ before the first activation.")
    IdCheck.objects.create(membership=membership, checked_by=staff, verified_18_plus=True)


def door_flags(user):
    """What the door must know from moderation (apps/safety): never why."""
    profile = getattr(user, "profile", None) if user else None
    if profile is None:
        return {"do_not_admit": False, "events_suspended_until": None}
    return {
        "do_not_admit": profile.do_not_admit_at is not None,
        "events_suspended_until": profile.events_suspended_until
        if profile.is_events_suspended()
        else None,
    }


def _refuse_barred(membership, checking_in=False):
    flags = door_flags(membership.user)
    if flags["do_not_admit"]:
        raise DeskError("Do not admit. Ask a member of the team.")
    if checking_in and flags["events_suspended_until"]:
        raise DeskError("Event access is suspended on this account. Ask a member of the team.")


def _refuse_guest_pass(membership):
    if membership.tier.is_guest_pass:
        raise DeskError("This is a guest pass. Use Guest visit.")


def _ensure_no_other_open(membership):
    others = (
        Membership.objects.non_terminal().filter(user=membership.user).exclude(pk=membership.pk)
    )
    if others.exists():
        raise DeskError("This person already has another open membership.")


@transaction.atomic
def record_payment_and_activate(staff, membership, method, amount_cents, note="", id_checked=False):
    membership = _lock(membership)
    _refuse_barred(membership)
    _refuse_guest_pass(membership)
    if method not in IN_PERSON_METHODS:
        raise DeskError("Choose cash or card.")
    if membership.status not in (
        Membership.Status.PENDING_PAYMENT,
        Membership.Status.EXPIRED,
        Membership.Status.CANCELLED,
    ):
        raise DeskError("This membership is already running. Use Renew instead.")
    _ensure_no_other_open(membership)
    _ensure_id(staff, membership, id_checked)
    Payment.objects.create(
        membership=membership,
        amount_cents=amount_cents,
        method=method,
        recorded_by=staff,
        note=note,
    )
    membership.start_new_period()
    membership.status = Membership.Status.ACTIVE
    membership.source = Membership.Source.MANUAL
    membership.paid_awaiting_id_check = False
    membership.cancel_at_period_end = False
    membership.save()
    _log(staff, "activate", membership, note)
    return membership


@transaction.atomic
def guest_visit(staff, membership, method, amount_cents, note="", id_checked=False):
    """One guest night: check ID if none is on file, take payment, open for one day.

    A returning guest's earlier pass (expired) is opened again, so they keep
    their account, their reference code and their ID check.
    """
    membership = _lock(membership)
    _refuse_barred(membership)
    if not membership.tier.is_guest_pass:
        raise DeskError("This is not a guest pass. Use Record payment and activate.")
    if method not in IN_PERSON_METHODS:
        raise DeskError("Choose cash or card.")
    if membership.status not in (
        Membership.Status.PENDING_PAYMENT,
        Membership.Status.EXPIRED,
        Membership.Status.CANCELLED,
    ):
        raise DeskError("This guest pass is already open for tonight.")
    if membership.user is None:
        raise DeskError("This guest pass belongs to a deleted account.")
    _ensure_no_other_open(membership)
    _ensure_id(staff, membership, id_checked)
    Payment.objects.create(
        membership=membership,
        amount_cents=amount_cents,
        method=method,
        recorded_by=staff,
        note=note,
    )
    membership.start_new_period()
    membership.status = Membership.Status.ACTIVE
    membership.source = Membership.Source.MANUAL
    membership.cancel_at_period_end = False
    membership.save()
    _log(staff, "guest_visit", membership, note)
    return membership


@transaction.atomic
def activate_paid_online(staff, membership, id_checked=False):
    """An online payment arrived before anyone saw an ID. Check it, then start the period."""
    membership = _lock(membership)
    _refuse_barred(membership)
    if not membership.paid_awaiting_id_check:
        raise DeskError("Nothing is waiting for an ID check.")
    _ensure_no_other_open(membership)
    _ensure_id(staff, membership, id_checked)
    # An imported membership already has its paid-up period end; keep it.
    if membership.current_period_end is None or membership.current_period_end <= timezone.now():
        membership.start_new_period()
    membership.status = Membership.Status.ACTIVE
    membership.paid_awaiting_id_check = False
    membership.save()
    _log(staff, "activate_after_id_check", membership)
    return membership


@transaction.atomic
def renew(staff, membership, method, amount_cents, note=""):
    """Extend from the later of today or the current period end."""
    membership = _lock(membership)
    _refuse_barred(membership)
    _refuse_guest_pass(membership)
    if method not in IN_PERSON_METHODS:
        raise DeskError("Choose cash or card.")
    if membership.status not in (
        Membership.Status.ACTIVE,
        Membership.Status.GRACE,
        Membership.Status.EXPIRED,
    ):
        raise DeskError("Only an active, grace or expired membership can be renewed here.")
    if membership.status == Membership.Status.EXPIRED:
        _ensure_no_other_open(membership)
    Payment.objects.create(
        membership=membership,
        amount_cents=amount_cents,
        method=method,
        recorded_by=staff,
        note=note,
    )
    now = timezone.now()
    start = max(now, membership.current_period_end or now)
    if (
        membership.current_period_start is None
        or membership.current_period_end is None
        or membership.current_period_end < now
    ):
        membership.current_period_start = start
    membership.current_period_end = membership.tier.period_end_from(start)
    membership.status = Membership.Status.ACTIVE
    membership.cancel_at_period_end = False
    membership.reminded_14_at = membership.reminded_3_at = membership.grace_started_at = None
    membership.save()
    _log(staff, "renew", membership, note)
    return membership


@transaction.atomic
def comp(staff, membership, reason, id_checked=False):
    if not reason.strip():
        raise DeskError("Give a reason for the complimentary membership.")
    membership = _lock(membership)
    _refuse_barred(membership)
    _refuse_guest_pass(membership)
    if membership.status in (
        Membership.Status.ACTIVE,
        Membership.Status.GRACE,
        Membership.Status.SUSPENDED,
    ):
        raise DeskError("This membership is already running.")
    _ensure_no_other_open(membership)
    _ensure_id(staff, membership, id_checked)
    Payment.objects.create(
        membership=membership,
        amount_cents=0,
        method=Payment.Method.COMP,
        recorded_by=staff,
        note=reason,
    )
    membership.start_new_period()
    membership.status = Membership.Status.ACTIVE
    membership.source = Membership.Source.COMP
    membership.paid_awaiting_id_check = False
    membership.save()
    _log(staff, "comp", membership, reason)
    return membership


@transaction.atomic
def suspend(staff, membership, reason):
    if not reason.strip():
        raise DeskError("Give a reason for suspending.")
    membership = _lock(membership)
    if membership.status not in (Membership.Status.ACTIVE, Membership.Status.GRACE):
        raise DeskError("Only an active membership can be suspended.")
    membership.status = Membership.Status.SUSPENDED
    membership.save()
    _log(staff, "suspend", membership, reason)
    return membership


@transaction.atomic
def reinstate(staff, membership, reason):
    if not reason.strip():
        raise DeskError("Give a reason for reinstating.")
    membership = _lock(membership)
    if membership.status != Membership.Status.SUSPENDED:
        raise DeskError("Only a suspended membership can be reinstated.")
    # The daily lifecycle moves it on to grace or expired if the period has passed.
    membership.status = Membership.Status.ACTIVE
    membership.save()
    _log(staff, "reinstate", membership, reason)
    return membership


@transaction.atomic
def refund(staff, payment, amount_cents, note=""):
    """A refund is a new row; the original payment is never edited."""
    payment = Payment.objects.select_related("membership").get(pk=payment.pk)
    if payment.status != Payment.Status.SUCCEEDED or payment.method == Payment.Method.COMP:
        raise DeskError("Only a successful paid payment can be refunded.")
    if amount_cents <= 0 or amount_cents > payment.amount_cents - payment.refunded_cents:
        raise DeskError("That amount is more than what is left to refund.")
    membership = payment.membership
    provider_ref = None
    if payment.method == Payment.Method.ONLINE:
        provider = registry.get(membership.provider)
        if provider is None:
            raise DeskError("The online provider for this payment is not configured.")
        provider_ref = provider.refund(payment, amount_cents)
    Payment.objects.create(
        membership=membership,
        amount_cents=amount_cents,
        method=payment.method,
        status=Payment.Status.REFUNDED,
        refund_of=payment,
        recorded_by=staff,
        note=note or ("Refunded through the provider" if provider_ref else "Refunded in person"),
    )
    _log(staff, "refund", membership, f"{amount_cents / 100:.2f} refunded. {note}".strip())
    return membership


def tonight_events(now=None):
    """Today's members-only events, for checking in members who arrive without an RSVP."""
    from apps.events.models import Event

    today = timezone.localtime(now or timezone.now()).date()
    start = timezone.make_aware(datetime.combine(today, time.min))
    return Event.objects.published().filter(
        audience=Event.Audience.MEMBERS,
        starts_at__gte=start,
        starts_at__lt=start + timedelta(days=1),
    )


@transaction.atomic
def walk_in(staff, membership, event, party_size):
    """Check a member in at tonight's members-only event without an RSVP.

    The same tier rules as an RSVP apply, and it uses one of the month's events. Someone
    already on the list is simply checked in. The audit entry never names the event.
    """
    from apps.events.models import RSVP, Event

    membership = _lock(membership)
    _refuse_barred(membership, checking_in=True)
    if not membership.is_entitled or membership.user is None:
        raise DeskError("Only an active membership can be checked in.")
    event = Event.objects.select_for_update().get(pk=event.pk)
    if not tonight_events().filter(pk=event.pk).exists():
        raise DeskError("Choose one of tonight's members-only events.")
    tier = membership.tier
    if not tier_includes_event(tier, event):
        raise DeskError(f"{tier.name} does not include this event.")
    limit = min(event.max_party_size, party_limit(tier, event))
    if not 1 <= party_size <= limit:
        raise DeskError(f"{tier.name} allows a party of {limit} at this event.")
    rsvp = RSVP.objects.filter(event=event, user=membership.user).first()
    if rsvp is not None and rsvp.status == RSVP.Status.GOING:
        rsvp.checked_in = True
        rsvp.save(update_fields=["checked_in", "updated_at"])
        _log(staff, "check_in", membership)
        return rsvp
    if events_remaining(membership, month_of(event.starts_at)) == 0:
        raise DeskError(f"No events left this month on {tier.name}.")
    if rsvp is None:
        rsvp = RSVP(event=event, user=membership.user)
    rsvp.status = RSVP.Status.GOING
    rsvp.party_size = party_size
    rsvp.waitlisted_at = None
    rsvp.checked_in = True
    rsvp.save()
    usage.sync(rsvp)
    _log(staff, "walk_in", membership)
    return rsvp


def reveal_signature_name(staff, membership):
    """The typed legal name, shown only on request, and the request is logged."""
    signature = membership.user.agreement_signatures.first() if membership.user else None
    _log(staff, "show_signature_name", membership)
    return signature.typed_name if signature else None
