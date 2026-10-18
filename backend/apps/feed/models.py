"""The opt-in member feed.

Every query that shows feed content to someone goes through apps.feed.visibility,
which applies feed_visible_q() (opted-out or banned authors vanish), blocks and
post status. Nothing here is ever deleted by opting out; only erasure deletes.
"""

import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max, Q

from apps.core.consent_images import consented_image
from apps.core.images import RandomizedUploadTo
from apps.core.private_media import private_storage
from apps.core.text import caption_to_html

CAPTION_MAX_LENGTH = 2200
COMMENT_MAX_LENGTH = 500
REPORT_DETAILS_MAX_LENGTH = 500


def new_public_id():
    """Opaque, unguessable identifier for URLs, so ids leak nothing about volume."""
    return secrets.token_urlsafe(9)


class Guidelines(models.Model):
    """Versioned community guidelines. Members accept a version before posting."""

    version = models.PositiveIntegerField(unique=True, editable=False)
    title = models.CharField(max_length=120, default="Community guidelines")
    body = models.TextField(
        help_text="Plain text. Blank lines separate paragraphs; lines starting with '- ' "
        "become bullet points."
    )
    published_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        verbose_name_plural = "guidelines"

    def __str__(self):
        state = "published" if self.published_at else "draft"
        return f"Guidelines v{self.version} ({state})"

    def save(self, *args, **kwargs):
        if not self.version:
            latest = Guidelines.objects.aggregate(latest=Max("version"))["latest"] or 0
            self.version = latest + 1
        super().save(*args, **kwargs)

    @classmethod
    def current(cls):
        return cls.objects.filter(published_at__isnull=False).order_by("-version").first()


class GuidelinesAcceptance(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="guidelines_acceptances"
    )
    guidelines = models.ForeignKey(Guidelines, on_delete=models.PROTECT, related_name="+")
    accepted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "guidelines"], name="accept_each_version_once")
        ]

    def __str__(self):
        return f"Acceptance of guidelines v{self.guidelines.version}"


class FeedPost(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        PUBLISHED = "published", "Published"
        HIDDEN_BY_REPORT = "hidden_by_report", "Hidden by report"
        REMOVED = "removed", "Removed"

    public_id = models.CharField(max_length=16, unique=True, default=new_public_id, editable=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feed_posts"
    )
    caption = models.TextField(max_length=CAPTION_MAX_LENGTH, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_sensitive = models.BooleanField(default=False)
    comments_enabled = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    removed_reason = models.TextField(blank=True)
    removed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    is_processing = models.BooleanField(default=False)
    consent_attested_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the author confirmed everyone identifiable agreed to be posted.",
    )
    first_published_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [models.Index(fields=["status", "-created_at"])]

    def __str__(self):
        return f"Post {self.public_id} by {self.author.display_name}"

    @property
    def caption_html(self):
        return caption_to_html(self.caption)


class FeedImage(
    consented_image(
        "image", upload_to="feed", storage=private_storage, alt_required=False, required=False
    )
):
    """One image in a post. Raw uploads wait in `incoming` until a worker strips them."""

    private_media = True

    public_id = models.CharField(max_length=16, unique=True, default=new_public_id, editable=False)
    post = models.ForeignKey(FeedPost, on_delete=models.CASCADE, related_name="images")
    position = models.PositiveSmallIntegerField(default=0)
    incoming = models.FileField(
        upload_to=RandomizedUploadTo("incoming"), storage=private_storage, blank=True
    )

    class Meta:
        ordering = ["position", "pk"]

    def __str__(self):
        return f"Image {self.position + 1} of {self.post.public_id}"

    def consent_publish_state(self):
        return self.post.status == FeedPost.Status.PUBLISHED


class FeedLike(models.Model):
    post = models.ForeignKey(FeedPost, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feed_likes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["post", "user"], name="like_once")]

    def __str__(self):
        return f"Like #{self.pk}"


class FeedComment(models.Model):
    class Status(models.TextChoices):
        VISIBLE = "visible", "Visible"
        HIDDEN_BY_REPORT = "hidden_by_report", "Hidden by report"
        REMOVED = "removed", "Removed"

    public_id = models.CharField(max_length=16, unique=True, default=new_public_id, editable=False)
    post = models.ForeignKey(FeedPost, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feed_comments"
    )
    body = models.TextField(max_length=COMMENT_MAX_LENGTH)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.VISIBLE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]

    def __str__(self):
        return f"Comment {self.public_id} by {self.author.display_name}"

    @property
    def body_html(self):
        return caption_to_html(self.body)


class Follow(models.Model):
    """Private: no counts or lists are ever shown, not even to the person followed."""

    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    followed = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["follower", "followed"], name="follow_once"),
            models.CheckConstraint(
                condition=~Q(follower=models.F("followed")), name="no_self_follow"
            ),
        ]

    def __str__(self):
        # Neutral on purpose: relationships are never displayed.
        return f"Follow #{self.pk}"


