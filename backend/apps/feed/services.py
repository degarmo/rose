"""Business rules for the member feed. Views stay thin and call these."""

import hashlib
import json
import secrets
import zipfile
from datetime import timedelta
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile, File
from django.db import transaction
from django.utils import timezone
from PIL import Image as PILImage

from apps.core import images
from apps.core.models import AuditLog, audit
from apps.core.private_media import private_media

from . import access
from .models import (
    CAPTION_MAX_LENGTH,
    COMMENT_MAX_LENGTH,
    Block,
    DataExport,
    FeedComment,
    FeedImage,
    FeedLike,
    FeedPost,
    Follow,
    Guidelines,
    GuidelinesAcceptance,
    HiddenPost,
    ModerationActionType,
    Mute,
    Notification,
    Report,
    SavedPost,
    StorySeen,
)
from .visibility import counted_likes, visible_posts


class FeedError(Exception):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def on_commit(func):
    transaction.on_commit(func)


# Joining, leaving, guidelines


def accept_guidelines(user, version):
    current = Guidelines.current()
    if current is None or current.version != version:
        raise FeedError(
            "guidelines_changed", "The guidelines have changed. Please read them again."
        )
    GuidelinesAcceptance.objects.get_or_create(user=user, guidelines=current)


def join_feed(user, guidelines_version, bio="", hide_from_directory=True):
    if not access.can_join_feed(user):
        raise FeedError("not_allowed", "The member feed is not available.", status=404)
    if len(bio) > 160:
        raise FeedError("bio", "Keep your bio to 160 characters.")
    with transaction.atomic():
        accept_guidelines(user, guidelines_version)
        profile = user.profile
        profile.bio = bio.strip()
        profile.hide_from_directory = hide_from_directory
        if profile.joined_feed_at is None:
            profile.joined_feed_at = timezone.now()
        profile.save(update_fields=["bio", "hide_from_directory", "joined_feed_at", "updated_at"])
        profile.set_feed_participation(True)


def step_away(user):
    """Opt out: everything they made disappears for everyone, and nothing is deleted."""
    user.profile.set_feed_participation(False)


# Posting


def validate_upload(upload):
    """Checked before the raw file is stored: size, real format and pixel dimensions."""
    try:
        images.validate_upload(upload)
    except ValidationError as exc:
        code = "image_too_large" if exc.message == images.TOO_BIG else "image_invalid"
        raise FeedError(code, exc.message) from exc


def _first_posts_need_review(author):
    approved = FeedPost.objects.filter(author=author, first_published_at__isnull=False).count()
    return approved < settings.FEED_PREMODERATION_POSTS


def create_post(author, caption, uploads, attested, is_sensitive=False, comments_enabled=True):
    if not access.can_view_feed(author):
        raise FeedError("not_allowed", "Not found.", status=404)
    reason = access.post_block_reason(author)
    if reason == access.GUIDELINES:
        raise FeedError(
            "guidelines", "Please accept the updated guidelines before posting.", status=403
        )
    if reason == access.COOLDOWN:
        raise FeedError("cooldown", "Posting is paused on your account for a little while.", 403)

    caption = (caption or "").strip()
    if len(caption) > CAPTION_MAX_LENGTH:
        raise FeedError("caption", f"Keep captions to {CAPTION_MAX_LENGTH} characters.")
    if not caption and not uploads:
        raise FeedError("empty", "Write something or add a photo.")
    if len(uploads) > settings.FEED_MAX_IMAGES_PER_POST:
        raise FeedError("too_many_images", "A post can have up to 10 images.")
    if uploads and not attested:
        raise FeedError(
            "attestation",
            "Confirm that everyone identifiable in these photos agreed to them being posted.",
        )

    day_ago = timezone.now() - timedelta(days=1)
    if (
        FeedPost.objects.filter(author=author, created_at__gte=day_ago).count()
        >= settings.FEED_MAX_POSTS_PER_DAY
    ):
        raise FeedError("rate_limited", "You have reached today's posting limit.", status=429)

    for upload in uploads:
        validate_upload(upload)

    needs_review = _first_posts_need_review(author)
    with transaction.atomic():
        post = FeedPost.objects.create(
            author=author,
            caption=caption,
            is_sensitive=is_sensitive,
            comments_enabled=comments_enabled,
            status=FeedPost.Status.PENDING if needs_review else FeedPost.Status.PUBLISHED,
            is_processing=bool(uploads),
            consent_attested_at=timezone.now() if uploads else None,
            first_published_at=None if needs_review else timezone.now(),
        )
        for position, upload in enumerate(uploads):
            FeedImage.objects.create(
                post=post,
                position=position,
                incoming=File(upload, name="upload"),
                # The author attested consent for everyone identifiable.
                image_faces_visible=True,
                image_consent_confirmed=True,
            )
    if uploads:
        from .tasks import process_post_images

        on_commit(lambda: process_post_images.delay(post.pk))
    return post


