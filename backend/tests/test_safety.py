"""The staff section, reports, member actions and appeals (apps/safety)."""

from datetime import timedelta
from io import StringIO

import pytest
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import AuditLog
from apps.events.access import RESTRICTED, can_rsvp
from apps.feed import services as feed_services
from apps.feed.access import can_view_feed
from apps.feed.models import FeedComment, FeedPost, Guidelines, Notification, Report
from apps.memberships import desk
from apps.memberships.models import Membership
from apps.safety import metrics, roles, services
from apps.safety.models import Appeal, BlockedEmail, MemberAction
from tests.conftest import csrf_client_for, staff_login

pytestmark = pytest.mark.django_db

STAFF_PATHS = [
    "/api/staff/overview/",
    "/api/staff/metrics/",
    "/api/staff/team/",
    "/api/staff/rules/",
    "/api/staff/reports/",
    "/api/staff/members/?q=ab",
    "/api/staff/appeals/",
]


@pytest.fixture
def team(make_user):
    """team(role) -> (client, user): a team member whose session passed the two-step login."""

    def make(role, verified=True, **kwargs):
        user = make_user(**kwargs)
        roles.set_role(user, role)
        client = APIClient(enforce_csrf_checks=True)
        if verified:
            staff_login(client, user)
        else:
            user.refresh_from_db()
            client.force_login(user)
        return csrf_client_for(client), user

    return make


@pytest.fixture
def joined_member(make_user):
    """A member who has joined the feed (staff grant), so they can post and report."""

    def make(**kwargs):
        user = make_user(**kwargs)
        user.profile.feed_access_granted = True
        user.profile.save()
        feed_services.join_feed(user, Guidelines.current().version)
        return user

    return make


@pytest.fixture
def post_by(make_post):
    def make(author):
        post = make_post(author)
        post.status = FeedPost.Status.PUBLISHED
        post.save(update_fields=["status"])
        return post

    return make


def report_post(reporter, post, reason="harassment"):
    client = csrf_client_for(_logged_in(reporter))
    response = client.post(
        "/api/members/reports/",
        {"target_type": "post", "target_id": post.public_id, "reason": reason},
        format="json",
    )
    assert response.status_code == 201
    return Report.objects.get(reporter=reporter, post=post)


def _logged_in(user):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)
    return client


def action(actor, member, kind="warning", **extra):
    return services.take_action(
        actor,
        member,
        services.ActionInput(kind=kind, rule="Community guidelines", reason="Because.", **extra),
    )


# Roles and access


@pytest.mark.parametrize("path", STAFF_PATHS)
def test_everyone_without_a_role_gets_404(path, client, signed_in, joined_member, desk_staff):
    assert client.get(path).status_code == 404
    member_client, _ = signed_in()
    assert member_client.get(path).status_code == 404
    assert csrf_client_for(_logged_in(joined_member())).get(path).status_code == 404
    # Door desk staff: is_staff, verified, but no team role.
    desk_client = APIClient()
    staff_login(desk_client, desk_staff)
    assert desk_client.get(path).status_code == 404


@pytest.mark.parametrize("path", STAFF_PATHS)
def test_a_role_without_the_two_step_login_gets_404(path, team):
    client, _ = team(roles.ADMIN, verified=False)
    assert client.get(path).status_code == 404


def test_each_role_sees_its_own_part(team):
    expectations = {
        roles.MODERATOR: {
            "/api/staff/reports/": 200,
            "/api/staff/metrics/": 404,
            "/api/staff/team/": 404,
        },
        roles.STAFF: {
            "/api/staff/reports/": 200,
            "/api/staff/metrics/": 200,
            "/api/staff/team/": 404,
        },
        roles.ADMIN: {
            "/api/staff/reports/": 200,
            "/api/staff/metrics/": 200,
            "/api/staff/team/": 200,
        },
    }
    for role, paths in expectations.items():
        client, _ = team(role)
        for path, status in paths.items():
            assert client.get(path).status_code == status, (role, path)


