"""Demo feed content for local development. seed_demo only calls this when DEBUG is on."""

import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.pages.management.commands.demo_media import sample_image

from . import services
from .models import (
    Block,
    FeedComment,
    FeedImage,
    FeedLike,
    FeedPost,
    Follow,
    Guidelines,
    GuidelinesAcceptance,
    Notification,
    Report,
)

PARTICIPANTS = [
    "ember_and_ash",
    "velvet_hour",
    "quiet_lantern",
    "silk_and_iron",
    "midnight_reader",
    "brass_key",
    "low_tide",
    "demo_member",
]
CAPTIONS = [
    "Candlelight and a good book after the Thursday class.",
    "The parlor after everyone left. My favourite hour.",
    "New gloves. Very pleased with them.",
    "Thank you to whoever brought the tea last night.",
    "Practising the knots from the workshop at home.",
    "Rain on the window, music on low.",
    "Quiet corner, warm light, no rush.",
    "First time hosting at the door. Everyone was lovely.",
    "A small ritual: one lamp, one chair, one evening to myself.",
    "Textures I keep coming back to.",
]
COMMENTS = [
    "This is lovely.",
    "Beautiful light.",
    "Agreed, what a night.",
    "Thank you for sharing.",
]


def _member(email, display_name, participating=True):
    user = User.objects.filter(email=email).first()
    if user is None:
        user = User.objects.create_user(
            email=email, display_name=display_name, password=secrets.token_urlsafe(16)
        )
    user.mark_email_verified()
    profile = user.profile
    profile.feed_access_granted = True
    profile.feed_access_granted_at = profile.feed_access_granted_at or timezone.now()
    profile.joined_feed_at = profile.joined_feed_at or timezone.now() - timedelta(days=60)
    profile.hide_from_directory = display_name.endswith(("hour", "reader"))
    profile.bio = "Here for the classes, staying for the people."
    profile.save()
    profile.set_feed_participation(participating)
    GuidelinesAcceptance.objects.get_or_create(user=user, guidelines=Guidelines.current())
    return user


def _post(author, caption, images, age, sensitive=False, status=FeedPost.Status.PUBLISHED, seed=0):
    created = timezone.now() - age
    post = FeedPost.objects.create(
        author=author,
        caption=caption,
        is_sensitive=sensitive,
        status=status,
        consent_attested_at=created if images else None,
        first_published_at=created if status == FeedPost.Status.PUBLISHED else None,
    )
    FeedPost.objects.filter(pk=post.pk).update(created_at=created)
    for position in range(images):
        picture = sample_image(seed * 7 + position, width=720)
        FeedImage.objects.create(
            post=post,
            position=position,
            image=picture.file,
            image_alt=picture.alt,
            image_faces_visible=True,
            image_consent_confirmed=True,
            width=picture.width,
            height=picture.height,
        )
    return post


@transaction.atomic
def seed_feed(demo_verified):
    """Returns the demo member account so its password can be set."""
    if FeedPost.objects.filter(author__display_name__in=PARTICIPANTS).exists():
        demo_member = User.objects.get(display_name="demo_member")
        _demo_member_activity(demo_member)
        return demo_member

    members = [
        _member("demo.member@example.org" if name == "demo_member" else f"{name}@example.org", name)
        for name in PARTICIPANTS
    ]
    opted_out = _member("stepped_away@example.org", "stepped_away")
    banned = _member("banned_one@example.org", "banned_one")
    pending_author = _member("brand_new@example.org", "brand_new")

    # The verified demo account is entitled but has not joined, to try the join flow.
    profile = demo_verified.profile
    profile.feed_access_granted = True
    profile.feed_access_granted_at = profile.feed_access_granted_at or timezone.now()
    profile.save()

    posts = []
    for index in range(30):
        author = members[index % len(members)]
        posts.append(
            _post(
                author,
                CAPTIONS[index % len(CAPTIONS)],
                images=[1, 1, 2, 3, 0][index % 5],
                age=timedelta(hours=index * 9 + 1),
                sensitive=index % 7 == 3,
                seed=index,
            )
        )
    _post(opted_out, "From before I stepped away.", 1, timedelta(days=20), seed=40)
    _post(banned, "This should never be visible.", 1, timedelta(days=10), seed=41)
    for offset in range(2):
        _post(
            pending_author,
            "My first post, waiting for review.",
            1,
            timedelta(hours=offset + 1),
            status=FeedPost.Status.PENDING,
            seed=50 + offset,
        )
    opted_out.profile.set_feed_participation(False)
    banned.profile.feed_banned_at = timezone.now()
    banned.profile.save()

    for index, post in enumerate(posts):
        for liker in members[: (index % 5) + 1]:
            if liker != post.author:
                FeedLike.objects.get_or_create(post=post, user=liker)
        if index % 3 == 0:
            commenter = members[(index + 2) % len(members)]
            if commenter != post.author:
                FeedComment.objects.create(
                    post=post, author=commenter, body=COMMENTS[index % len(COMMENTS)]
                )

    for follower in members:
        for followed in members[:3]:
            if follower != followed:
                Follow.objects.get_or_create(follower=follower, followed=followed)
    Block.objects.get_or_create(blocker=members[1], blocked=members[2])

    hidden_target = posts[5]
    Report.objects.create(
        reporter=members[0],
        target_type=Report.TargetType.POST,
        post=hidden_target,
        reason=Report.Reason.NO_CONSENT,
        details="I am in the background of this photo.",
    )
    hidden_target.status = FeedPost.Status.HIDDEN_BY_REPORT
    hidden_target.save(update_fields=["status"])
    Report.objects.create(
        reporter=members[3],
        target_type=Report.TargetType.POST,
        post=posts[8],
        reason=Report.Reason.SPAM,
    )
    _demo_member_activity(members[-1])
    return members[-1]


def _demo_member_activity(demo_member):
    """Saved posts and notifications for the demo member, so those screens have content."""
    others = FeedPost.objects.filter(status=FeedPost.Status.PUBLISHED).exclude(author=demo_member)
    for post in others.order_by("-created_at")[:4]:
        services.save_post(demo_member, post.public_id)
    own = FeedPost.objects.filter(author=demo_member, status=FeedPost.Status.PUBLISHED)
    fans = User.objects.filter(display_name__in=PARTICIPANTS).exclude(pk=demo_member.pk)
    for post in own.order_by("-created_at")[:3]:
        for fan in fans[:4]:
            services.like(fan, post.public_id)
        if not post.comments.exclude(author=demo_member).exists():
            # Directly rather than through add_comment, whose hourly limit the seed would hit.
            comment = FeedComment.objects.create(post=post, author=fans[0], body=COMMENTS[0])
            Notification.objects.create(
                recipient=demo_member,
                kind=Notification.Kind.COMMENT,
                post=post,
                comment=comment,
                actor=fans[0],
            )