def stored_size(media, name):
    """Pixel size of a processed image, read back from storage."""
    with media.storage.open(name, "rb") as stored, PILImage.open(stored) as picture:
        return picture.size


def process_images(post_id):
    """Strip metadata, re-encode to WebP and discard the raw upload."""
    post = FeedPost.objects.filter(pk=post_id).first()
    if post is None:
        return
    media = private_media()
    for image in post.images.exclude(incoming=""):
        raw_name = image.incoming.name
        try:
            with media.storage.open(raw_name, "rb") as raw:
                image.image = File(BytesIO(raw.read()), name="upload")
            image.incoming = ""
            # A savepoint per image, so one bad file cannot spoil the others.
            with transaction.atomic():
                image.save()
                image.width, image.height = stored_size(media, image.image.name)
                image.save(update_fields=["width", "height"])
        except ValidationError:
            FeedImage.objects.filter(pk=image.pk).delete()
        finally:
            media.delete(raw_name)
    post.is_processing = False
    if not post.images.exists() and not post.caption:
        post.status = FeedPost.Status.REMOVED
        post.removed_reason = "The images could not be processed."
    post.save(update_fields=["is_processing", "status", "removed_reason"])


def edit_post(post, user, caption=None, is_sensitive=None, comments_enabled=None):
    if post.author_id != user.pk:
        raise FeedError("not_found", "Not found.", status=404)
    if caption is not None:
        caption = caption.strip()
        if len(caption) > CAPTION_MAX_LENGTH:
            raise FeedError("caption", f"Keep captions to {CAPTION_MAX_LENGTH} characters.")
        if not caption and not post.images.exists():
            raise FeedError("empty", "A post without photos needs a caption.")
        post.caption = caption
    if is_sensitive is not None:
        post.is_sensitive = is_sensitive
    if comments_enabled is not None:
        post.comments_enabled = comments_enabled
    post.edited_at = timezone.now()
    post.save()
    return post


def delete_post_files(post):
    media = private_media()
    for image in post.images.all():
        media.delete(image.image.name)
        media.delete(image.incoming.name)


def delete_post(post, user):
    if post.author_id != user.pk:
        raise FeedError("not_found", "Not found.", status=404)
    delete_post_files(post)
    post.delete()


# Likes, comments and notifications


def _viewable_post(viewer, public_id):
    post = visible_posts(viewer).filter(public_id=public_id).select_related("author").first()
    if post is None:
        raise FeedError("not_found", "Not found.", status=404)
    return post


def like(viewer, public_id):
    post = _viewable_post(viewer, public_id)
    _, created = FeedLike.objects.get_or_create(post=post, user=viewer)
    if created and post.author_id != viewer.pk and post.author.profile.notify_likes:
        notification, _ = Notification.objects.get_or_create(
            recipient=post.author, post=post, kind=Notification.Kind.LIKE
        )
        notification.read_at = None
        notification.save(update_fields=["read_at", "updated_at"])
    return post


def unlike(viewer, public_id):
    post = _viewable_post(viewer, public_id)
    FeedLike.objects.filter(post=post, user=viewer).delete()
    return post


def save_post(viewer, public_id):
    """Bookmark a post this member can see. Only published posts can be saved."""
    post = _viewable_post(viewer, public_id)
    if post.status != FeedPost.Status.PUBLISHED:
        raise FeedError("not_found", "Not found.", status=404)
    SavedPost.objects.get_or_create(user=viewer, post=post)
    return post


def unsave_post(viewer, public_id):
    SavedPost.objects.filter(user=viewer, post__public_id=public_id).delete()


def hide_post(viewer, public_id):
    """Keep another member's post out of this member's feed and Explore. Nobody is told."""
    post = _viewable_post(viewer, public_id)
    if post.author_id == viewer.pk:
        raise FeedError("not_found", "Not found.", status=404)
    HiddenPost.objects.get_or_create(user=viewer, post=post)
    return post