def test_writes_need_csrf_after_the_access_check(team):
    _, user = team(roles.ADMIN)
    client = APIClient(enforce_csrf_checks=True)
    staff_login(client, user)
    assert client.post("/api/staff/team/", {"person": "x"}).status_code == 403


def test_the_session_says_whether_the_two_step_login_is_done(team):
    client, _ = team(roles.MODERATOR, verified=False)
    staff = client.get("/api/account/session/").json()["user"]["staff"]
    assert staff["role"] == "moderator" and not staff["verified"]
    assert "/login/?next=" in staff["verify_url"] and "%2Fmembers%2Fstaff" in staff["verify_url"]
    client, _ = team(roles.MODERATOR)
    assert client.get("/api/account/session/").json()["user"]["staff"]["verified"]


def test_superusers_are_admins_and_roles_need_the_staff_flag(make_user, django_user_model):
    boss = django_user_model.objects.create_superuser(
        email="boss@example.org", display_name="boss", password="x" * 20
    )
    assert roles.role_of(boss) == roles.ADMIN
    person = make_user()
    roles.set_role(person, roles.MODERATOR)
    person.refresh_from_db()
    assert person.is_staff and roles.role_of(person) == roles.MODERATOR
    roles.set_role(person, None)
    person.refresh_from_db()
    assert not person.is_staff and roles.role_of(person) is None


def test_only_admins_manage_the_team_and_it_is_logged(team, make_user):
    client, admin = team(roles.ADMIN)
    newcomer = make_user(display_name="new_mod")
    response = client.post(
        "/api/staff/team/", {"person": "new_mod", "role": "moderator"}, format="json"
    )
    assert response.status_code == 200
    newcomer.refresh_from_db()
    assert roles.role_of(newcomer) == roles.MODERATOR
    assert AuditLog.objects.filter(
        category="security", action="team_role", target_user=newcomer
    ).exists()
    own = client.post(
        "/api/staff/team/", {"person": admin.display_name, "role": None}, format="json"
    )
    assert own.status_code == 400


def test_staff_always_have_the_member_app(make_user):
    volunteer = make_user()
    volunteer.is_staff = True
    volunteer.save()
    client = csrf_client_for(_logged_in(volunteer))
    assert client.get("/api/account/session/").json()["user"]["member_app"] == "join"


# Metrics


def test_small_numbers_are_withheld():
    assert metrics.count(4) == {"value": None, "fewer_than": 5}
    assert metrics.count(0) == {"value": None, "fewer_than": 5}
    assert metrics.count(5) == {"value": 5}
    assert metrics.money(10_000, 4) == {"cents": None, "fewer_than": 5}
    assert metrics.money(10_000, 5) == {"cents": 10_000}


def test_metrics_suppress_and_never_name_anyone(team, joined_member, post_by, make_membership):
    authors = [joined_member(display_name=f"author_{n}") for n in range(4)]
    for author in authors:
        post_by(author)
    make_membership(user=authors[0])
    client, _ = team(roles.STAFF)
    data = client.get("/api/staff/metrics/?range=90d").json()
    assert data["feed"]["posts"] == {"value": None, "fewer_than": 5}
    assert data["members"]["total_active"]["value"] is None
    post_by(joined_member(display_name="author_5"))
    data = client.get("/api/staff/metrics/?range=90d").json()
    assert data["feed"]["posts"] == {"value": 5}
    raw = client.get("/api/staff/metrics/?range=12m").content.decode()
    export = client.post("/api/staff/metrics/export/", {"range": "12m"}, format="json")
    for text in (raw, export.content.decode()):
        assert "author_" not in text and "@example.org" not in text
    assert AuditLog.objects.filter(category="export", action="metrics_export").exists()
    assert len(data["series"]) == 13


def test_no_person_level_metric_endpoints():
    from django.urls import get_resolver

    staff = get_resolver().url_patterns
    names = {name for name in _all_names(staff) if name.startswith("staff-")}
    metric_routes = {reverse(name) for name in names if name.startswith("staff-metrics")}
    # Only the dashboard and its export: neither takes a person, an id or a handle.
    assert metric_routes == {"/api/staff/metrics/", "/api/staff/metrics/export/"}


