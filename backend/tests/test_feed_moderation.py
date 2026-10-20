import pytest
from django.core.exceptions import ValidationError

from apps.core.models import AuditLog
from apps.feed import services
from apps.feed.models import FeedComment, FeedPost, Notification, Report
from tests.conftest import verify_age

pytestmark = pytest.mark.django_db


def report(client, target_type, target_id, reason, details=""):
    return client.post(
        "/api/members/reports/",
        {"target_type": target_type, "target_id": target_id, "reason": reason, "details": details},
        format="json",
    )


@pytest.mark.parametrize("reason", ["no_consent", "under_18"])
def test_serious_reasons_hide_immediately(member_client, make_post, reason):
    _, author = member_client()
    post = make_post(author)
    client, _ = member_client()
    response = report(client, "post", post.public_id, reason)
    assert response.status_code == 201
    assert response.json() == {"detail": "Thanks, our team will review this."}
    post.refresh_from_db()
    assert post.status == FeedPost.Status.HIDDEN_BY_REPORT
    viewer, _ = member_client()
    assert viewer.get(f"/api/members/posts/{post.public_id}/").status_code == 404


def test_other_reasons_queue_until_three_reporters(member_client, make_post):
    _, author = member_client()
    post = make_post(author)
    first, _ = member_client()
    for _ in range(2):
        report(first, "post", post.public_id, "spam")
    second, _ = member_client()
    report(second, "post", post.public_id, "harassment")
    post.refresh_from_db()
    assert post.status == FeedPost.Status.PUBLISHED
    assert Report.objects.filter(post=post).count() == 2
    third, _ = member_client()
    report(third, "post", post.public_id, "other", "Feels off")
    post.refresh_from_db()
    assert post.status == FeedPost.Status.HIDDEN_BY_REPORT


def test_other_reason_needs_details(member_client, make_post):
    _, author = member_client()
    post = make_post(author)
    client, _ = member_client()
    assert report(client, "post", post.public_id, "other").status_code == 400


def test_comment_and_profile_reports(member_client, make_post):
    _, author = member_client(display_name="reported_one")
    post = make_post(author)
    commenter_client, commenter = member_client()
    comment = services.add_comment(commenter, post.public_id, "Rude words")
    client, _ = member_client()
    report(client, "comment", comment.public_id, "no_consent")
    comment.refresh_from_db()
    assert comment.status == FeedComment.Status.HIDDEN_BY_REPORT
    report(client, "profile", "reported_one", "under_18")
    author.profile.refresh_from_db()
    assert author.profile.hidden_by_report
    assert client.get("/api/members/u/reported_one/").status_code == 404
    assert report(client, "profile", "nobody_here", "spam").status_code == 404


def test_reporter_learns_nothing(member_client, make_post, admin_user):
    _, author = member_client()
    post = make_post(author)
    client, reporter = member_client()
    report(client, "post", post.public_id, "spam")
    services.moderate(admin_user, "remove", "post", post, reason="Spam")
    assert client.get("/api/members/notifications/").json()["results"] == []


def test_moderation_actions_and_log(member_client, make_post, admin_user):
    author_client, author = member_client()
    post = make_post(author)
    reporter, _ = member_client()
    report(reporter, "post", post.public_id, "no_consent")

    services.moderate(admin_user, "dismiss", "post", post)
    post.refresh_from_db()
    assert post.status == FeedPost.Status.PUBLISHED
    assert Report.objects.get(post=post).resolution == "dismissed"

    with pytest.raises(services.FeedError):
        services.moderate(admin_user, "remove", "post", post, reason="")
    services.moderate(admin_user, "remove", "post", post, reason="Shows a face without consent")
    post.refresh_from_db()
    assert post.status == FeedPost.Status.REMOVED and post.removed_by == admin_user
    texts = [n["text"] for n in author_client.get("/api/members/notifications/").json()["results"]]
    assert any("Shows a face without consent" in t for t in texts)

    services.moderate(admin_user, "warn", "user", author, reason="Please re-read")
    author.profile.refresh_from_db()
    assert author.profile.posting_cooldown_until is not None
    assert author_client.get("/api/members/me/").json()["post_block_reason"] == "cooldown"

    services.moderate(admin_user, "suspend", "user", author, days=3)
    assert author_client.get("/api/members/feed/").status_code == 404

    log = list(AuditLog.objects.order_by("created_at").values_list("action", flat=True))
    assert log == ["dismiss", "remove", "warn", "suspend"]
    assert all(a.actor_label == "house_admin" for a in AuditLog.objects.all())
    assert set(AuditLog.objects.values_list("category", flat=True)) == {"moderation"}