class Block(models.Model):
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["blocker", "blocked"], name="block_once"),
            models.CheckConstraint(condition=~Q(blocker=models.F("blocked")), name="no_self_block"),
        ]

    def __str__(self):
        # Neutral on purpose: relationships are never displayed.
        return f"Block #{self.pk}"


class Mute(models.Model):
    muter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    muted = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["muter", "muted"], name="mute_once"),
            models.CheckConstraint(condition=~Q(muter=models.F("muted")), name="no_self_mute"),
        ]

    def __str__(self):
        # Neutral on purpose: relationships are never displayed.
        return f"Mute #{self.pk}"


class Notification(models.Model):
    """In-app only. Likes are one grouped row per post with a live, nameless count."""

    class Kind(models.TextChoices):
        LIKE = "like", "Likes on your post"
        COMMENT = "comment", "Comment on your post"
        MODERATION = "moderation", "Moderation outcome"
        GUIDELINES = "guidelines", "Guidelines updated"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feed_notifications"
    )
    kind = models.CharField(max_length=12, choices=Kind.choices)
    post = models.ForeignKey(FeedPost, null=True, blank=True, on_delete=models.CASCADE)
    comment = models.ForeignKey(FeedComment, null=True, blank=True, on_delete=models.CASCADE)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )
    message = models.CharField(max_length=400, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["recipient", "post"],
                condition=Q(kind="like"),
                name="one_like_notification_per_post",
            )
        ]

    def __str__(self):
        return f"{self.get_kind_display()} notification"


class Report(models.Model):
    class TargetType(models.TextChoices):
        POST = "post", "Post"
        COMMENT = "comment", "Comment"
        PROFILE = "profile", "Profile"

    class Reason(models.TextChoices):
        NO_CONSENT = "no_consent", "Posted without consent"
        IDENTIFIES = "identifies", "Identifies someone"
        HARASSMENT = "harassment", "Harassment"
        UNDER_18 = "under_18", "May involve someone under 18"
        SPAM = "spam", "Spam"
        OTHER = "other", "Other"

    # Reasons that hide the content straight away, before anyone reviews it.
    IMMEDIATE_HIDE = frozenset({Reason.NO_CONSENT, Reason.UNDER_18})
    AUTO_HIDE_REPORTERS = 3

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    target_type = models.CharField(max_length=10, choices=TargetType.choices)
    post = models.ForeignKey(
        FeedPost, null=True, blank=True, on_delete=models.CASCADE, related_name="reports"
    )
    comment = models.ForeignKey(
        FeedComment, null=True, blank=True, on_delete=models.CASCADE, related_name="reports"
    )
    profile_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )
    reason = models.CharField(max_length=12, choices=Reason.choices)
    details = models.TextField(max_length=REPORT_DETAILS_MAX_LENGTH, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["reporter", "post"],
                condition=Q(target_type="post"),
                name="report_post_once",
            ),
            models.UniqueConstraint(
                fields=["reporter", "comment"],
                condition=Q(target_type="comment"),
                name="report_comment_once",
            ),
            models.UniqueConstraint(
                fields=["reporter", "profile_user"],
                condition=Q(target_type="profile"),
                name="report_profile_once",
            ),
        ]

    def __str__(self):
        return f"{self.get_reason_display()} report on {self.target_type}"

    @property
    def target(self):
        return {"post": self.post, "comment": self.comment, "profile": self.profile_user}[
            self.target_type
        ]


class ImmutableQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Moderation actions cannot be changed.")

    def delete(self):
        raise ValidationError("Moderation actions cannot be deleted.")


class ModerationAction(models.Model):
    """Append-only log of every moderation decision."""

    class Action(models.TextChoices):
        APPROVE = "approve", "Approve"
        REMOVE = "remove", "Remove"
        DISMISS = "dismiss", "Dismiss report"
        WARN = "warn", "Warn"
        SUSPEND = "suspend", "Suspend"
        BAN = "ban", "Ban"
        ERASE = "erase", "Erase member content"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    actor_label = models.CharField(max_length=30)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    target_label = models.CharField(max_length=120)
    target_type = models.CharField(max_length=10)
    target_ref = models.CharField(max_length=32, blank=True)
    action = models.CharField(max_length=10, choices=Action.choices)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ImmutableQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-pk"]

    def __str__(self):
        return f"{self.get_action_display()}: {self.target_label} by {self.actor_label}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("Moderation actions cannot be changed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Moderation actions cannot be deleted.")


class DataExport(models.Model):
    """A member's zip download. The link token is stored only as a hash."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feed_exports"
    )
    token_hash = models.CharField(max_length=64, unique=True)
    file_name = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Data export #{self.pk}"