def _all_names(patterns):
    for pattern in patterns:
        if hasattr(pattern, "url_patterns"):
            yield from _all_names(pattern.url_patterns)
        elif pattern.name:
            yield pattern.name


# Reports, end to end


def test_every_report_type_reaches_the_inbox(team, joined_member, post_by, csrf_client):
    author = joined_member(display_name="author_one")
    reporter = joined_member(display_name="reporter_one")
    post = post_by(author)
    comment = FeedComment.objects.create(post=post, author=author, body="Rude words")
    client = csrf_client_for(_logged_in(reporter))
    for target_type, target_id in (
        ("post", post.public_id),
        ("comment", comment.public_id),
        ("profile", author.display_name),
    ):
        response = client.post(
            "/api/members/reports/",
            {"target_type": target_type, "target_id": target_id, "reason": "harassment"},
            format="json",
        )
        assert response.status_code == 201, target_type
    in_app = client.post(
        "/api/concerns/",
        {"details": "At the social someone was pushy.", "reported_name": "author_one"},
        format="json",
    )
    assert in_app.status_code == 201
    website = csrf_client.post(
        "/api/concerns/",
        {"details": "A guest worry.", "contact_email": "guest@example.net"},
        format="json",
    )
    assert website.status_code == 201
    assert mail.outbox[-1].to == ["guest@example.net"]
    team_client, _ = team(roles.MODERATOR, display_name="mod_one")
    inbox = team_client.get("/api/staff/reports/?status=open").json()
    assert sorted(item["kind"] for item in inbox) == [
        "comment",
        "event",
        "event",
        "post",
        "profile",
    ]
    for item in inbox:
        detail = team_client.get(f"/api/staff/reports/{item['id']}/").json()
        assert detail["reporter"] == {"hidden": True, "can_reveal": False}
        assert "reporter_one" not in str(detail)


def test_concern_emails_to_staff_carry_no_text(team, csrf_client):
    team(roles.MODERATOR, email="mod@example.org")
    csrf_client.post("/api/concerns/", {"details": "SECRET WORDS"}, format="json")
    alerts = [m for m in mail.outbox if m.to == ["mod@example.org"]]
    assert alerts and all("SECRET" not in m.body and "SECRET" not in m.subject for m in alerts)
    assert alerts[0].subject == "Something is waiting for review"


def test_concern_honeypot_and_empty_text(csrf_client):
    assert (
        csrf_client.post(
            "/api/concerns/", {"details": "x", "website": "spam"}, format="json"
        ).status_code
        == 201
    )
    assert not Report.objects.exists()
    assert csrf_client.post("/api/concerns/", {"details": "  "}, format="json").status_code == 400


def test_reporters_learn_received_then_reviewed_only(team, joined_member, post_by, csrf_client):
    reporter = joined_member()
    report = report_post(reporter, post_by(joined_member()))
    reporter_client = csrf_client_for(_logged_in(reporter))
    assert reporter_client.get("/api/account/reports/").json()[0]["status"] == "received"
    staff_client, _ = team(roles.MODERATOR)
    staff_client.post(
        f"/api/staff/reports/{report.pk}/status/", {"status": "in_review"}, format="json"
    )
    assert reporter_client.get("/api/account/reports/").json()[0]["status"] == "received"
    staff_client.post(
        f"/api/staff/reports/{report.pk}/status/", {"status": "dismissed"}, format="json"
    )
    mine = reporter_client.get("/api/account/reports/").json()[0]
    assert mine == {
        "id": report.pk,
        "kind_label": "Post",
        "created_at": mine["created_at"],
        "status": "reviewed",
    }
    # A website reporter gets the same, by email, and the address is then forgotten.
    csrf_client.post(
        "/api/concerns/", {"details": "x", "contact_email": "g@example.net"}, format="json"
    )
    concern = Report.objects.get(target_type="event")
    staff_client.post(
        f"/api/staff/reports/{concern.pk}/status/", {"status": "resolved"}, format="json"
    )
    concern.refresh_from_db()
    assert concern.contact_email == ""
    assert mail.outbox[-1].subject == "An update on your message"


