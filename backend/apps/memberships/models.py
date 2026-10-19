"""Paid membership. Payment records and membership status are sensitive.

Never stored here: card data, ID numbers, dates of birth or ID images. An
IdCheck records only that staff saw a valid photo ID showing 18+.
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max, Q
from django.utils import timezone

from apps.core.text import sanitize_rich_text

# No 0/O, 1/I/L or other look-alikes, so codes survive being read aloud or written down.
REFERENCE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def new_reference_code():
    pick = lambda n: "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(n))  # noqa: E731
    return f"{pick(3)}-{pick(3)}"


class Tier(models.Model):
    class Interval(models.TextChoices):
        MONTH = "month", "Monthly"
        YEAR = "year", "Yearly"
        ONCE = "once", "One-time pass"

    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    benefits = models.JSONField(
        default=list,
        blank=True,
        help_text='Short lines, e.g. ["Weekend socials", "Members-only classes"].',
    )
    price_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="USD", editable=False)
    interval = models.CharField(max_length=5, choices=Interval.choices, default=Interval.MONTH)
    duration_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Length of a one-time pass. Required when the interval is a one-time pass.",
    )
    grants_feed_access = models.BooleanField(default=True)
    grants_members_events = models.BooleanField(default=True)
    grants_members_education = models.BooleanField(default=True)
    is_guest_pass = models.BooleanField(
        default=False,
        help_text="A one-night guest pass: a one-time pass lasting 1 day with no online "
        "access. Paid at the door, offered on the Guests page rather than with memberships.",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_placeholder = models.BooleanField(
        default=False,
        editable=False,
        help_text="Development-only demo tier. Never offered when DEBUG is off.",
    )

    class Meta:
        ordering = ["sort_order", "price_cents"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.interval == self.Interval.ONCE and not self.duration_days:
            raise ValidationError({"duration_days": "Set how many days a one-time pass lasts."})
        if self.is_guest_pass:
            if self.interval != self.Interval.ONCE or self.duration_days != 1:
                raise ValidationError(
                    {"is_guest_pass": "A guest pass is a one-time pass lasting 1 day."}
                )
            if (
                self.grants_feed_access
                or self.grants_members_events
                or (self.grants_members_education)
            ):
                raise ValidationError(
                    {
                        "is_guest_pass": "A guest pass grants no member community, members-only "
                        "events or members-only classes. Untick those three."
                    }
                )
        if not isinstance(self.benefits, list) or not all(
            isinstance(b, str) for b in self.benefits
        ):
            raise ValidationError({"benefits": "Use a list of short text lines."})

    def period_end_from(self, start):
        if self.interval == self.Interval.MONTH:
            return start + timedelta(days=30)
        if self.interval == self.Interval.YEAR:
            return start + timedelta(days=365)
        return start + timedelta(days=self.duration_days or 30)

    @property
    def entitlement_flags(self):
        flags = set()
        if self.grants_feed_access:
            flags.add("feed")
        if self.grants_members_events:
            flags.add("members_events")
        if self.grants_members_education:
            flags.add("members_education")
        return flags


class MembershipAgreement(models.Model):
    version = models.PositiveIntegerField(unique=True, editable=False)
    title = models.CharField(max_length=120, default="Membership agreement")
    body = models.TextField(
        help_text="Paragraphs, lists, bold and links. Anything else is removed."
    )
    published_at = models.DateTimeField(null=True, blank=True, editable=False)
    is_placeholder = models.BooleanField(
        default=False,
        editable=False,
        help_text="Development-only placeholder text. "
        "Joining is refused while it is current and DEBUG is off.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]

    def __str__(self):
        return f"Agreement v{self.version}{' (placeholder)' if self.is_placeholder else ''}"

    def save(self, *args, **kwargs):
        self.body = sanitize_rich_text(self.body)
        if not self.version:
            self.version = (MembershipAgreement.objects.aggregate(v=Max("version"))["v"] or 0) + 1
        super().save(*args, **kwargs)

    @classmethod
    def current(cls):
        return cls.objects.filter(published_at__isnull=False).order_by("-version").first()


class AgreementSignature(models.Model):
    """The typed full name is private: staff admin only, never serialized."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agreement_signatures"
    )
    agreement = models.ForeignKey(MembershipAgreement, on_delete=models.PROTECT, related_name="+")
    typed_name = models.CharField(max_length=200)
    signed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-signed_at"]

    def __str__(self):
        return f"Signature on agreement v{self.agreement.version}"


class MembershipQuerySet(models.QuerySet):
    def non_terminal(self):
        return self.filter(status__in=Membership.NON_TERMINAL)