def unhide_post(viewer, public_id):
    HiddenPost.objects.filter(user=viewer, post__public_id=public_id).delete()


def mark_stories_seen(viewer, keys):
    existing = set(
        StorySeen.objects.filter(user=viewer, key__in=keys).values_list("key", flat=True)
    )
    StorySeen.objects.bulk_create(
        [StorySeen(user=viewer, key=key) for key in keys if key not in existing],
        ignore_conflicts=True,
    )


def like_count_for(post, viewer):
    """Only the author ever learns how many people liked a post."""
    return counted_likes(post).count() if post.author_id == viewer.pk else None


def add_comment(viewer, public_id, body):
    post = _viewable_post(viewer, public_id)
    if post.status != FeedPost.Status.PUBLISHED:
        raise FeedError("not_published", "Comments open once the post is published.")
    if not post.comments_enabled:
        raise FeedError("comments_off", "Comments are turned off for this post.", status=403)
    body = (body or "").strip()
    if not body:
        raise FeedError("empty", "Write a comment first.")
    if len(body) > COMMENT_MAX_LENGTH:
        raise FeedError("too_long", f"Keep comments to {COMMENT_MAX_LENGTH} characters.")
    hour_ago = timezone.now() - timedelta(hours=1)
    if (
        FeedComment.objects.filter(author=viewer, created_at__gte=hour_ago).count()
        >= settings.FEED_MAX_COMMENTS_PER_HOUR
    ):
        raise FeedError("rate_limited", "You are commenting very quickly. Take a short break.", 429)
    comment = FeedComment.objects.create(post=post, author=viewer, body=body)
    if post.author_id != viewer.pk and post.author.profile.notify_comments:
        Notification.objects.create(
            recipient=post.author,
            kind=Notification.Kind.COMMENT,
            post=post,
            comment=comment,
            actor=viewer,
        )
    return comment


def delete_comment(viewer, public_id):
    comment = FeedComment.objects.filter(public_id=public_id).select_related("post").first()
    if comment is None or viewer.pk not in (comment.author_id, comment.post.author_id):
        raise FeedError("not_found", "Not found.", status=404)
    comment.delete()


def notify(recipient, kind, message, post=None):
    return Notification.objects.create(recipient=recipient, kind=kind, message=message, post=post)


# Follow, block, mute


def follow(viewer, target):
    if target == viewer:
        raise FeedError("self", "You cannot follow yourself.")
    Follow.objects.get_or_create(follower=viewer, followed=target)


def unfollow(viewer, target):
    Follow.objects.filter(follower=viewer, followed=target).delete()


def block(viewer, target):
    """Hide both people from each other. The blocked person is never told."""
    if target == viewer:
        raise FeedError("self", "You cannot block yourself.")
    with transaction.atomic():
        Block.objects.get_or_create(blocker=viewer, blocked=target)
        Follow.objects.filter(follower=viewer, followed=target).delete()
        Follow.objects.filter(follower=target, followed=viewer).delete()


def unblock(viewer, target):
    Block.objects.filter(blocker=viewer, blocked=target).delete()


def mute(viewer, target):
    if target == viewer:
        raise FeedError("self", "You cannot mute yourself.")
    Mute.objects.get_or_create(muter=viewer, muted=target)


def unmute(viewer, target):
    Mute.objects.filter(muter=viewer, muted=target).delete()


# Reports


def _hide(target_type, target):
    if target_type == Report.TargetType.POST and target.status == FeedPost.Status.PUBLISHED:
        target.status = FeedPost.Status.HIDDEN_BY_REPORT
        target.save(update_fields=["status"])
    elif target_type == Report.TargetType.COMMENT and target.status == FeedComment.Status.VISIBLE:
        target.status = FeedComment.Status.HIDDEN_BY_REPORT
        target.save(update_fields=["status"])
    elif target_type == Report.TargetType.PROFILE and not target.profile.hidden_by_report:
        target.profile.hidden_by_report = True
        target.profile.save(update_fields=["hidden_by_report", "updated_at"])


def _target_filter(target_type, target):
    return {
        "target_type": target_type,
        {"post": "post", "comment": "comment", "profile": "profile_user"}[target_type]: target,
    }


