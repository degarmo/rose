import secrets

from django.conf import settings
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import CursorPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.accounts.models import User, feed_visible_q
from apps.core.private_media import private_media
from apps.core.text import caption_to_html

from . import access, services
from .api import FeedAPIView
from .models import Block, FeedComment, FeedImage, FeedLike, Follow, Guidelines, Mute, Notification
from .serializers import (
    CommentCreateSerializer,
    FeedCommentSerializer,
    FeedPostSerializer,
    MemberProfileSerializer,
    MeSerializer,
    PostCreateSerializer,
    PostEditSerializer,
    ProfileUpdateSerializer,
    ReportCreateSerializer,
    member_card,
    notification_payload,
)
from .visibility import (
    block_pair_ids,
    feed_posts,
    profile_by_avatar_key,
    visible_comments,
    visible_posts,
    visible_profile,
)

DIRECTORY_MIN_QUERY = 3
DIRECTORY_LIMIT = 20
NOTIFICATION_LIMIT = 50


class FeedPagination(CursorPagination):
    page_size = 10
    ordering = ("-created_at", "-pk")


def serialize_posts(request, posts):
    posts = list(posts)
    liked = set(
        FeedLike.objects.filter(user=request.user, post__in=posts).values_list("post_id", flat=True)
    )
    context = {"viewer": request.user, "liked_ids": liked}
    return FeedPostSerializer(posts, many=True, context=context).data


def paginated_posts(view, request, queryset):
    paginator = FeedPagination()
    page = paginator.paginate_queryset(
        queryset.select_related("author", "author__profile").prefetch_related("images"),
        request,
        view=view,
    )
    return paginator.get_paginated_response(serialize_posts(request, page))


def visible_notifications(user):
    rows = Notification.objects.filter(recipient=user).select_related(
        "post", "comment", "actor", "actor__profile"
    )[:NOTIFICATION_LIMIT]
    return [payload for row in rows if (payload := notification_payload(row, user))]


# Your own membership


def me_payload(request):
    context = {
        "post_block_reason": access.post_block_reason(request.user),
        "unread": sum(1 for n in visible_notifications(request.user) if not n["read"]),
    }
    return MeSerializer(request.user, context=context).data


class MeView(FeedAPIView):
    parser_classes = [JSONParser]

    def get(self, request):
        return Response(me_payload(request))

    def patch(self, request):
        serializer = ProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = request.user.profile
        for field, value in serializer.validated_data.items():
            setattr(profile, field, value.strip() if isinstance(value, str) else value)
        profile.save()
        return Response(me_payload(request))


