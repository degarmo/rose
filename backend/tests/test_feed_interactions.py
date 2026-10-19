import pytest

from apps.feed import services
from apps.feed.models import Follow, Notification

pytestmark = pytest.mark.django_db


def post_url(post, suffix=""):
    return f"/api/members/posts/{post.public_id}/{suffix}"


def feed_ids(client, tab="everyone"):
    return [p["id"] for p in client.get(f"/api/members/feed/?tab={tab}").json()["results"]]


def test_like_count_only_for_author(member_client, make_post):
    author_client, author = member_client()
    post = make_post(author)
    fans = [member_client() for _ in range(3)]
    for client, _ in fans:
        response = client.post(post_url(post, "like/"))
        assert response.status_code == 200
        assert response.json()["liked_by_me"] is True
        assert response.json()["like_count"] is None
    viewer_client, _ = member_client()
    viewer_view = viewer_client.get(post_url(post)).json()
    assert viewer_view["like_count"] is None and viewer_view["liked_by_me"] is False
    assert author_client.get(post_url(post)).json()["like_count"] == 3

    fans[0][0].delete(post_url(post, "like/"))
    assert author_client.get(post_url(post)).json()["like_count"] == 2


def test_like_notifications_are_grouped_and_nameless(member_client, make_post):
    author_client, author = member_client()
    post = make_post(author, images=1)
    for _ in range(3):
        client, fan = member_client()
        client.post(post_url(post, "like/"))
    assert Notification.objects.filter(recipient=author, kind="like").count() == 1
    results = author_client.get("/api/members/notifications/").json()["results"]
    assert results[0]["text"] == "3 people liked your post"
    assert fan.display_name not in str(results)
    assert results[0]["actor"] is None
    # The author's own picture, through the access-checked media view.
    assert results[0]["thumbnail"] == f"/api/members/media/{post.images.first().public_id}/"
    assert author_client.get("/api/members/me/").json()["unread_notifications"] == 1
    author_client.post("/api/members/notifications/read/")
    assert author_client.get("/api/members/me/").json()["unread_notifications"] == 0


def test_comments_and_comment_notifications(member_client, make_post):
    author_client, author = member_client()
    post = make_post(author)
    client, commenter = member_client(display_name="kind_words")
    response = client.post(
        post_url(post, "comments/"), {"body": "Lovely <b>light</b>"}, format="json"
    )
    assert response.status_code == 201
    assert "&lt;b&gt;" in response.json()["body_html"]
    note = author_client.get("/api/members/notifications/").json()["results"][0]
    assert note["text"] == "kind_words commented on your post"
    assert note["actor"]["handle"] == "kind_words"

    comments = author_client.get(post_url(post, "comments/")).json()
    assert comments[0]["can_delete"] is True
    third, _ = member_client()
    assert third.get(post_url(post, "comments/")).json()[0]["can_delete"] is False
    assert third.delete(f"/api/members/comments/{comments[0]['id']}/").status_code == 404
    assert author_client.delete(f"/api/members/comments/{comments[0]['id']}/").status_code == 204


def test_comments_can_be_turned_off(member_client, make_post):
    _, author = member_client()
    post = make_post(author, comments_enabled=False)
    client, _ = member_client()
    response = client.post(post_url(post, "comments/"), {"body": "Hi"}, format="json")
    assert response.status_code == 403


def test_follow_tab_and_privacy(member_client, make_post):
    client, viewer = member_client()
    _, followed = member_client(display_name="followed_one")
    _, stranger = member_client()
    followed_post = make_post(followed)
    stranger_post = make_post(stranger)
    assert client.post("/api/members/u/followed_one/follow/").status_code == 200
    assert feed_ids(client, "following") == [followed_post.public_id]
    assert set(feed_ids(client)) == {followed_post.public_id, stranger_post.public_id}
    profile = client.get("/api/members/u/followed_one/").json()
    assert profile["relationship"] == {"following": True, "muted": False}
    followed_client, _ = member_client(user=followed)
    own = followed_client.get("/api/members/u/followed_one/").json()
    assert own["relationship"] is None
    me_keys = set(followed_client.get("/api/members/me/").json())
    assert not {key for key in me_keys if "follow" in key}


def test_mute_hides_from_feed_only(member_client, make_post):
    client, viewer = member_client()
    _, noisy = member_client(display_name="noisy_one")
    post = make_post(noisy)
    client.post("/api/members/u/noisy_one/mute/")
    assert post.public_id not in feed_ids(client)
    assert client.get(post_url(post)).status_code == 200
    assert client.get("/api/members/u/noisy_one/").status_code == 200
    client.delete("/api/members/u/noisy_one/mute/")
    assert post.public_id in feed_ids(client)