def test_notes_and_assignment(team):
    client, moderator = team(roles.MODERATOR, display_name="mod_two")
    report = services.file_concern(None, "Something")
    detail = client.post(
        f"/api/staff/reports/{report.pk}/notes/", {"body": "Called them"}, format="json"
    ).json()
    assert detail["notes"][0]["body"] == "Called them"
    detail = client.post(
        f"/api/staff/reports/{report.pk}/assign/", {"assignee": "mod_two"}, format="json"
    ).json()
    assert detail["assigned_to"] == {"display_name": "mod_two"} and detail["status"] == "in_review"


def test_reported_content_pictures_only_through_the_staff_path(team, joined_member, make_post):
    author = joined_member()
    post = make_post(author, images=1)
    post.status = FeedPost.Status.PUBLISHED
    post.save(update_fields=["status"])
    client, _ = team(roles.MODERATOR)
    image = post.images.first()
    assert client.get(f"/api/staff/media/{image.public_id}/").status_code == 404
    report_post(joined_member(), post)
    detail = client.get(f"/api/staff/reports/{Report.objects.get().pk}/").json()
    assert detail["content"]["images"] == [f"/api/staff/media/{image.public_id}/"]


# Reporter anonymity


def test_reporter_identity_is_hidden_and_reveal_is_admin_only_and_logged(
    team, joined_member, post_by
):
    author = joined_member()
    reporter = joined_member(display_name="quiet_reporter")
    report = report_post(reporter, post_by(author))
    moderator_client, moderator = team(roles.MODERATOR)
    assert moderator_client.post(f"/api/staff/reports/{report.pk}/reveal/").status_code == 404
    admin_client, _ = team(roles.ADMIN)
    revealed = admin_client.post(f"/api/staff/reports/{report.pk}/reveal/").json()
    assert revealed["display_name"] == "quiet_reporter"
    assert AuditLog.objects.filter(category="private_data", action="reveal_reporter").count() == 1
    # The reported member never sees who it was.
    taken = action(moderator, author, report=report)
    author_client = csrf_client_for(_logged_in(author))
    notices = author_client.get("/api/account/notices/").content.decode()
    assert "quiet_reporter" not in notices and str(taken.pk) in notices
    assert "report" not in author_client.get("/api/account/notices/").json()[0]


# Actions and their reversal


def test_warning_notifies_discreetly_and_reverses(team, joined_member):
    _, moderator = team(roles.MODERATOR)
    member = joined_member()
    mail.outbox.clear()
    warning = action(moderator, member)
    assert mail.outbox[-1].subject == "An update about your account"
    assert (
        "Because" not in mail.outbox[-1].body
        and "/members/settings/notices" in mail.outbox[-1].body
    )
    services.reverse_action(moderator, warning, "Mistake")
    warning.refresh_from_db()
    assert warning.is_reversed and not warning.is_in_force()


def test_remove_content_and_restore(team, joined_member, post_by):
    _, moderator = team(roles.MODERATOR)
    author = joined_member()
    post = post_by(author)
    comment = FeedComment.objects.create(post=post, author=author, body="x")
    removed_post = action(moderator, author, kind="remove_content", post=post)
    removed_comment = action(moderator, author, kind="remove_content", comment=comment)
    post.refresh_from_db()
    comment.refresh_from_db()
    assert post.status == FeedPost.Status.REMOVED and comment.status == FeedComment.Status.REMOVED
    services.reverse_action(moderator, removed_post, "Fine after all")
    services.reverse_action(moderator, removed_comment, "Fine after all")
    post.refresh_from_db()
    comment.refresh_from_db()
    assert post.status == FeedPost.Status.PUBLISHED and comment.status == FeedComment.Status.VISIBLE


