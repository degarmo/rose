import pytest

from apps.feed.models import Guidelines, GuidelinesAcceptance, Notification

pytestmark = pytest.mark.django_db


def test_default_guidelines_cover_the_basics():
    body = Guidelines.current().body.lower()
    for phrase in (
        "consent",
        "face",
        "license plates",
        "street signs",
        "tattoos",
        "real name",
        "screenshots",
        "respectful",
        "report",
    ):
        assert phrase in body, phrase


def test_new_version_requires_reacceptance(member_client, admin_client):
    client, member = member_client()
    assert client.get("/api/members/me/").json()["can_post"] is True
    draft = Guidelines.objects.create(title="Community guidelines", body="Updated text")
    admin_client.post(
        "/admin/feed/guidelines/", {"action": "publish", "_selected_action": [draft.pk]}
    )
    draft.refresh_from_db()
    assert Guidelines.current() == draft

    me = client.get("/api/members/me/").json()
    assert me["can_post"] is False and me["post_block_reason"] == "guidelines"
    assert client.get("/api/members/feed/").status_code == 200
    blocked = client.post("/api/members/feed/", {"caption": "Hi"}, format="multipart")
    assert blocked.status_code == 403 and blocked.json()["code"] == "guidelines"
    assert Notification.objects.filter(recipient=member, kind="guidelines").exists()

    stale = client.post(
        "/api/account/feed/guidelines/", {"guidelines_version": draft.version - 1}, format="json"
    )
    assert stale.status_code == 400
    ok = client.post(
        "/api/account/feed/guidelines/", {"guidelines_version": draft.version}, format="json"
    )
    assert ok.status_code == 200 and ok.json()["accepted_current_guidelines"] is True
    assert (
        client.post("/api/members/feed/", {"caption": "Hi"}, format="multipart").status_code == 201
    )
    assert GuidelinesAcceptance.objects.filter(user=member).count() == 2


def test_published_guidelines_are_read_only(admin_client):
    current = Guidelines.current()
    response = admin_client.get(f"/admin/feed/guidelines/{current.pk}/change/")
    assert b'name="body"' not in response.content


def test_join_flow(signed_in, make_user, private_root):
    client, user = signed_in()
    user.profile.feed_access_granted = True
    user.profile.save()
    version = Guidelines.current().version
    missing = client.post("/api/account/feed/join/", {"bio": "x"}, format="json")
    assert missing.status_code == 400
    response = client.post(
        "/api/account/feed/join/",
        {"guidelines_version": version, "bio": "Quiet one", "hide_from_directory": True},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["participating"] is True and body["can_view"] is True
    user.profile.refresh_from_db()
    assert user.profile.bio == "Quiet one" and user.profile.joined_feed_at is not None
    assert client.get("/api/members/feed/").status_code == 200