def test_block_is_symmetric_and_silent(member_client, make_post):
    a_client, a = member_client(display_name="alpha_one")
    b_client, b = member_client(display_name="beta_one")
    a_post = make_post(a)
    b_post = make_post(b)
    services.like(b, a_post.public_id)
    services.add_comment(b, a_post.public_id, "From b")
    services.follow(b, a)
    observer_client, _ = member_client()

    assert a_client.post("/api/members/u/beta_one/block/").status_code == 200
    assert not Follow.objects.filter(follower=b, followed=a).exists()

    for client, other_post, other in (
        (a_client, b_post, "beta_one"),
        (b_client, a_post, "alpha_one"),
    ):
        assert other_post.public_id not in feed_ids(client)
        assert client.get(post_url(other_post)).status_code == 404
        assert client.get(f"/api/members/u/{other}/").status_code == 404
    # Existing interactions between them are hidden, not deleted.
    assert a_client.get(post_url(a_post)).json()["like_count"] == 0
    assert observer_client.get(post_url(a_post, "comments/")).json() == []
    assert a_post.comments.count() == 1 and a_post.likes.count() == 1
    # B is not told: nothing in B's notifications or own view mentions it.
    assert b_client.get("/api/members/notifications/").json()["results"] == []
    assert a_client.get("/api/members/me/blocks/").json() == {"blocked": ["beta_one"]}
    assert b_client.get("/api/members/me/blocks/").json() == {"blocked": []}

    assert a_client.delete("/api/members/u/beta_one/block/").status_code == 200
    assert a_client.get(post_url(a_post)).json()["like_count"] == 1
    assert len(observer_client.get(post_url(a_post, "comments/")).json()) == 1


def test_directory_search(member_client, make_member):
    client, _ = member_client()
    listed = make_member(display_name="moonlit_lane")
    listed.profile.hide_from_directory = False
    listed.profile.save()
    make_member(display_name="moonlit_hidden")
    assert client.get("/api/members/directory/?q=mo").json()["results"] == []
    results = client.get("/api/members/directory/?q=moonlit").json()["results"]
    assert [r["handle"] for r in results] == ["moonlit_lane"]
    assert client.get("/api/members/directory/").json()["results"] == []


def test_profile_shows_month_not_date(member_client, make_member):
    client, _ = member_client()
    make_member(display_name="month_only")
    data = client.get("/api/members/u/month_only/").json()
    assert set(data) == {
        "handle",
        "avatar",
        "bio",
        "pronouns",
        "joined",
        "is_self",
        "relationship",
        "post_count",
    }
    assert len(data["joined"]) == 7


def test_opt_out_hides_everything_and_rejoin_restores(member_client, make_post, image_upload):
    from apps.feed.models import Guidelines

    leaver_client, leaver = member_client(display_name="leaving_soon")
    leaver.profile.bio = "My bio"
    leaver.profile.hide_from_directory = False
    leaver.profile.save()
    leaver_client.post(
        "/api/members/me/avatar/",
        {"image": image_upload(), "shows_face": "false"},
        format="multipart",
    )
    leaver.profile.refresh_from_db()
    avatar_url = f"/api/members/avatars/{leaver.profile.avatar_key}/"

    author_client, author = member_client()
    author_post = make_post(author)
    own_post = make_post(leaver)
    services.like(leaver, author_post.public_id)
    services.add_comment(leaver, author_post.public_id, "Nice")
    viewer_client, _ = member_client()
    assert viewer_client.get(avatar_url).status_code == 200

    response = leaver_client.post("/api/account/feed/step-away/")
    assert response.status_code == 200 and response.json()["participating"] is False

    assert own_post.public_id not in feed_ids(viewer_client)
    assert viewer_client.get(post_url(own_post)).status_code == 404
    assert viewer_client.get(post_url(author_post, "comments/")).json() == []
    assert author_client.get(post_url(author_post)).json()["like_count"] == 0
    assert viewer_client.get("/api/members/u/leaving_soon/").status_code == 404
    assert viewer_client.get(avatar_url).status_code == 404
    assert viewer_client.get("/api/members/directory/?q=leaving").json()["results"] == []
    assert author_client.get("/api/members/notifications/").json()["results"] == []
    assert leaver_client.get("/api/members/feed/").status_code == 404

    # Nothing was deleted.
    assert own_post.__class__.objects.filter(pk=own_post.pk).exists()
    assert author_post.likes.count() == 1 and author_post.comments.count() == 1

    rejoin = leaver_client.post(
        "/api/account/feed/join/",
        {
            "guidelines_version": Guidelines.current().version,
            "bio": "My bio",
            "hide_from_directory": False,
        },
        format="json",
    )
    assert rejoin.status_code == 200 and rejoin.json()["participating"] is True
    assert own_post.public_id in feed_ids(viewer_client)
    assert len(viewer_client.get(post_url(author_post, "comments/")).json()) == 1
    assert author_client.get(post_url(author_post)).json()["like_count"] == 1
    assert viewer_client.get(avatar_url).status_code == 200
    assert viewer_client.get("/api/members/u/leaving_soon/").json()["bio"] == "My bio"


def test_avatar_with_face_needs_attestation(member_client, image_upload):
    client, user = member_client()
    response = client.post(
        "/api/members/me/avatar/",
        {"image": image_upload(), "shows_face": "true"},
        format="multipart",
    )
    assert response.status_code == 400
    ok = client.post(
        "/api/members/me/avatar/",
        {"image": image_upload(), "shows_face": "true", "consent_attested": "true"},
        format="multipart",
    )
    assert ok.status_code == 201
    user.profile.refresh_from_db()
    assert user.profile.avatar_faces_visible and user.profile.avatar_consent_confirmed
    assert user.profile.avatar.name.startswith("avatars/")