def test_remove_content_needs_their_own_content(team, joined_member, post_by):
    _, moderator = team(roles.MODERATOR)
    with pytest.raises(services.SafetyError):
        action(moderator, joined_member(), kind="remove_content", post=post_by(joined_member()))


def test_feed_suspension_and_reversal(team, joined_member):
    _, moderator = team(roles.MODERATOR)
    member = joined_member()
    suspension = action(moderator, member, kind="feed_suspension", days=7)
    member.profile.refresh_from_db()
    assert not can_view_feed(member)
    assert suspension.ends_at - suspension.created_at >= timedelta(days=6, hours=23)
    custom = action(
        moderator, member, kind="feed_suspension", until=timezone.now() + timedelta(days=40)
    )
    services.reverse_action(moderator, custom, "Shorter is enough")
    member.profile.refresh_from_db()
    assert member.profile.feed_suspended_until == suspension.ends_at
    services.reverse_action(moderator, suspension, "Done")
    member.profile.refresh_from_db()
    assert can_view_feed(member)
    with pytest.raises(services.SafetyError, match="how long"):
        action(moderator, member, kind="feed_suspension")


def test_event_suspension_blocks_rsvps_and_flags_the_door(
    team, make_membership, make_event, desk_staff
):
    _, moderator = team(roles.MODERATOR)
    membership = make_membership()
    member = membership.user
    event = make_event()
    suspension = action(moderator, member, kind="event_suspension", days=30)
    member.profile.refresh_from_db()
    assert can_rsvp(member, event) == (False, RESTRICTED)
    flags = desk.door_flags(member)
    assert flags["events_suspended_until"] == suspension.ends_at and not flags["do_not_admit"]
    services.reverse_action(moderator, suspension, "Cleared")
    member.profile.refresh_from_db()
    assert can_rsvp(member, event)[0]


def test_ban_ends_membership_and_flags_the_door(team, make_membership, desk_staff, client):
    _, moderator = team(roles.MODERATOR)
    membership = make_membership()
    member = membership.user
    action(moderator, member, kind="ban", block_email=True)
    membership.refresh_from_db()
    member.profile.refresh_from_db()
    assert membership.status == Membership.Status.CANCELLED
    assert member.profile.is_feed_banned and member.profile.do_not_admit_at
    assert BlockedEmail.blocks(member.email.upper())
    with pytest.raises(desk.DeskError, match="Do not admit"):
        desk.renew(desk_staff, membership, "cash", 1000)
    staff_login(client, desk_staff)
    page = client.get(reverse("admin:memberships_door_desk"), {"q": membership.reference_code})
    assert "Do not admit" in page.content.decode()


def test_ban_reversal_clears_the_flags(team, make_membership):
    _, moderator = team(roles.MODERATOR)
    member = make_membership().user
    ban = action(moderator, member, kind="ban", block_email=True)
    services.reverse_action(moderator, ban, "Appeal upheld")
    member.profile.refresh_from_db()
    assert not member.profile.is_feed_banned and member.profile.do_not_admit_at is None
    assert not BlockedEmail.blocks(member.email)


def test_blocked_email_cannot_register(csrf_client, team, make_user):
    _, moderator = team(roles.MODERATOR)
    member = make_user(email="gone@example.org")
    action(moderator, member, kind="ban", block_email=True)
    member.delete()
    mail.outbox.clear()
    response = csrf_client.post(
        "/api/account/register/",
        {
            "email": "Gone@example.org",
            "display_name": "back_again",
            "password": "a-long-password-123",
        },
        format="json",
    )
    assert response.status_code == 201
    from apps.accounts.models import User

    assert not User.objects.filter(email__iexact="gone@example.org").exists()
    assert not mail.outbox


def test_actions_need_a_reason_and_a_rule(team, joined_member):
    _, moderator = team(roles.MODERATOR)
    member = joined_member()
    for rule, reason in (("", "x"), ("Rule", "")):
        with pytest.raises(services.SafetyError):
            services.take_action(
                moderator, member, services.ActionInput(kind="warning", rule=rule, reason=reason)
            )
    with pytest.raises(services.SafetyError):
        services.reverse_action(moderator, action(moderator, member), "  ")