def report(reporter, target_type, target, reason, details=""):
    """File a report. The reporter never learns the outcome or who else reported."""
    if reason not in Report.Reason.values:
        raise FeedError("reason", "Choose a reason.")
    if reason == Report.Reason.OTHER and not details.strip():
        raise FeedError("details", "Tell us a little about what is wrong.")
    lookup = _target_filter(target_type, target)
    with transaction.atomic():
        Report.objects.get_or_create(
            reporter=reporter, **lookup, defaults={"reason": reason, "details": details.strip()}
        )
        open_reports = Report.objects.filter(**lookup, resolved_at__isnull=True)
        distinct_reporters = open_reports.values("reporter").distinct().count()
        if reason in Report.IMMEDIATE_HIDE or distinct_reporters >= Report.AUTO_HIDE_REPORTERS:
            _hide(target_type, target)


# Moderation


def _log(actor, action, target_type, target, target_user, reason=""):
    label = {
        "post": lambda t: f"Post {t.public_id} by {t.author.display_name}",
        "comment": lambda t: f"Comment {t.public_id} by {t.author.display_name}",
        "profile": lambda t: f"Profile of {t.display_name}",
        "user": lambda t: f"Member {t.display_name}",
    }[target_type](target)
    ref = getattr(target, "public_id", "") or getattr(target, "display_name", "")
    return audit(
        AuditLog.Category.MODERATION,
        action,
        actor,
        label,
        target_type,
        target_user=target_user,
        target_ref=ref,
        reason=reason,
    )


def _resolve_reports(target_type, target, resolution):
    if target_type == "user":
        return
    status = Report.Status.DISMISSED if resolution == "dismissed" else Report.Status.RESOLVED
    Report.objects.filter(**_target_filter(target_type, target), resolved_at__isnull=True).update(
        resolved_at=timezone.now(), resolution=resolution, status=status
    )


def moderate(actor, action, target_type, target, reason="", days=None):
    """Apply one moderation decision and log it. Returns the AuditLog entry."""
    A = ModerationActionType
    # Reports may have changed the target since it was loaded.
    target.refresh_from_db()
    if target_type in ("profile", "user"):
        target.profile.refresh_from_db()
    target_user = {
        "post": lambda t: t.author,
        "comment": lambda t: t.author,
        "profile": lambda t: t,
        "user": lambda t: t,
    }[target_type](target)

    with transaction.atomic():
        if action == A.APPROVE:
            if target_type == "post":
                target.status = FeedPost.Status.PUBLISHED
                target.first_published_at = target.first_published_at or timezone.now()
                target.save(update_fields=["status", "first_published_at"])
                notify(target_user, Notification.Kind.MODERATION, "Your post is now live.", target)
            elif target_type == "comment":
                target.status = FeedComment.Status.VISIBLE
                target.save(update_fields=["status"])
            elif target_type == "profile":
                target.profile.hidden_by_report = False
                target.profile.save(update_fields=["hidden_by_report", "updated_at"])
            _resolve_reports(target_type, target, "approved")

        elif action == A.REMOVE:
            if not reason.strip():
                raise FeedError("reason", "Give a reason. The member will see it.")
            if target_type == "post":
                target.status = FeedPost.Status.REMOVED
                target.removed_reason = reason
                target.removed_by = actor
                target.save(update_fields=["status", "removed_reason", "removed_by"])
                message = f"A post of yours was removed. Reason: {reason}"
            elif target_type == "comment":
                target.status = FeedComment.Status.REMOVED
                target.save(update_fields=["status"])
                message = f"A comment of yours was removed. Reason: {reason}"
            else:
                profile = target.profile
                private_media().delete(profile.avatar.name)
                profile.avatar = ""
                profile.avatar_key = ""
                profile.bio = ""
                profile.hidden_by_report = False
                profile.save()
                message = f"Your profile picture and bio were removed. Reason: {reason}"
            notify(target_user, Notification.Kind.MODERATION, message)
            _resolve_reports(target_type, target, "removed")

        elif action == A.DISMISS:
            if target_type == "post" and target.status == FeedPost.Status.HIDDEN_BY_REPORT:
                target.status = FeedPost.Status.PUBLISHED
                target.save(update_fields=["status"])
            elif target_type == "comment" and target.status == FeedComment.Status.HIDDEN_BY_REPORT:
                target.status = FeedComment.Status.VISIBLE
                target.save(update_fields=["status"])
            elif target_type == "profile" and target.profile.hidden_by_report:
                target.profile.hidden_by_report = False
                target.profile.save(update_fields=["hidden_by_report", "updated_at"])
            _resolve_reports(target_type, target, "dismissed")

        elif action == A.WARN:
            profile = target_user.profile
            profile.posting_cooldown_until = timezone.now() + timedelta(
                hours=settings.FEED_WARNING_COOLDOWN_HOURS
            )
            profile.save(update_fields=["posting_cooldown_until", "updated_at"])
            note = f" Reason: {reason}" if reason.strip() else ""
            notify(
                target_user,
                Notification.Kind.MODERATION,
                "Our team has sent you a warning, and posting is paused for "
                f"{settings.FEED_WARNING_COOLDOWN_HOURS} hours.{note}",
            )

        elif action == A.SUSPEND:
            if not days or days < 1:
                raise FeedError("days", "Choose how many days.")
            profile = target_user.profile
            profile.feed_suspended_until = timezone.now() + timedelta(days=days)
            profile.save(update_fields=["feed_suspended_until", "updated_at"])
            note = f" Reason: {reason}" if reason.strip() else ""
            notify(
                target_user,
                Notification.Kind.MODERATION,
                f"Your feed access is suspended for {days} day{'s' if days > 1 else ''}.{note}",
            )

        elif action == A.BAN:
            profile = target_user.profile
            profile.feed_banned_at = timezone.now()
            profile.save(update_fields=["feed_banned_at", "updated_at"])

        else:
            raise FeedError("action", "Unknown action.")

        return _log(actor, action, target_type, target, target_user, reason)


