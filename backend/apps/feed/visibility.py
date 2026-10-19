"""What a given member can see. Feed content never bypasses these helpers."""

from django.db.models import Q

from apps.accounts.models import Profile, User, feed_visible_q

from .models import Block, FeedComment, FeedLike, FeedPost, HiddenPost, Mute


def block_pair_ids(user):
    """Everyone this person blocked or was blocked by. Blocks hide both ways."""
    pairs = Block.objects.filter(Q(blocker=user) | Q(blocked=user)).values_list(
        "blocker_id", "blocked_id"
    )
    return {a if b == user.pk else b for a, b in pairs}


def muted_ids(user):
    return set(Mute.objects.filter(muter=user).values_list("muted_id", flat=True))


def is_block_pair(user_a, user_b):
    return Block.objects.filter(
        Q(blocker=user_a, blocked=user_b) | Q(blocker=user_b, blocked=user_a)
    ).exists()


def visible_posts(viewer):
    """Posts this member may open: published ones, plus their own work in progress."""
    published = Q(status=FeedPost.Status.PUBLISHED, is_processing=False)
    own = Q(author=viewer) & ~Q(status=FeedPost.Status.REMOVED)
    return (
        FeedPost.objects.filter(feed_visible_q("author"))
        .filter(published | own)
        .exclude(author_id__in=block_pair_ids(viewer))
    )


def feed_posts(viewer, tab="everyone"):
    """The scrolling feed: visible posts minus muted members and posts the viewer hid."""
    posts = (
        visible_posts(viewer)
        .exclude(author_id__in=muted_ids(viewer))
        .exclude(pk__in=HiddenPost.objects.filter(user=viewer).values("post_id"))
    )
    if tab == "following":
        from .models import Follow

        followed = Follow.objects.filter(follower=viewer).values_list("followed_id", flat=True)
        posts = posts.filter(Q(author_id__in=followed) | Q(author=viewer))
    return posts


def visible_comments(viewer, post):
    """Comments any viewer may see, minus anyone in a block with the viewer or author."""
    hidden_people = block_pair_ids(viewer) | block_pair_ids(post.author)
    return (
        FeedComment.objects.filter(post=post, status=FeedComment.Status.VISIBLE)
        .filter(feed_visible_q("author"))
        .exclude(author_id__in=hidden_people - {post.author_id})
        .select_related("author", "author__profile")
    )


def counted_likes(post):
    """Likes that count: from visible members not in a block with the author."""
    return (
        FeedLike.objects.filter(post=post)
        .filter(feed_visible_q("user"))
        .exclude(user_id__in=block_pair_ids(post.author))
    )


def visible_profile(viewer, handle):
    """A member profile this viewer may open, or None."""
    user = (
        User.objects.filter(feed_visible_q(None), display_name__iexact=handle)
        .select_related("profile")
        .first()
    )
    if user is None:
        return None
    if user != viewer and (user.profile.hidden_by_report or is_block_pair(viewer, user)):
        return None
    return user


def profile_by_avatar_key(viewer, key):
    profile = (
        Profile.objects.filter(avatar_key=key).exclude(avatar_key="").select_related("user").first()
    )
    if profile is None:
        return None
    return profile if visible_profile(viewer, profile.user.display_name) else None
