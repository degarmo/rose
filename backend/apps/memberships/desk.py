"""Door desk actions. Every one of them is written to the audit log."""

from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone

from apps.core.models import AuditLog, audit

from . import usage
from .access import events_remaining, is_age_verified, month_of, party_limit, tier_includes_event
from .age import AgeCheckError, is_team_account, record_id_check, revoke_id_checks
from .models import Membership, Payment
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
    """A membership is only switched on with a valid ID check on file, or one recorded now."""
    if is_age_verified(membership.user):
        return
    if not id_checked:
        raise DeskError("Check a photo ID showing 18+ before switching this membership on.")
    try:
        record_id_check(staff, membership.user, membership)
    except AgeCheckError as exc:
        raise DeskError(str(exc)) from exc


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
def renew(staff, membership, method, amount_cents, note="", id_checked=False):
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
    _ensure_id(staff, membership, id_checked)
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
def reinstate(staff, membership, reason, id_checked=False):
    if not reason.strip():
        raise DeskError("Give a reason for reinstating.")
    membership = _lock(membership)
    if membership.status != Membership.Status.SUSPENDED:
        raise DeskError("Only a suspended membership can be reinstated.")
    _ensure_id(staff, membership, id_checked)
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


# The desk itself, shared by the admin's door desk and the staff section's
# (apps.safety.door): one search, one card and one way to run an action, so the two
# can never disagree. Every action above is logged; so is a signature reveal.

DESK_PERMISSION = "memberships.change_membership"
DONATION_METHODS = [
    ("cash", "Cash"),
    ("card_in_person", "Card in person"),
    ("check", "Check"),
]
ACTIONS = (
    "record_donation",
    "refund",
    "activate",
    "guest_visit",
    "activate_paid",
    "renew",
    "comp",
    "suspend",
    "reinstate",
    "walk_in",
    "show_signature",
    "verify",
    "revoke",
)
# Statuses where the person is, or is about to be, a member at the door.
CURRENT = (
    Membership.Status.PENDING_PAYMENT,
    Membership.Status.ACTIVE,
    Membership.Status.GRACE,
    Membership.Status.SUSPENDED,
)


def find_memberships(query):
    """By reference code (with or without its dash) or part of a display name."""
    from django.db.models import Q

    query = query.strip()
    if not query:
        return Membership.objects.none()
    code = query.upper().replace(" ", "")
    if len(code) == 6 and "-" not in code:
        code = f"{code[:3]}-{code[3:]}"
    return (
        Membership.objects.filter(Q(reference_code=code) | Q(user__display_name__icontains=query))
        .select_related("tier", "user")
        .order_by("-updated_at")[:10]
    )


def _accounts_without_membership():
    """People the desk may need to check who have no membership at all: the team, and
    people the staff granted the feed to."""
    from django.db.models import Q

    from apps.accounts.models import User

    return User.objects.filter(is_active=True, memberships__isnull=True).filter(
        Q(is_staff=True) | Q(is_superuser=True) | Q(profile__feed_access_granted=True)
    )


def find_people(query):
    """Accounts without a membership, by part of the display name (they have no code)."""
    query = query.strip()
    if len(query) < 2:
        return []
    return list(
        _accounts_without_membership()
        .filter(display_name__icontains=query)
        .select_related("profile")
        .order_by("display_name")[:10]
    )


def needing_id_check(limit=25):
    """The "Needs ID check" list: current memberships and accounts with no valid check."""
    from .models import IdCheck

    verified = IdCheck.valid().values("user_id")
    memberships = (
        Membership.objects.filter(status__in=CURRENT, user__isnull=False, user__is_active=True)
        .exclude(user__in=verified)
        .select_related("tier", "user")
        .order_by("-updated_at")[:limit]
    )
    people = (
        _accounts_without_membership()
        .exclude(pk__in=verified)
        .select_related("profile")
        .order_by("display_name")[:limit]
    )
    return list(memberships), list(people)


def witnesses_for(staff):
    """Who can witness a team member's own ID check: everyone else on the team."""
    from django.db.models import Q

    from apps.accounts.models import User

    return list(
        User.objects.filter(is_active=True)
        .filter(Q(is_staff=True) | Q(is_superuser=True))
        .exclude(pk=staff.pk)
        .order_by("display_name")
    )


def parse_amount(value):
    """Dollars as typed at the desk, in cents; None when it is not a number."""
    try:
        return max(0, round(float(value) * 100))
    except (TypeError, ValueError):
        return None


def card(membership):
    """What the door sees about one membership, and which actions it offers."""
    status = membership.status
    S = Membership.Status
    guest = membership.tier.is_guest_pass
    running = status in (S.ACTIVE, S.GRACE)
    startable = (
        status == S.PENDING_PAYMENT and not membership.paid_awaiting_id_check
    ) or status in (S.EXPIRED, S.CANCELLED)
    if guest:
        actions = ["guest_visit"] if status in (S.PENDING_PAYMENT, S.EXPIRED, S.CANCELLED) else []
    else:
        actions = []
        if membership.paid_awaiting_id_check:
            actions.append("activate_paid")
        if startable:
            actions += ["activate", "comp"]
        if running:
            actions.append("walk_in")
        if running or status == S.EXPIRED:
            actions.append("renew")
        if running:
            actions.append("suspend")
        if status == S.SUSPENDED:
            actions.append("reinstate")
    verified = is_age_verified(membership.user)
    if membership.user is not None:
        actions.append("revoke" if verified else "verify")
    return {
        "membership": membership,
        "events_remaining": None if guest else events_remaining(membership),
        "flags": door_flags(membership.user),
        "is_guest_pass": guest,
        "id_checked": verified,
        "team_account": bool(membership.user and is_team_account(membership.user)),
        "payments": list(membership.payments.all()[:5]),
        "default_amount": f"{membership.tier.price_cents / 100:.2f}",
        "actions": actions,
    }


