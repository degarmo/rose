import json
import zipfile
from datetime import timedelta
from io import BytesIO

import pytest
from django.core import mail
from django.utils import timezone

from apps.accounts.models import User
from apps.feed import services, tasks
from apps.feed.models import (
    Block,
    DataExport,
    FeedComment,
    FeedLike,
    FeedPost,
    Follow,
    GuidelinesAcceptance,
    Mute,
    Notification,
)

from .conftest import PASSWORD

pytestmark = pytest.mark.django_db


@pytest.fixture
def busy_member(member_client, make_post, image_upload, private_root):
    client, member = member_client(display_name="busy_member")
    client.post(
        "/api/members/me/avatar/",
        {"image": image_upload(), "shows_face": "false"},
        format="multipart",
    )
    member.profile.refresh_from_db()
    other_client, other = member_client()
    own_post = make_post(member, images=2)
    their_post = make_post(other)
    services.like(member, their_post.public_id)
    services.add_comment(member, their_post.public_id, "From busy")
    services.like(other, own_post.public_id)
    services.follow(member, other)
    services.follow(other, member)
    services.block(member, member_client()[1])
    services.mute(member, member_client()[1])
    files = [image.image.name for image in own_post.images.all()] + [member.profile.avatar.name]
    assert all((private_root / name).exists() for name in files)
    return {
        "client": client,
        "member": member,
        "other": other,
        "files": files,
        "root": private_root,
    }


def remaining(member):
    return {
        "posts": FeedPost.objects.filter(author=member).count(),
        "comments": FeedComment.objects.filter(author=member).count(),
        "likes": FeedLike.objects.filter(user=member).count(),
        "follows": Follow.objects.filter(follower=member).count()
        + Follow.objects.filter(followed=member).count(),
        "blocks": Block.objects.filter(blocker=member).count(),
        "mutes": Mute.objects.filter(muter=member).count(),
        "notifications": Notification.objects.filter(recipient=member).count(),
        "acceptances": GuidelinesAcceptance.objects.filter(user=member).count(),
    }


def test_leave_and_erase(busy_member):
    client, member = busy_member["client"], busy_member["member"]
    wrong = client.post("/api/account/feed/erase/", {"display_name": "Busy_Member"}, format="json")
    assert wrong.status_code == 400
    response = client.post(
        "/api/account/feed/erase/", {"display_name": "busy_member"}, format="json"
    )
    assert response.status_code == 202
    assert set(remaining(member).values()) == {0}
    assert not any((busy_member["root"] / name).exists() for name in busy_member["files"])
    member.profile.refresh_from_db()
    assert not member.profile.avatar and member.profile.bio == ""
    assert member.profile.participates_in_feed is False
    assert User.objects.filter(pk=member.pk).exists()
    assert mail.outbox[-1].subject == tasks.ERASE_SUBJECT
    assert mail.outbox[-1].to == [member.email]


def test_account_deletion_runs_the_same_erase(busy_member, monkeypatch):
    client, member = busy_member["client"], busy_member["member"]
    calls = []
    original = services.erase_feed_data

    def spy(user):
        calls.append(user.pk)
        return original(user)

    monkeypatch.setattr("apps.accounts.views.erase_feed_data", spy)
    response = client.post("/api/account/delete/", {"password": PASSWORD}, format="json")
    assert response.status_code == 200
    assert calls == [member.pk]
    assert not User.objects.filter(pk=member.pk).exists()
    assert not any((busy_member["root"] / name).exists() for name in busy_member["files"])


def test_export_contents_and_single_use(busy_member, api_client):
    client, member = busy_member["client"], busy_member["member"]
    response = client.post("/api/account/feed/export/")
    assert response.status_code == 202
    assert client.post("/api/account/feed/export/").status_code in (202, 409)
    email = next(m for m in mail.outbox if m.subject == tasks.EXPORT_SUBJECT)
    token = email.body.split("#token=")[1].split()[0]
    assert len(token) > 30

    download = api_client.post(
        "/api/account/feed/export/download/", {"token": token}, format="json"
    )
    assert download.status_code == 200
    assert download["Content-Disposition"] == 'attachment; filename="my-data.zip"'
    assert download["Cache-Control"].startswith("private")
    archive = zipfile.ZipFile(BytesIO(b"".join(download.streaming_content)))
    names = set(archive.namelist())
    assert "data.json" in names and "images/avatar.webp" in names
    data = json.loads(archive.read("data.json"))
    assert data["profile"]["display_name"] == "busy_member"
    assert len(data["posts"]) == 1 and len(data["posts"][0]["images"]) == 2
    assert [c["body"] for c in data["comments"]] == ["From busy"]
    assert len(data["likes"]) == 1
    assert member.email not in archive.read("data.json").decode()

    again = api_client.post("/api/account/feed/export/download/", {"token": token}, format="json")
    assert again.status_code == 400


def test_export_expires(busy_member, api_client):
    busy_member["client"].post("/api/account/feed/export/")
    token = (
        next(m for m in mail.outbox if m.subject == tasks.EXPORT_SUBJECT)
        .body.split("#token=")[1]
        .split()[0]
    )
    DataExport.objects.update(expires_at=timezone.now() - timedelta(minutes=1))
    assert (
        api_client.post(
            "/api/account/feed/export/download/", {"token": token}, format="json"
        ).status_code
        == 400
    )
    assert tasks.purge_expired_exports() == 1
    assert not DataExport.objects.exists()


def test_export_task_receives_only_an_id(busy_member, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "apps.feed.tasks.build_member_export.delay", lambda *args: sent.append(args)
    )
    busy_member["client"].post("/api/account/feed/export/")
    assert sent == [(DataExport.objects.get().pk,)]
