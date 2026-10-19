"""Joining: sign the agreement, then either pay at the door or check out online."""

from django.conf import settings
from django.db import IntegrityError, transaction

from . import emails
from .models import AgreementSignature, Membership, MembershipAgreement, Tier
from .providers import registry
from .providers.base import ProviderError


class JoinError(Exception):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def offered_tiers():
    tiers = Tier.objects.filter(is_active=True)
    if not settings.DEBUG:
        tiers = tiers.filter(is_placeholder=False)
    return tiers


def current_agreement():
    agreement = MembershipAgreement.current()
    if agreement is None or (agreement.is_placeholder and not settings.DEBUG):
        return None
    return agreement


def open_membership(user):
    return Membership.objects.non_terminal().filter(user=user).select_related("tier").first()


def end_guest_pass(membership):
    """Close an open guest pass: an unpaid one is cancelled, a running one has ended."""
    status = (
        Membership.Status.CANCELLED
        if membership.status == Membership.Status.PENDING_PAYMENT
        else Membership.Status.EXPIRED
    )
    membership.end(status)
    membership.save(update_fields=["status", "ended_at", "auto_renew", "updated_at"])


def payment_methods():
    methods = [{"key": "manual", "label": registry.build("manual").label, "online": False}]
    methods += [{"key": p.key, "label": p.label, "online": True} for p in registry.online()]
    return methods


def checkout_urls(membership):
    base = settings.SITE_URL
    return (
        f"{base}/join/confirming?ref={membership.reference_code}",
        f"{base}/join?cancelled=1",
    )


def start_checkout(membership, provider_key):
    provider = registry.get(provider_key)
    if provider is None or not provider.online:
        raise JoinError("method", "That payment method is not available.")
    success, cancel = checkout_urls(membership)
    try:
        session = provider.create_checkout(membership, success, cancel)
    except ProviderError as exc:
        raise JoinError("provider", str(exc), status=502) from exc
    membership.provider = provider.key
    membership.save(update_fields=["provider", "updated_at"])
    return session


def join(user, tier_slug, agreement_version, typed_name, method):
    """Returns (membership, redirect_url or None)."""
    if not user.email_verified:
        raise JoinError("unverified", "Please confirm your email first.", status=403)
    tier = offered_tiers().filter(slug=tier_slug).first()
    if tier is None:
        raise JoinError("tier", "Choose one of the options shown.")
    agreement = current_agreement()
    if agreement is None:
        raise JoinError("agreement", "Joining online is not open yet.", status=503)
    if agreement.version != agreement_version:
        raise JoinError("agreement_changed", "The agreement has changed. Please read it again.")
    typed_name = " ".join(typed_name.split())
    if len(typed_name) < 2 or len(typed_name) > 200:
        raise JoinError("typed_name", "Type your full name to sign.")
    if method not in [m["key"] for m in payment_methods()]:
        raise JoinError("method", "That payment method is not available.")
    if tier.is_guest_pass and method != "manual":
        raise JoinError("method", "Guest passes are paid at the door.")
    current = open_membership(user)
    # A guest who becomes a member gives up tonight's pass for the membership.
    replaces_guest_pass = (
        current is not None and current.tier.is_guest_pass and not tier.is_guest_pass
    )
    if current is not None and not replaces_guest_pass:
        raise JoinError(
            "exists", "You already have a membership. See your account page.", status=409
        )

    try:
        with transaction.atomic():
            if replaces_guest_pass:
                end_guest_pass(current)
            AgreementSignature.objects.create(user=user, agreement=agreement, typed_name=typed_name)
            membership = Membership.objects.create(
                user=user,
                tier=tier,
                status=Membership.Status.PENDING_PAYMENT,
                source=Membership.Source.MANUAL
                if method == "manual"
                else Membership.Source.PROVIDER,
            )
    except IntegrityError as exc:
        raise JoinError(
            "exists", "You already have a membership. See your account page.", 409
        ) from exc

    if method == "manual":
        transaction.on_commit(lambda: emails.send_reference_code(membership))
        return membership, None
    return membership, start_checkout(membership, method).redirect_url