def test_ban_hides_content_and_access(member_client, make_post, admin_user):
    author_client, author = member_client()
    post = make_post(author)
    viewer, _ = member_client()
    services.moderate(admin_user, "ban", "user", author, reason="Repeated violations")
    assert viewer.get(f"/api/members/posts/{post.public_id}/").status_code == 404
    assert author_client.get("/api/members/feed/").status_code == 404
    assert author_client.get("/api/account/feed/").json()["banned"] is True


def test_moderation_log_is_immutable(admin_user, make_member):
    member = make_member()
    action = services.moderate(admin_user, "warn", "user", member)
    action.reason = "changed"
    with pytest.raises(ValidationError):
        action.save()
    with pytest.raises(ValidationError):
        action.delete()
    with pytest.raises(ValidationError):
        AuditLog.objects.all().delete()
    with pytest.raises(ValidationError):
        AuditLog.objects.update(reason="x")
    assert AuditLog.objects.get().reason == ""


def test_moderation_log_read_only_in_admin(admin_client, admin_user, make_member):
    action = services.moderate(admin_user, "warn", "user", make_member())
    url = f"/admin/core/auditlog/{action.pk}/change/"
    assert admin_client.get("/admin/core/auditlog/add/").status_code == 403
    assert admin_client.post(url, {"reason": "edited"}).status_code == 403
    delete_url = f"/admin/core/auditlog/{action.pk}/delete/"
    assert admin_client.post(delete_url, {"post": "yes"}).status_code == 403
    assert AuditLog.objects.filter(pk=action.pk).exists()


def test_moderation_queue_view(admin_client, admin_user, member_client, make_post, settings):
    verify_age(admin_user)  # the pictures need the viewer's own ID check
    _, author = member_client()
    pending = make_post(author, caption="Waiting post", images=1, premoderation=3)
    reported = make_post(author, caption="Reported post")
    client, _ = member_client()
    report(client, "post", reported.public_id, "under_18")
    response = admin_client.get("/admin/feed/feedpost/moderation/")
    content = response.content.decode()
    assert response.status_code == 200
    assert "Waiting post" in content and "Reported post" in content
    assert "Hidden until reviewed" in content
    image = pending.images.get()
    assert f"/admin/feed/feedpost/moderation/image/{image.public_id}/" in content
    preview = admin_client.get(f"/admin/feed/feedpost/moderation/image/{image.public_id}/")
    assert preview.status_code == 200 and preview["Cache-Control"].startswith("private")

    admin_client.post(
        "/admin/feed/feedpost/moderation/",
        {"target_type": "post", "target_ref": pending.public_id, "action": "approve"},
    )
    pending.refresh_from_db()
    assert pending.status == FeedPost.Status.PUBLISHED
    assert AuditLog.objects.filter(action="approve").exists()
    assert Notification.objects.filter(recipient=author, kind="moderation").exists()


def test_staff_erase_needs_confirmation(admin_client, member_client, make_post):
    _, author = member_client(display_name="erase_me")
    post = make_post(author)
    admin_client.post(
        "/admin/feed/feedpost/moderation/",
        {"target_type": "user", "target_ref": "erase_me", "action": "erase", "confirm": "wrong"},
    )
    assert FeedPost.objects.filter(pk=post.pk).exists()
    admin_client.post(
        "/admin/feed/feedpost/moderation/",
        {"target_type": "user", "target_ref": "erase_me", "action": "erase", "confirm": "erase_me"},
    )
    assert not FeedPost.objects.filter(pk=post.pk).exists()
    assert AuditLog.objects.filter(action="erase").exists()


@pytest.mark.django_db(transaction=True)
def test_moderation_log_migrates_into_audit_log_without_loss():
    from datetime import timedelta

    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    from django.utils import timezone

    executor = MigrationExecutor(connection)
    executor.migrate([("feed", "0002_default_guidelines"), ("core", "0001_audit_log")])
    old_apps = executor.loader.project_state([("feed", "0002_default_guidelines")]).apps
    Old = old_apps.get_model("feed", "ModerationAction")
    when = timezone.now() - timedelta(days=40)
    old = Old.objects.create(
        actor_label="moderator_one",
        target_label="Post abc by someone",
        target_type="post",
        target_ref="abc",
        action="remove",
        reason="No consent",
    )
    Old.objects.filter(pk=old.pk).update(created_at=when)

    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())

    moved = AuditLog.objects.get(target_ref="abc")
    assert (moved.category, moved.action, moved.reason) == ("moderation", "remove", "No consent")
    assert moved.actor_label == "moderator_one"
    assert moved.created_at == when
