"""Donations. Financial records: append-only, like membership payments.

No donor list is ever public. `donor` is linked only when a signed-in donor
chooses to show their display name; otherwise the gift is recorded as
"Anonymous" with no link to any account. An email for an acknowledgement is
kept apart from the donation (Acknowledgement) and cleared once it is sent.
"""

import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.memberships.models import REFERENCE_ALPHABET

ANONYMOUS = "Anonymous"


def new_donation_reference():
    return "DON-" + "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(6))


class ImmutableQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Donations cannot be changed. Record a refund instead.")

    def delete(self):
        raise ValidationError("Donations cannot be deleted. Record a refund instead.")


class Donation(models.Model):
    """Append-only. A correction is a new refund row pointing at the original."""

    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        CARD_IN_PERSON = "card_in_person", "Card in person"
        ONLINE = "online", "Online"
        CHECK = "check", "Check"

    class Status(models.TextChoices):
        SUCCEEDED = "succeeded", "Received"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refund"

    reference = models.CharField(max_length=12, default=new_donation_reference, db_index=True)
    donor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="donations",
    )
    donor_display = models.CharField(max_length=60, default=ANONYMOUS)
    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="USD")
    method = models.CharField(max_length=16, choices=Method.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SUCCEEDED)
    provider = models.CharField(max_length=40, blank=True)
    # NULL, not "", for in-person gifts, so the uniqueness constraint ignores them.
    provider_payment_ref = models.CharField(max_length=120, null=True, blank=True)  # noqa: DJ001
    refund_of = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="refunds"
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    acknowledgement_requested = models.BooleanField(default=False)
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    objects = ImmutableQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider_payment_ref", "status"],
                condition=Q(provider_payment_ref__isnull=False),
                name="one_row_per_provider_donation_and_status",
            )
        ]

    def __str__(self):
        return f"{self.get_status_display()} {self.amount_display} ({self.get_method_display()})"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("Donations cannot be changed. Record a refund instead.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Donations cannot be deleted. Record a refund instead.")

    @property
    def amount_display(self):
        return f"${self.amount_cents / 100:,.2f}"


class DonationCheckout(models.Model):
    """An online gift that has been started but not yet paid.

    The webhook turns it into a Donation. Kept only for DONATION_CHECKOUT_RETENTION_DAYS.
    """

    reference = models.CharField(max_length=12, unique=True, default=new_donation_reference)
    amount_cents = models.PositiveIntegerField()
    donor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    donor_display = models.CharField(max_length=60, default=ANONYMOUS)
    acknowledgement_email = models.EmailField(blank=True)
    provider = models.CharField(max_length=40, blank=True)
    provider_checkout_ref = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Online gift {self.reference}"

    @property
    def purpose(self):
        return f"donation:{self.reference}"


class Acknowledgement(models.Model):
    """Whether a donor asked for an acknowledgement, and where it went.

    The email address is cleared as soon as the acknowledgement is sent.
    """

    donation = models.OneToOneField(
        Donation, on_delete=models.PROTECT, related_name="acknowledgement"
    )
    email = models.EmailField(blank=True)
    emailed_at = models.DateTimeField(null=True, blank=True)
    printed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Acknowledgement for {self.donation.reference}"


class AcknowledgementTemplate(models.Model):
    """The wording of every acknowledgement. Singleton (pk=1), edited by staff.

    Placeholders: {legal_name}, {ein}, {donor_name}, {amount}, {date},
    {reference} and {method}.
    """

    subject = models.CharField(
        max_length=80,
        default="Thank you for your gift",
        help_text="Keep it neutral: never the organisation's name or what it does.",
    )
    body = models.TextField(
        help_text="Plain text. Placeholders: {legal_name}, {ein}, {donor_name}, {amount}, "
        "{date}, {reference}, {method}."
    )
    is_placeholder = models.BooleanField(
        default=False,
        editable=False,
        help_text="Development-only wording. Never sent or printed with DEBUG off.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "acknowledgement wording"
        verbose_name_plural = "acknowledgement wording"

    def __str__(self):
        return "Acknowledgement wording"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("The acknowledgement wording cannot be deleted.")

    @classmethod
    def current(cls):
        """The wording, or None if there is none fit to use here."""
        template = cls.objects.filter(pk=1).first()
        if template is None or (template.is_placeholder and not settings.DEBUG):
            return None
        return template
