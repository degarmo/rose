"""Moderation casework: notes on reports, member actions, appeals and blocked emails.

Every action and every reversal is also written to the append-only core.AuditLog
(moderation category), which is the permanent record; these rows can change state
(an action is reversed, an appeal decided), the log never does.
"""

import hashlib
import hmac

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import ERASED_MEMBER


class ReportNote(models.Model):
    """An internal note on a report. Staff only; never shown to the reporter or the member."""

    report = models.ForeignKey("feed.Report", on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]

    def __str__(self):
        return f"Note on report {self.report_id}"


class MemberAction(models.Model):
    class Kind(models.TextChoices):
        WARNING = "warning", "Warning"
        REMOVE_CONTENT = "remove_content", "Remove content"
        REMOVE_ALL_CONTENT = "remove_all_content", "Remove all feed content"
        FEED_SUSPENSION = "feed_suspension", "Feed suspension"
        EVENT_SUSPENSION = "event_suspension", "Event suspension"
        BAN = "ban", "Ban"

    # Kept when the member's account is erased: the record then shows "Erased member".
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="moderation_actions",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    rule = models.CharField(max_length=200, help_text="The rule this relates to.")
    reason = models.TextField(max_length=2000)
    report = models.ForeignKey(
        "feed.Report", null=True, blank=True, on_delete=models.SET_NULL, related_name="actions"
    )
    # Remove content: what was removed and the status to restore on reversal.
    post = models.ForeignKey(
        "feed.FeedPost", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    comment = models.ForeignKey(
        "feed.FeedComment", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    previous_status = models.CharField(max_length=20, blank=True)
    # Remove all feed content: {"posts": {pk: status}, "comments": {pk: status}}, the
    # status each item had, to restore on reversal.
    removed_items = models.JSONField(default=dict, blank=True)
    # Suspensions: when they end (None for an event suspension with no end date).
    ends_at = models.DateTimeField(null=True, blank=True)
    block_email = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reversed_at = models.DateTimeField(null=True, blank=True)
    reversed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    reversal_reason = models.TextField(max_length=2000, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

    def __str__(self):
        return f"{self.get_kind_display()} #{self.pk}"

    @property
    def member_label(self):
        return self.member.display_name if self.member_id else ERASED_MEMBER

    @property
    def is_reversed(self):
        return self.reversed_at is not None

    def is_in_force(self, now=None):
        if self.is_reversed:
            return False
        return self.ends_at is None or self.ends_at > (now or timezone.now())


class Appeal(models.Model):
    """One appeal per action, from the member it was taken against."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        UPHELD = "upheld", "Upheld"
        REVERSED = "reversed", "Reversed"

    action = models.OneToOneField(MemberAction, on_delete=models.CASCADE, related_name="appeal")
    text = models.TextField(max_length=2000)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.OPEN, db_index=True
    )
    # Someone other than the moderator who acted, whenever the team allows it.
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

    def __str__(self):
        return f"Appeal on action #{self.action_id}"


def email_hash(email):
    """A keyed hash of a normalised address, so a blocked email is not stored in the clear."""
    normalised = email.strip().lower().encode()
    return hmac.new(settings.SECRET_KEY.encode(), normalised, hashlib.sha256).hexdigest()


class BlockedEmail(models.Model):
    """An address that may not register again, from a ban. Only its keyed hash is kept."""

    email_hash = models.CharField(max_length=64, unique=True)
    action = models.ForeignKey(
        MemberAction, null=True, on_delete=models.SET_NULL, related_name="blocked_emails"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "Blocked address"

    @classmethod
    def blocks(cls, email):
        return cls.objects.filter(email_hash=email_hash(email)).exists()