def staff_erase(actor, user, confirmation):
    if confirmation != user.display_name:
        raise FeedError("confirm", "Type the member's display name exactly to confirm.")
    action = _log(actor, ModerationActionType.ERASE, "user", user, user, "Erased by staff")
    from .tasks import erase_member_feed

    on_commit(lambda: erase_member_feed.delay(user.pk, notify=False))
    return action


# Erasure and export


def erase_feed_data(user):
    """Permanently delete everything a member made in the feed, including files."""
    media = private_media()
    with transaction.atomic():
        for post in FeedPost.objects.filter(author=user).prefetch_related("images"):
            delete_post_files(post)
        FeedPost.objects.filter(author=user).delete()
        FeedComment.objects.filter(author=user).delete()
        FeedLike.objects.filter(user=user).delete()
        SavedPost.objects.filter(user=user).delete()
        HiddenPost.objects.filter(user=user).delete()
        StorySeen.objects.filter(user=user).delete()
        Follow.objects.filter(follower=user).delete()
        Follow.objects.filter(followed=user).delete()
        Block.objects.filter(blocker=user).delete()
        Mute.objects.filter(muter=user).delete()
        Notification.objects.filter(recipient=user).delete()
        Notification.objects.filter(actor=user).delete()
        GuidelinesAcceptance.objects.filter(user=user).delete()
        for export in DataExport.objects.filter(user=user):
            media.delete(export.file_name)
        DataExport.objects.filter(user=user).delete()

        # Copies of other members' photos that carry this person's name.
        media.delete_viewer_copies(user.pk)

        profile = user.profile
        media.delete(profile.avatar.name)
        profile.avatar = ""
        profile.avatar_key = ""
        profile.avatar_alt = ""
        profile.bio = ""
        profile.hide_from_directory = True
        profile.always_show_sensitive = False
        profile.hidden_by_report = False
        profile.joined_feed_at = None
        profile.participates_in_feed = False
        profile.feed_status_changed_at = timezone.now()
        profile.save()


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def request_export(user):
    """Queue an export. The real link token is created by the worker and only emailed."""
    pending = DataExport.objects.filter(user=user, ready_at__isnull=True)
    if pending.exists():
        raise FeedError("pending", "An export is already being prepared.", status=409)
    # Placeholder hash until the worker mints the token; nothing can match it.
    export = DataExport.objects.create(user=user, token_hash=hash_token(secrets.token_hex(32)))
    from .tasks import build_member_export

    on_commit(lambda: build_member_export.delay(export.pk))
    return export


def _when(moment):
    return moment.isoformat() if moment else None