def test_actions_through_the_api(team, joined_member, post_by):
    client, _ = team(roles.MODERATOR)
    author = joined_member(display_name="api_author")
    report = report_post(joined_member(), post_by(author))
    response = client.post(
        "/api/staff/members/api_author/actions/",
        {
            "kind": "remove_content",
            "rule": "Consent",
            "reason": "No consent",
            "report_id": report.pk,
        },
        format="json",
    )
    assert response.status_code == 201
    report.refresh_from_db()
    assert report.status == Report.Status.RESOLVED
    taken = response.json()
    reversed_ = client.post(
        f"/api/staff/actions/{taken['id']}/reverse/", {"reason": "Wrong post"}, format="json"
    )
    assert reversed_.status_code == 200 and reversed_.json()["reversed_at"]
    member = client.get("/api/staff/members/api_author/").json()
    assert member["reports_about"] == 1 and member["actions"][0]["kind"] == "remove_content"


# Appeals


def test_notices_count_as_unread_until_seen_and_open_from_the_notification(team, joined_member):
    _, acting = team(roles.MODERATOR, display_name="acting_mod")
    _, other = team(roles.MODERATOR, display_name="other_mod")
    member = joined_member()
    client = csrf_client_for(_logged_in(member))

    def unread():
        return client.get("/api/account/session/").json()["user"]["unread_notices"]

    assert unread() == 0
    taken = action(acting, member, kind="feed_suspension", days=7)
    note = Notification.objects.filter(recipient=member).latest("created_at")
    assert note.kind == Notification.Kind.NOTICE and "Settings, under Notices" in note.message
    assert unread() == 1
    client = csrf_client_for(client)
    assert client.post("/api/account/notices/seen/").json() == {"unread_notices": 0}
    assert unread() == 0

    # An appeal decided later is an update to the same notice.
    client.post(f"/api/account/notices/{taken.pk}/appeal/", {"text": "Please"}, format="json")
    Profile = type(member.profile)
    Profile.objects.filter(user=member).update(
        notices_seen_at=timezone.now() - timedelta(minutes=1)
    )
    services.decide_appeal(other, Appeal.objects.get(), "uphold", "It stands")
    assert unread() == 1
    assert services.unread_notices(member) == 1


def test_a_reviewed_report_notifies_the_reporter_as_a_notice(team, joined_member, post_by):
    _, moderator = team(roles.MODERATOR)
    reporter, author = joined_member(), joined_member()
    report = report_post(reporter, post_by(author))
    services.set_status(moderator, report, Report.Status.DISMISSED)
    assert Notification.objects.filter(recipient=reporter, kind=Notification.Kind.NOTICE).exists()


def test_appeals_go_to_someone_else_and_one_per_action(team, joined_member):
    _, acting = team(roles.MODERATOR, display_name="acting_mod")
    _, other = team(roles.MODERATOR, display_name="other_mod")
    member = joined_member()
    taken = action(acting, member, kind="feed_suspension", days=7)
    member_client = csrf_client_for(_logged_in(member))
    response = member_client.post(
        f"/api/account/notices/{taken.pk}/appeal/", {"text": "Please"}, format="json"
    )
    assert response.status_code == 201
    appeal = Appeal.objects.get()
    assert appeal.assigned_to == other
    again = member_client.post(
        f"/api/account/notices/{taken.pk}/appeal/", {"text": "Again"}, format="json"
    )
    assert again.status_code == 409
    with pytest.raises(services.SafetyError, match="Someone other"):
        services.decide_appeal(acting, appeal, "reverse", "My own call")
    services.decide_appeal(other, appeal, "reverse", "Too harsh")
    appeal.refresh_from_db()
    taken.refresh_from_db()
    assert appeal.status == Appeal.Status.REVERSED and taken.is_reversed
    member.profile.refresh_from_db()
    assert can_view_feed(member)


