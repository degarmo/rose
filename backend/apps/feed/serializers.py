"""Feed payloads. Built for one viewer at a time.

Never included anywhere: who liked something, who follows whom, follower or
like counts for anyone but a post's author, email, legal name, RSVPs, or exact
timestamps older than seven days.
"""

from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import CAPTION_MAX_LENGTH, COMMENT_MAX_LENGTH, FeedPost, Notification, Report
from .services import like_count_for
from .visibility import counted_likes, is_block_pair, visible_comments

RECENT_WINDOW = timedelta(days=7)


def posted(moment, now=None):
    """Exact time for the last week; only the month after that."""
    now = now or timezone.now()
    if now - moment <= RECENT_WINDOW:
        return {"recent": True, "at": moment.isoformat(), "month": None}
    return {"recent": False, "at": None, "month": timezone.localtime(moment).strftime("%Y-%m")}


def avatar_url(profile):
    if (
        profile.avatar
        and profile.avatar_key
        and not profile.hidden_by_report
        and profile.image_is_displayable("avatar")
    ):
        return f"/api/members/avatars/{profile.avatar_key}/"
    return None


def member_card(user):
    return {"handle": user.display_name, "avatar": avatar_url(user.profile)}


def own_state(post):
    if post.is_processing:
        return "processing"
    return post.status


class FeedImageSerializer(serializers.Serializer):
    id = serializers.CharField(source="public_id")
    url = serializers.SerializerMethodField()
    alt = serializers.CharField(source="image_alt")

    def get_url(self, image):
        return f"/api/members/media/{image.public_id}/"


class FeedPostSerializer(serializers.Serializer):
    id = serializers.CharField(source="public_id")
    author = serializers.SerializerMethodField()
    caption_html = serializers.CharField()
    caption = serializers.SerializerMethodField()
    posted = serializers.SerializerMethodField()
    edited = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    is_sensitive = serializers.BooleanField()
    blur = serializers.SerializerMethodField()
    comments_enabled = serializers.BooleanField()
    comment_count = serializers.SerializerMethodField()
    liked_by_me = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    is_own = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()

    def _viewer(self):
        return self.context["viewer"]

    def get_author(self, post):
        return member_card(post.author)

    def get_caption(self, post):
        """Raw text only for the author, who may edit it."""
        return post.caption if post.author_id == self._viewer().pk else None

    def get_posted(self, post):
        return posted(post.created_at)

    def get_edited(self, post):
        return post.edited_at is not None

    def get_images(self, post):
        images = [image for image in post.images.all() if image.image and not image.incoming]
        return FeedImageSerializer(images, many=True).data

    def get_blur(self, post):
        viewer = self._viewer()
        return (
            post.is_sensitive
            and post.author_id != viewer.pk
            and not viewer.profile.always_show_sensitive
        )

    def get_comment_count(self, post):
        return visible_comments(self._viewer(), post).count()

    def get_liked_by_me(self, post):
        liked = self.context.get("liked_ids")
        if liked is not None:
            return post.pk in liked
        return counted_likes(post).filter(user=self._viewer()).exists()

    def get_like_count(self, post):
        return like_count_for(post, self._viewer())

    def get_is_own(self, post):
        return post.author_id == self._viewer().pk

    def get_state(self, post):
        return own_state(post) if post.author_id == self._viewer().pk else None


class FeedCommentSerializer(serializers.Serializer):
    id = serializers.CharField(source="public_id")
    author = serializers.SerializerMethodField()
    body_html = serializers.CharField()
    posted = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    def get_author(self, comment):
        return member_card(comment.author)

    def get_posted(self, comment):
        return posted(comment.created_at)

    def get_can_delete(self, comment):
        viewer = self.context["viewer"]
        return viewer.pk in (comment.author_id, comment.post.author_id)