class Membership(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Waiting for payment"
        ACTIVE = "active", "Active"
        GRACE = "grace", "Grace period"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"
        SUSPENDED = "suspended", "Suspended"

    class Source(models.TextChoices):
        MANUAL = "manual", "In person"
        PROVIDER = "provider", "Online"
        COMP = "comp", "Complimentary"

    NON_TERMINAL = (Status.PENDING_PAYMENT, Status.ACTIVE, Status.GRACE, Status.SUSPENDED)
    ENTITLED = (Status.ACTIVE, Status.GRACE)

    # Financial records outlive a deleted account, detached from the person.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="memberships",
    )
    tier = models.ForeignKey(Tier, on_delete=models.PROTECT, related_name="memberships")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING_PAYMENT)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=False)
    cancel_at_period_end = models.BooleanField(default=False)
    paid_awaiting_id_check = models.BooleanField(
        default=False, help_text="Paid online; becomes active once staff check a photo ID."
    )
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.MANUAL)
    provider = models.CharField(max_length=40, blank=True)
    provider_customer_ref = models.CharField(max_length=120, blank=True)
    provider_subscription_ref = models.CharField(max_length=120, blank=True, db_index=True)
    reference_code = models.CharField(
        max_length=7, unique=True, default=new_reference_code, editable=False
    )
    reminded_14_at = models.DateTimeField(null=True, blank=True, editable=False)
    reminded_3_at = models.DateTimeField(null=True, blank=True, editable=False)
    grace_started_at = models.DateTimeField(null=True, blank=True, editable=False)
    ended_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    objects = MembershipQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(status__in=["pending_payment", "active", "grace", "suspended"]),
                name="one_open_membership_per_person",
            )
        ]

    def __str__(self):
        return f"Membership {self.reference_code}"

    @property
    def is_entitled(self):
        return self.status in self.ENTITLED

    def end(self, status, when=None):
        """Move to a terminal status (expired or cancelled)."""
        self.status = status
        self.ended_at = when or timezone.now()
        self.auto_renew = False

    def start_new_period(self, start=None):
        start = start or timezone.now()
        self.current_period_start = start
        self.current_period_end = self.tier.period_end_from(start)
        self.reminded_14_at = None
        self.reminded_3_at = None
        self.grace_started_at = None
        self.ended_at = None


class ImmutableQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Payments cannot be changed. Record a refund instead.")

    def delete(self):
        raise ValidationError("Payments cannot be deleted. Record a refund instead.")


class Payment(models.Model):
    """Append-only. A correction is a new refund row pointing at the original."""

    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        CARD_IN_PERSON = "card_in_person", "Card in person"
        ONLINE = "online", "Online"
        COMP = "comp", "Complimentary"

    class Status(models.TextChoices):
        SUCCEEDED = "succeeded", "Succeeded"
        REFUNDED = "refunded", "Refund"
        FAILED = "failed", "Failed"

    membership = models.ForeignKey(Membership, on_delete=models.PROTECT, related_name="payments")
    amount_cents = models.PositiveIntegerField()
    method = models.CharField(max_length=16, choices=Method.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SUCCEEDED)
    # NULL, not "", for in-person payments, so the uniqueness constraint ignores them.
    provider_payment_ref = models.CharField(max_length=120, null=True, blank=True)  # noqa: DJ001
    refund_of = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="refunds"
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    objects = ImmutableQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider_payment_ref", "status"],
                condition=Q(provider_payment_ref__isnull=False),
                name="one_row_per_provider_payment_and_status",
            )
        ]

    def __str__(self):
        amount = f"{self.amount_cents / 100:.2f}"
        return f"{self.get_status_display()} of {amount} ({self.get_method_display()})"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("Payments cannot be changed. Record a refund instead.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Payments cannot be deleted. Record a refund instead.")

    @property
    def refunded_cents(self):
        return sum(r.amount_cents for r in self.refunds.all())


class IdCheck(models.Model):
    """Only that a valid photo ID showing 18+ was seen, by whom and when. Nothing else."""

    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="id_checks")
    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    checked_at = models.DateTimeField(auto_now_add=True)
    verified_18_plus = models.BooleanField(default=True)

    class Meta:
        ordering = ["-checked_at"]

    def __str__(self):
        return f"ID check for {self.membership.reference_code}"


def has_id_check(user):
    return IdCheck.objects.filter(membership__user=user, verified_18_plus=True).exists()


class WebhookEvent(models.Model):
    """Every provider event is stored before it is applied, which makes handling idempotent."""

    provider = models.CharField(max_length=40)
    event_id = models.CharField(max_length=120)
    payload = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-received_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "event_id"], name="one_row_per_provider_event"
            )
        ]

    def __str__(self):
        return f"{self.provider} event {self.event_id}"