class MyAvatarView(FeedAPIView):
    """Avatars are small, so they are cleaned in the request rather than queued."""

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("image")
        if upload is None:
            return Response({"detail": "Choose an image."}, status=status.HTTP_400_BAD_REQUEST)
        shows_face = request.data.get("shows_face") in ("true", "1", "on")
        attested = request.data.get("consent_attested") in ("true", "1", "on")
        if shows_face and not attested:
            return Response(
                {"detail": "Confirm that everyone in the picture agreed to it being used."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        services.validate_upload(upload)
        profile = request.user.profile
        old_name = profile.avatar.name
        profile.avatar = upload
        profile.avatar_alt = str(request.data.get("alt", ""))[:200]
        profile.avatar_faces_visible = shows_face
        profile.avatar_consent_confirmed = attested or not shows_face
        profile.avatar_key = secrets.token_urlsafe(12)
        profile.save()
        private_media().delete(old_name)
        return Response(me_payload(request), status=status.HTTP_201_CREATED)

    def delete(self, request):
        profile = request.user.profile
        private_media().delete(profile.avatar.name)
        profile.avatar = ""
        profile.avatar_key = ""
        profile.avatar_alt = ""
        profile.save()
        return Response(me_payload(request))


class MyBlocksView(FeedAPIView):
    """People you blocked, so you can unblock them. Never shows who blocked you."""

    def get(self, request):
        handles = Block.objects.filter(blocker=request.user).values_list(
            "blocked__display_name", flat=True
        )
        return Response({"blocked": sorted(handles, key=str.lower)})


# The feed and posts


class FeedView(FeedAPIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        tab = "following" if request.query_params.get("tab") == "following" else "everyone"
        return paginated_posts(self, request, feed_posts(request.user, tab))

    def post(self, request):
        serializer = PostCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        post = services.create_post(
            request.user,
            data.get("caption", ""),
            request.FILES.getlist("images"),
            attested=data["consent_attested"],
            is_sensitive=data["is_sensitive"],
            comments_enabled=data["comments_enabled"],
        )
        for image, alt in zip(post.images.all(), request.data.getlist("alt"), strict=False):
            image.image_alt = alt.strip()[:200]
            image.save(update_fields=["image_alt"])
        payload = serialize_posts(request, [post])[0]
        return Response(payload, status=status.HTTP_201_CREATED)


class PostDetailView(FeedAPIView):
    parser_classes = [JSONParser]

    def get_post(self, request, public_id):
        return get_object_or_404(
            visible_posts(request.user).select_related("author", "author__profile"),
            public_id=public_id,
        )

    def get(self, request, public_id):
        return Response(serialize_posts(request, [self.get_post(request, public_id)])[0])

    def patch(self, request, public_id):
        serializer = PostEditSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = services.edit_post(
            self.get_post(request, public_id), request.user, **serializer.validated_data
        )
        return Response(serialize_posts(request, [post])[0])

    def delete(self, request, public_id):
        services.delete_post(self.get_post(request, public_id), request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PostLikeView(FeedAPIView):
    def post(self, request, public_id):
        post = services.like(request.user, public_id)
        return Response(serialize_posts(request, [post])[0])

    def delete(self, request, public_id):
        post = services.unlike(request.user, public_id)
        return Response(serialize_posts(request, [post])[0])


class PostCommentsView(FeedAPIView):
    parser_classes = [JSONParser]

    def get(self, request, public_id):
        post = get_object_or_404(visible_posts(request.user), public_id=public_id)
        comments = visible_comments(request.user, post)
        return Response(
            FeedCommentSerializer(comments, many=True, context={"viewer": request.user}).data
        )

    def post(self, request, public_id):
        serializer = CommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = services.add_comment(request.user, public_id, serializer.validated_data["body"])
        return Response(
            FeedCommentSerializer(comment, context={"viewer": request.user}).data,
            status=status.HTTP_201_CREATED,
        )


class CommentDetailView(FeedAPIView):
    def delete(self, request, public_id):
        services.delete_comment(request.user, public_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


# Members


def participant_by_handle(handle):
    """Look a member up without the visibility rules, for undoing your own choices."""
    return get_object_or_404(User.objects.filter(feed_visible_q(None)), display_name__iexact=handle)


class MemberProfileView(FeedAPIView):
    def get(self, request, handle):
        user = visible_profile(request.user, handle)
        if user is None:
            raise Http404
        relationship = None
        if user != request.user:
            relationship = {
                "following": Follow.objects.filter(follower=request.user, followed=user).exists(),
                "muted": Mute.objects.filter(muter=request.user, muted=user).exists(),
            }
        context = {"viewer": request.user, "relationship": relationship}
        return Response(MemberProfileSerializer(user, context=context).data)


class MemberPostsView(FeedAPIView):
    def get(self, request, handle):
        user = visible_profile(request.user, handle)
        if user is None:
            raise Http404
        return paginated_posts(self, request, visible_posts(request.user).filter(author=user))


RELATIONSHIPS = {
    "follow": (services.follow, services.unfollow),
    "block": (services.block, services.unblock),
    "mute": (services.mute, services.unmute),
}


class MemberRelationshipView(FeedAPIView):
    def post(self, request, handle, kind):
        target = visible_profile(request.user, handle)
        if target is None or kind not in RELATIONSHIPS:
            raise Http404
        RELATIONSHIPS[kind][0](request.user, target)
        return Response({"ok": True})

    def delete(self, request, handle, kind):
        if kind not in RELATIONSHIPS:
            raise Http404
        RELATIONSHIPS[kind][1](request.user, participant_by_handle(handle))
        return Response({"ok": True})


class DirectoryView(FeedAPIView):
    """Search only. There is no way to browse the whole list."""

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < DIRECTORY_MIN_QUERY:
            return Response({"results": [], "min_query": DIRECTORY_MIN_QUERY})
        users = (
            User.objects.filter(feed_visible_q(None), display_name__icontains=query)
            .filter(profile__hide_from_directory=False, profile__hidden_by_report=False)
            .exclude(pk__in=block_pair_ids(request.user))
            .select_related("profile")
            .order_by("display_name")[:DIRECTORY_LIMIT]
        )
        return Response(
            {"results": [member_card(user) for user in users], "min_query": DIRECTORY_MIN_QUERY}
        )


class NotificationsView(FeedAPIView):
    def get(self, request):
        return Response({"results": visible_notifications(request.user)})


class NotificationsReadView(FeedAPIView):
    def post(self, request):
        Notification.objects.filter(recipient=request.user, read_at__isnull=True).update(
            read_at=timezone.now()
        )
        return Response({"ok": True})


class ReportView(FeedAPIView):
    parser_classes = [JSONParser]

    def post(self, request):
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        target_type, target_id = data["target_type"], data["target_id"]
        if target_type == "post":
            target = get_object_or_404(visible_posts(request.user), public_id=target_id)
        elif target_type == "comment":
            comment = get_object_or_404(
                FeedComment.objects.select_related("post"), public_id=target_id
            )
            if not visible_comments(request.user, comment.post).filter(pk=comment.pk).exists():
                raise Http404
            if not visible_posts(request.user).filter(pk=comment.post_id).exists():
                raise Http404
            target = comment
        else:
            target = visible_profile(request.user, target_id)
            if target is None or target == request.user:
                raise Http404
        services.report(request.user, target_type, target, data["reason"], data["details"])
        return Response({"detail": "Thanks, our team will review this."}, status=201)


class GuidelinesView(FeedAPIView):
    def get(self, request):
        current = Guidelines.current()
        if current is None:
            raise Http404
        return Response(guidelines_payload(current))


def guidelines_payload(guidelines):
    return {
        "version": guidelines.version,
        "title": guidelines.title,
        "body": guidelines.body,
        "body_html": caption_to_html(guidelines.body),
        "published_at": guidelines.published_at,
    }


# Private media


def deliver_image(request, file_name):
    media = private_media()
    if not media.exists(file_name):
        raise Http404
    if not settings.FEED_WATERMARK:
        return media.deliver(request, file_name)
    label = f"{request.user.display_name}  {timezone.localdate().isoformat()}"
    return media.deliver_watermarked(request, file_name, request.user.pk, label)


class MediaView(FeedAPIView):
    """Every request re-checks access, blocks and post status."""

    def get(self, request, public_id):
        image = (
            FeedImage.objects.filter(public_id=public_id, post__in=visible_posts(request.user))
            .exclude(image="")
            .filter(Q(incoming="") | Q(incoming__isnull=True))
            .first()
        )
        if image is None:
            raise Http404
        if not image.image_is_displayable("image") and image.post.author_id != request.user.pk:
            raise Http404
        return deliver_image(request, image.image.name)


class AvatarMediaView(FeedAPIView):
    def get(self, request, key):
        profile = profile_by_avatar_key(request.user, key)
        if profile is None or not profile.avatar:
            raise Http404
        if profile.user != request.user and (
            profile.hidden_by_report or not profile.image_is_displayable("avatar")
        ):
            raise Http404
        return deliver_image(request, profile.avatar.name)