class MemberProfileSerializer(serializers.Serializer):
    handle = serializers.CharField(source="display_name")
    avatar = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    joined = serializers.SerializerMethodField()
    is_self = serializers.SerializerMethodField()
    relationship = serializers.SerializerMethodField()

    def get_avatar(self, user):
        return avatar_url(user.profile)

    def get_bio(self, user):
        return user.profile.bio

    def get_joined(self, user):
        joined = user.profile.joined_feed_at or user.date_joined
        return timezone.localtime(joined).strftime("%Y-%m")

    def get_is_self(self, user):
        return user.pk == self.context["viewer"].pk

    def get_relationship(self, user):
        """Only the viewer's own choices about this person."""
        return self.context.get("relationship")


class MeSerializer(serializers.Serializer):
    handle = serializers.CharField(source="display_name")
    avatar = serializers.SerializerMethodField()
    avatar_alt = serializers.CharField(source="profile.avatar_alt")
    bio = serializers.CharField(source="profile.bio")
    hide_from_directory = serializers.BooleanField(source="profile.hide_from_directory")
    always_show_sensitive = serializers.BooleanField(source="profile.always_show_sensitive")
    can_post = serializers.SerializerMethodField()
    post_block_reason = serializers.SerializerMethodField()
    unread_notifications = serializers.SerializerMethodField()

    def get_avatar(self, user):
        profile = user.profile
        return f"/api/members/avatars/{profile.avatar_key}/" if profile.avatar_key else None

    def get_can_post(self, user):
        return self.context["post_block_reason"] is None

    def get_post_block_reason(self, user):
        return self.context["post_block_reason"]

    def get_unread_notifications(self, user):
        return self.context["unread"]


class ProfileUpdateSerializer(serializers.Serializer):
    bio = serializers.CharField(max_length=160, required=False, allow_blank=True)
    hide_from_directory = serializers.BooleanField(required=False)
    always_show_sensitive = serializers.BooleanField(required=False)


class PostCreateSerializer(serializers.Serializer):
    caption = serializers.CharField(max_length=CAPTION_MAX_LENGTH, required=False, allow_blank=True)
    is_sensitive = serializers.BooleanField(required=False, default=False)
    comments_enabled = serializers.BooleanField(required=False, default=True)
    consent_attested = serializers.BooleanField(required=False, default=False)
    alt = serializers.ListField(
        child=serializers.CharField(max_length=200, allow_blank=True), required=False
    )


class PostEditSerializer(serializers.Serializer):
    caption = serializers.CharField(max_length=CAPTION_MAX_LENGTH, required=False, allow_blank=True)
    is_sensitive = serializers.BooleanField(required=False)
    comments_enabled = serializers.BooleanField(required=False)


class CommentCreateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=COMMENT_MAX_LENGTH)


class ReportCreateSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=Report.TargetType.choices)
    target_id = serializers.CharField(max_length=40)
    reason = serializers.ChoiceField(choices=Report.Reason.choices)
    details = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


def notification_payload(notification, viewer):
    """Text for one notification, or None when it should not be shown any more."""
    kind = notification.kind
    if kind == Notification.Kind.LIKE:
        post = notification.post
        if post is None or post.status == FeedPost.Status.REMOVED:
            return None
        count = counted_likes(post).exclude(user=viewer).count()
        if count == 0:
            return None
        text = f"{count} {'person' if count == 1 else 'people'} liked your post"
    elif kind == Notification.Kind.COMMENT:
        actor = notification.actor
        comment = notification.comment
        if (
            actor is None
            or comment is None
            or comment.status != comment.Status.VISIBLE
            or not actor.profile.participates_in_feed
            or actor.profile.is_feed_banned
            or is_block_pair(viewer, actor)
        ):
            return None
        text = f"{actor.display_name} commented on your post"
    else:
        text = notification.message
    return {
        "id": notification.pk,
        "kind": kind,
        "text": text,
        "post_id": notification.post.public_id if notification.post else None,
        "read": notification.read_at is not None,
        "posted": posted(notification.updated_at),
    }