def person_card(user):
    """What the door sees about an account with no membership: a team member, or someone
    the staff granted the feed to. The only thing to do here is the ID check."""
    verified = is_age_verified(user)
    profile = getattr(user, "profile", None)
    return {
        "person": user,
        "flags": door_flags(user),
        "id_checked": verified,
        "team_account": is_team_account(user),
        "feed_granted": bool(profile and profile.feed_access_granted),
        "actions": ["revoke" if verified else "verify"],
    }


class Outcome:
    """What an action did: a message for staff, or a revealed signature name."""

    def __init__(self, message="", signature=None):
        self.message = message
        self.signature = signature


def _checked(data):
    return str(data.get("id_checked", "")).lower() in ("on", "true", "1")


def _amount(data):
    amount = parse_amount(data.get("amount"))
    if amount is None:
        raise DeskError("Enter an amount.")
    return amount


def _person(pk):
    from apps.accounts.models import User

    user = User.objects.filter(pk=pk, is_active=True).select_related("profile").first()
    if user is None:
        raise DeskError("That account was not found.")
    return user


def _age_action(staff, action, data, user, membership):
    """Record an ID check on its own, or revoke one. Both are logged in apps.memberships.age."""
    name = user.display_name if user else "This account"
    try:
        if action == "verify":
            if not _checked(data):
                raise DeskError("Tick the box once you have seen a photo ID showing 18+.")
            witness = None
            if data.get("witness"):
                witness = _person(data.get("witness"))
            record_id_check(staff, user, membership, witness)
            return Outcome(f"{name}: ID check recorded.")
        revoke_id_checks(staff, user, data.get("reason", ""), membership)
        return Outcome(f"{name}: ID check revoked.")
    except AgeCheckError as exc:
        raise DeskError(str(exc)) from exc


def perform(staff, data):
    """Run one desk action from a submitted form or request body; DeskError if refused."""
    action = data.get("action")
    if action not in ACTIONS:
        raise DeskError("Unknown action.")
    if action == "record_donation":
        from apps.donations.services import DonationError, record_desk_donation

        amount = parse_amount(data.get("amount"))
        if not amount:
            raise DeskError("Enter an amount.")
        try:
            donation = record_desk_donation(
                staff,
                amount,
                data.get("method", ""),
                donor_display=data.get("donor_display", ""),
                acknowledgement_email=data.get("acknowledgement_email", ""),
                note=data.get("note", ""),
            )
        except DonationError as exc:
            raise DeskError(str(exc)) from exc
        return Outcome(f"Donation of {donation.amount_display} recorded.")
    if action == "refund":
        payment = Payment.objects.filter(pk=data.get("payment")).first()
        if payment is None:
            raise DeskError("That payment was not found.")
        refund(staff, payment, _amount(data), data.get("note", ""))
        return Outcome("Refund recorded.")
    if action in ("verify", "revoke") and data.get("person"):
        return _age_action(staff, action, data, _person(data.get("person")), None)
    membership = (
        Membership.objects.select_related("tier", "user").filter(pk=data.get("membership")).first()
    )
    if membership is None:
        raise DeskError("That membership was not found.")
    if action in ("verify", "revoke"):
        return _age_action(staff, action, data, membership.user, membership)
    code = membership.reference_code
    if action == "activate":
        record_payment_and_activate(
            staff,
            membership,
            data.get("method"),
            _amount(data),
            data.get("note", ""),
            _checked(data),
        )
        return Outcome(f"{code} is active.")
    if action == "guest_visit":
        guest_visit(
            staff,
            membership,
            data.get("method"),
            _amount(data),
            data.get("note", ""),
            _checked(data),
        )
        return Outcome(f"{code} is in for tonight.")
    if action == "activate_paid":
        activate_paid_online(staff, membership, _checked(data))
        return Outcome(f"{code} is active.")
    if action == "renew":
        renew(
            staff,
            membership,
            data.get("method"),
            _amount(data),
            data.get("note", ""),
            _checked(data),
        )
        return Outcome(f"{code} renewed.")
    if action == "comp":
        comp(staff, membership, data.get("reason", ""), _checked(data))
        return Outcome(f"{code} is a complimentary membership.")
    if action == "suspend":
        suspend(staff, membership, data.get("reason", ""))
        return Outcome(f"{code} is suspended.")
    if action == "reinstate":
        reinstate(staff, membership, data.get("reason", ""), _checked(data))
        return Outcome(f"{code} is reinstated.")
    if action == "walk_in":
        event = tonight_events().filter(pk=data.get("event")).first()
        if event is None:
            raise DeskError("Choose one of tonight's members-only events.")
        try:
            party_size = int(data.get("party_size", "1"))
        except (TypeError, ValueError):
            party_size = 0
        walk_in(staff, membership, event, party_size)
        return Outcome(f"{code} is checked in.")
    name = reveal_signature_name(staff, membership)
    return Outcome(signature={membership.pk: name or "No signature on file"})