def test_a_lone_moderator_may_review_their_own_appeal(team, joined_member):
    _, only = team(roles.MODERATOR)
    member = joined_member()
    taken = action(only, member)
    appeal = services.submit_appeal(member, taken, "Please")
    assert appeal.assigned_to is None
    services.decide_appeal(only, appeal, "uphold", "It stands")
    appeal.refresh_from_db()
    assert appeal.status == Appeal.Status.UPHELD and not taken.is_reversed


def test_members_cannot_appeal_someone_elses_action(team, joined_member):
    _, moderator = team(roles.MODERATOR)
    taken = action(moderator, joined_member())
    stranger = csrf_client_for(_logged_in(joined_member()))
    assert (
        stranger.post(
            f"/api/account/notices/{taken.pk}/appeal/", {"text": "x"}, format="json"
        ).status_code
        == 404
    )


def test_appeal_decisions_through_the_api(team, joined_member):
    _, acting = team(roles.MODERATOR)
    client, admin = team(roles.ADMIN)
    member = joined_member()
    appeal = services.submit_appeal(member, action(acting, member), "Please")
    listed = client.get("/api/staff/appeals/").json()
    assert [a["id"] for a in listed] == [appeal.pk] and listed[0]["may_decide"]
    decided = client.post(
        f"/api/staff/appeals/{appeal.pk}/decide/",
        {"decision": "uphold", "note": "Stands"},
        format="json",
    )
    assert decided.status_code == 200 and decided.json()["status"] == "upheld"


# The log


def test_every_action_and_reversal_is_in_the_immutable_log(team, joined_member):
    _, moderator = team(roles.MODERATOR)
    member = joined_member()
    taken = action(moderator, member, kind="feed_suspension", days=7)
    services.reverse_action(moderator, taken, "Lifted")
    entries = AuditLog.objects.filter(category="moderation", target_user=member)
    assert {e.action for e in entries} >= {"feed_suspension", "reverse_feed_suspension"}
    entry = entries.first()
    with pytest.raises(ValidationError):
        entry.save()
    with pytest.raises(ValidationError):
        entry.delete()
    with pytest.raises(ValidationError):
        entries.update(reason="changed")
    with pytest.raises(ValidationError):
        entries.delete()
    assert MemberAction.objects.filter(pk=taken.pk, reversed_at__isnull=False).exists()


# Part A: getting to the member app


def test_member_app_state_on_the_session(make_user, joined_member, team):
    plain = csrf_client_for(_logged_in(make_user()))
    assert plain.get("/api/account/session/").json()["user"]["member_app"] is None
    joined = csrf_client_for(_logged_in(joined_member()))
    assert joined.get("/api/account/session/").json()["user"]["member_app"] == "open"
    entitled = make_user()
    entitled.profile.feed_access_granted = True
    entitled.profile.save()
    assert (
        csrf_client_for(_logged_in(entitled))
        .get("/api/account/session/")
        .json()["user"]["member_app"]
        == "join"
    )
    _, moderator = team(roles.MODERATOR)
    suspended = joined_member()
    action(moderator, suspended, kind="feed_suspension", days=3)
    session = csrf_client_for(_logged_in(suspended)).get("/api/account/session/").json()["user"]
    assert session["member_app"] == "paused"


def test_seed_demo_prints_the_logins_last(settings):
    settings.DEBUG = True
    out = StringIO()
    call_command("seed_demo", stdout=out)
    tail = out.getvalue().strip().splitlines()
    summary = tail[tail.index("Demo accounts (DEBUG only). Every password is DEMO_PASSWORD:") :]
    joined = "\n".join(summary)
    for email in (
        "demo.member@example.org",
        "team.moderator@example.org",
        "team.admin@example.org",
        "desk.volunteer@example.org",
    ):
        assert email in joined
    assert f"password: {settings.DEMO_PASSWORD}" in joined
    assert Report.objects.filter(target_type="event").count() >= 2
    assert Appeal.objects.exists()