def _account_export(user):
    """The account's own records: settings, RSVPs and membership (dates and amounts).
    Never the email, legal name or phone: a zip travels, and those stay in Settings."""
    from apps.events.models import RSVP
    from apps.memberships.models import Membership, Payment

    profile = user.profile
    return {
        "display_name": user.display_name,
        "created_at": _when(user.date_joined),
        "pronouns": profile.pronouns,
        "appearance": user.appearance,
        "preferences": {
            "calendar_details": profile.calendar_details,
            "email_event_reminders": profile.email_event_reminders,
            "email_membership_reminders": profile.email_membership_reminders,
            "notify_likes": profile.notify_likes,
            "notify_comments": profile.notify_comments,
        },
        "rsvps": [
            {
                "event": rsvp.event.title,
                "starts_at": _when(rsvp.event.starts_at),
                "status": rsvp.status,
                "party_size": rsvp.party_size,
                "created_at": _when(rsvp.created_at),
            }
            for rsvp in RSVP.objects.filter(user=user).select_related("event")
        ],
        "memberships": [
            {
                "tier": membership.tier.name,
                "status": membership.status,
                "started_at": _when(membership.current_period_start),
                "ends_at": _when(membership.current_period_end),
            }
            for membership in Membership.objects.filter(user=user).select_related("tier")
        ],
        "payments": [
            {
                "date": _when(payment.created_at),
                "amount_cents": payment.amount_cents,
                "status": payment.status,
            }
            for payment in Payment.objects.filter(membership__user=user)
        ],
    }


def build_export(export):
    """Write the zip and return the single-use download token."""
    user = export.user
    profile = user.profile
    posts = FeedPost.objects.filter(author=user).prefetch_related("images")
    buffer = BytesIO()
    media = private_media()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        data = {
            "account": _account_export(user),
            "profile": {
                "display_name": user.display_name,
                "bio": profile.bio,
                "joined_feed_at": _when(profile.joined_feed_at),
                "hide_from_directory": profile.hide_from_directory,
                "avatar": "images/avatar.webp" if profile.avatar else None,
            },
            "posts": [],
            "comments": [
                {
                    "post": comment.post.public_id,
                    "body": comment.body,
                    "created_at": _when(comment.created_at),
                }
                for comment in FeedComment.objects.filter(author=user).select_related("post")
            ],
            "likes": [
                {"post": like.post.public_id, "created_at": _when(like.created_at)}
                for like in FeedLike.objects.filter(user=user).select_related("post")
            ],
            "saved": [
                {"post": saved.post.public_id, "created_at": _when(saved.created_at)}
                for saved in SavedPost.objects.filter(user=user).select_related("post")
            ],
            "hidden": [
                {"post": hidden.post.public_id, "created_at": _when(hidden.created_at)}
                for hidden in HiddenPost.objects.filter(user=user).select_related("post")
            ],
            "stories_seen": [
                {"story": seen.key, "seen_at": _when(seen.seen_at)}
                for seen in StorySeen.objects.filter(user=user)
            ],
        }
        if profile.avatar and media.exists(profile.avatar.name):
            archive.writestr("images/avatar.webp", media.read(profile.avatar.name))
        for post in posts:
            files = []
            for image in post.images.all():
                if image.image and media.exists(image.image.name):
                    path = f"images/{post.public_id}-{image.position + 1}.webp"
                    archive.writestr(path, media.read(image.image.name))
                    files.append({"file": path, "alt": image.image_alt})
            data["posts"].append(
                {
                    "id": post.public_id,
                    "caption": post.caption,
                    "created_at": _when(post.created_at),
                    "edited_at": _when(post.edited_at),
                    "status": post.status,
                    "is_sensitive": post.is_sensitive,
                    "images": files,
                }
            )
        archive.writestr("data.json", json.dumps(data, indent=2))

    name = media.storage.save(
        f"exports/{secrets.token_hex(16)}.zip", ContentFile(buffer.getvalue())
    )
    token = secrets.token_urlsafe(32)
    export.token_hash = hash_token(token)
    export.file_name = name
    export.ready_at = timezone.now()
    export.expires_at = export.ready_at + timedelta(hours=settings.FEED_EXPORT_TTL_HOURS)
    export.save(update_fields=["token_hash", "file_name", "ready_at", "expires_at"])
    return token


def claim_export(token):
    """Single use: the first successful claim marks it used; later ones fail."""
    with transaction.atomic():
        export = (
            DataExport.objects.select_for_update()
            .filter(token_hash=hash_token(token or ""))
            .first()
        )
        now = timezone.now()
        if (
            export is None
            or export.ready_at is None
            or export.used_at is not None
            or export.expires_at <= now
        ):
            raise FeedError("invalid", "This download link has expired or was already used.")
        export.used_at = now
        export.save(update_fields=["used_at"])
        return export
