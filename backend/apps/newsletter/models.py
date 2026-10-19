"""The email list: double opt-in subscribers, staff-written newsletters, and
suppression records for people who left.

Subscribers are kept apart from accounts, even when the same address has one.
No open or click tracking, ever.
"""

import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.text import sanitize_rich_text


def new_token():
    return secrets.token_urlsafe(24)


def email_hash(email):
    """Salted hash of a normalised address, for suppression records."""
    normalised = email.strip().lower()
    return hashlib.sha256(f"{settings.SECRET_KEY}:suppress:{normalised}".encode()).hexdigest()


class Subscriber(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Waiting for confirmation"
        CONFIRMED = "confirmed", "Confirmed"
        UNSUBSCRIBED = "unsubscribed", "Unsubscribed"

    email = models.EmailField(unique=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    # Confirms and unsubscribes without a login. Replaced on every new sign-up.
    token = models.CharField(max_length=64, unique=True, default=new_token, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Subscriber #{self.pk}"

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


class Suppression(models.Model):
    """Someone who unsubscribed: only a hash of their address and the date."""

    email_hash = models.CharField(max_length=64, unique=True)
    unsubscribed_on = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Suppressed since {self.unsubscribed_on:%Y-%m-%d}"


class Newsletter(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        SENT = "sent", "Sent"

    subject = models.CharField(
        max_length=120,
        help_text="Keep it neutral: never the organisation's name, its activities or "
        "anything you would not want on a shared screen.",
    )
    preheader = models.CharField(
        max_length=150,
        blank=True,
        help_text="The grey line many inboxes show after the subject. Neutral too.",
    )
    body = models.TextField(
        help_text="Paragraphs, lists, bold and links. Anything else is removed on save."
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    scheduled_at = models.DateTimeField(
        null=True, blank=True, help_text="Chicago time. Used when the status is Scheduled."
    )
    send_started_at = models.DateTimeField(null=True, blank=True, editable=False)
    sent_at = models.DateTimeField(null=True, blank=True, editable=False)
    sent_count = models.PositiveIntegerField(default=0, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.subject

    def save(self, *args, **kwargs):
        self.body = sanitize_rich_text(self.body)
        super().save(*args, **kwargs)
