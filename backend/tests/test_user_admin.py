"""The admin's Members page: real actions in place of Django's delete, one at a time or in
bulk, each through the existing services, logged, told to the member and reversible."""

import csv
import io
from datetime import timedelta

import pytest
from django.contrib import admin
from django.core import mail
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.accounts import member_actions
from apps.accounts.models import User
from apps.core.models import ERASED_MEMBER, AuditLog
from apps.feed.models import FeedComment, FeedPost, Notification, Report
from apps.memberships.desk import door_flags
from apps.safety import roles, services
from apps.safety.models import BlockedEmail, MemberAction
from tests.conftest import PASSWORD, fresh_code, next_window, staff_login, verify_age

pytestmark = pytest.mark.django_db

CHANGELIST = "/admin/accounts/user/"
RULE = "Consent first"
NOTICE_SUBJECT = "An update about your account"


def bulk(client, key, users, **data):
    return client.post(
        CHANGELIST,
        {
            "action": f"bulk_{key}",
            "_selected_action": [user.pk for user in users],
            "apply": "1",
            **data,
        },
        follow=True,
    )


def detail_url(user, key):
    return reverse(f"admin:accounts_user_detail_{key}", args=(user.pk,))


def page_messages(response):
    return [str(message) for message in response.context["messages"]]


def notices(user):
    return Notification.objects.filter(recipient=user, kind=Notification.Kind.NOTICE).count()


def logged(action, user):
    return AuditLog.objects.filter(action=action, target_user=user).exists()


@pytest.fixture
def as_role(make_user):
    def login(role, **kwargs):
        user = make_user(display_name=f"team_{role}", **kwargs)
        roles.set_role(user, role)
        return staff_login(Client(), user), user

    return login


@pytest.fixture
def admin_actor(admin_user):
    """The superuser, logged in with an authenticator for fresh codes."""
    return staff_login(Client(), admin_user), admin_user


@pytest.fixture
def members(make_member):
    return [make_member(display_name=f"member_{n}") for n in range(3)]


# The list


def test_the_list_has_the_columns_filters_and_actions_but_no_delete(
    admin_client, make_member, make_tier
):
    make_member(display_name="listed_one")
    make_tier(name="Rose")
    page = admin_client.get(CHANGELIST).content.decode()
    for text in (
        "listed_one",
        "Tier",
        "Membership",
        "ID verified",
        "Feed member",
        "Joined",
        "Active",
        "Send a warning",
        "Suspend from feed",
        "Erase account",
    ):
        assert text in page, text
    for title in (
        "membership status",
        "tier",
        "ID verified",
        "feed member",
        "suspended",
        "banned",
        "deactivated",
        "email verified",
        "staff role",
    ):
        assert f"By {title}" in page, title
    assert "Delete selected" not in page and "delete_selected" not in page


def test_email_shows_and_searches_for_admins_only(admin_client, as_role, make_member):
    member = make_member(display_name="quiet_one", email="quiet.one@private.example")
    moderator, _ = as_role(roles.MODERATOR)
    as_moderator = moderator.get(CHANGELIST, {"q": "quiet.one@private"}).content.decode()
    assert "quiet.one@private.example" not in as_moderator and "quiet_one" not in as_moderator
    assert "quiet_one" in moderator.get(CHANGELIST, {"q": "quiet"}).content.decode()
    as_admin = admin_client.get(CHANGELIST, {"q": "quiet.one@private"}).content.decode()
    assert member.email in as_admin
    page = moderator.get(reverse("admin:accounts_user_change", args=(member.pk,))).content
    assert member.email.encode() not in page


def test_the_filters_find_the_right_people(admin_client, make_member, make_user):
    suspended = make_member(display_name="paused_one")
    suspended.profile.feed_suspended_until = timezone.now() + timedelta(days=2)
    suspended.profile.save()
    gone = make_user(display_name="gone_one", is_active=False)
    unverified = make_user(display_name="new_one", verified=False)

    def shown(**query):
        return admin_client.get(CHANGELIST, query).content.decode()

    assert "paused_one" in shown(suspended="yes") and "gone_one" not in shown(suspended="yes")
    assert "gone_one" in shown(deactivated="yes")
    assert unverified.display_name in shown(email_verified="no")
    assert "paused_one" in shown(feed_member="yes") and "new_one" not in shown(feed_member="yes")
    assert gone.display_name in shown(id_verified="no")


# The confirmation page


def test_an_action_opens_a_confirmation_page_first(as_role, members):
    moderator, _ = as_role(roles.MODERATOR)
    response = moderator.post(
        CHANGELIST,
        {"action": "bulk_suspend_feed", "_selected_action": [m.pk for m in members]},
    )
    page = response.content.decode()
    assert response.status_code == 200
    for member in members:
        assert member.display_name in page
    for label in ("How long", "7 days", "30 days", "Until a date", "Rule broken", "Reason"):
        assert label in page
    assert not MemberAction.objects.exists()


def test_a_reason_and_a_rule_are_required(as_role, members):
    moderator, _ = as_role(roles.MODERATOR)
    response = bulk(moderator, "warn", members, rule="", reason="")
    assert response.status_code == 200
    assert "This field is required." in response.content.decode()
    assert not MemberAction.objects.exists()


# Each action: the right service, the log, the notice, the way back


def test_warning(as_role, members):
    moderator, actor = as_role(roles.MODERATOR)
    response = bulk(moderator, "warn", members, rule=RULE, reason="Asked twice")
    assert "Send a warning: done for 3" in page_messages(response)[0]
    for member in members:
        action = MemberAction.objects.get(member=member, kind=MemberAction.Kind.WARNING)
        assert action.created_by == actor and action.rule == RULE
        assert logged("warning", member) and notices(member) == 1
    assert sum(message.subject == NOTICE_SUBJECT for message in mail.outbox) == 3
    services.reverse_action(actor, action, "On second thought")
    action.refresh_from_db()
    assert action.is_reversed and logged("reverse_warning", action.member)


def test_feed_suspension_for_seven_days_then_lifted(as_role, members):
    moderator, actor = as_role(roles.MODERATOR)
    bulk(moderator, "suspend_feed", members, length="7", rule=RULE, reason="Cooling off")
    for member in members:
        member.profile.refresh_from_db()
        until = member.profile.feed_suspended_until
        assert timedelta(days=6, hours=23) < until - timezone.now() <= timedelta(days=7)
        assert logged("feed_suspension", member)
    response = bulk(moderator, "lift_suspensions", members, reason="Talked it through")
    assert "Lift suspensions: done for 3" in page_messages(response)[0]
    for member in members:
        member.profile.refresh_from_db()
        assert member.profile.feed_suspended_until is None
        assert logged("reverse_feed_suspension", member)
        assert notices(member) == 2


def test_event_suspension_until_a_date_flags_the_door(as_role, members):
    moderator, _ = as_role(roles.MODERATOR)
    last_day = timezone.localdate() + timedelta(days=10)
    member = members[0]
    bulk(
        moderator,
        "suspend_events",
        [member],
        length="custom",
        until=last_day.isoformat(),
        rule=RULE,
        reason="At the social",
    )
    member.profile.refresh_from_db()
    assert timezone.localtime(member.profile.events_suspended_until).date() == last_day
    assert door_flags(member)["events_suspended_until"] is not None
    bulk(moderator, "lift_suspensions", [member], reason="Appeal heard")
    member.profile.refresh_from_db()
    assert member.profile.events_suspended_until is None


def test_a_custom_date_must_be_given(as_role, members):
    moderator, _ = as_role(roles.MODERATOR)
    response = bulk(moderator, "suspend_feed", members, length="custom", rule=RULE, reason="x")
    assert "Choose the last day." in response.content.decode()


def test_remove_all_feed_content_and_put_it_back(as_role, members, make_post):
    moderator, actor = as_role(roles.MODERATOR)
    member, other = members[0], members[1]
    posts = [make_post(member, caption=f"Mine {n}") for n in range(2)]
    on_theirs = make_post(other)
    comment = services_comment(member, on_theirs)
    bulk(moderator, "remove_content", [member], rule=RULE, reason="Spam wave")
    assert all(FeedPost.objects.get(pk=post.pk).status == FeedPost.Status.REMOVED for post in posts)
    assert FeedComment.objects.get(pk=comment.pk).status == FeedComment.Status.REMOVED
    assert FeedPost.objects.get(pk=on_theirs.pk).status == FeedPost.Status.PUBLISHED
    action = MemberAction.objects.get(member=member, kind=MemberAction.Kind.REMOVE_ALL_CONTENT)
    assert logged("remove_all_content", member) and notices(member) == 1
    services.reverse_action(actor, action, "Not spam after all")
    assert all(
        FeedPost.objects.get(pk=post.pk).status == FeedPost.Status.PUBLISHED for post in posts
    )
    assert FeedComment.objects.get(pk=comment.pk).status == FeedComment.Status.VISIBLE


def services_comment(author, post):
    from apps.feed import services as feed_services

    return feed_services.add_comment(author, post.public_id, "A comment")


def test_ban_needs_an_admin_and_a_fresh_code_and_unban_reverses_it(admin_actor, as_role, members):
    client, actor = admin_actor
    member = members[0]
    moderator, _ = as_role(roles.MODERATOR)
    assert moderator.get(detail_url(member, "ban")).status_code == 403

    data = {"rule": RULE, "reason": "Threats", "block_email": "on"}
    refused = bulk(client, "ban", [member], code="000000", **data)
    assert "That code did not work" in refused.content.decode()
    member.profile.refresh_from_db()
    assert member.profile.feed_banned_at is None

    # A wrong code slows the next attempt down (django-otp's throttle); as if they waited.
    TOTPDevice.objects.get(user=actor).throttle_reset()
    bulk(client, "ban", [member], code=fresh_code(actor), **data)
    member.profile.refresh_from_db()
    assert member.profile.feed_banned_at and member.profile.do_not_admit_at
    assert door_flags(member)["do_not_admit"] is True
    assert BlockedEmail.blocks(member.email) and logged("ban", member)

    next_window(actor)
    bulk(client, "unban", [member], reason="Appeal upheld", code=fresh_code(actor))
    member.profile.refresh_from_db()
    assert member.profile.feed_banned_at is None and member.profile.do_not_admit_at is None
    assert not BlockedEmail.blocks(member.email) and logged("reverse_ban", member)
    assert notices(member) == 2


def test_feed_grant_respects_the_age_check(admin_client, make_user):
    user = make_user(display_name="volunteer_one")
    response = bulk(admin_client, "grant_feed", [user], reason="Volunteer")
    assert "after their ID check" in page_messages(response)[0]
    user.profile.refresh_from_db()
    assert user.profile.feed_access_granted and logged("feed_grant", user) and notices(user) == 1
    from apps.feed.access import can_join_feed

    assert not can_join_feed(user)
    verify_age(user)
    assert can_join_feed(user)
    bulk(admin_client, "revoke_feed", [user], reason="Finished volunteering")
    user.profile.refresh_from_db()
    assert not user.profile.feed_access_granted and logged("feed_grant_revoked", user)


def test_mark_email_verified(admin_client, make_user):
    user = make_user(verified=False)
    bulk(admin_client, "confirm_email", [user], reason="Confirmed by phone")
    user.refresh_from_db()
    assert user.email_verified and logged("email_confirmed_by_staff", user)
    response = bulk(admin_client, "confirm_email", [user], reason="Again")
    assert "already confirmed" in page_messages(response)[0]


def test_password_reset_email(as_role, make_user):
    staff, _ = as_role(roles.STAFF)
    user = make_user(email="forgot@example.org")
    bulk(staff, "password_reset", [user])
    assert any(
        message.to == ["forgot@example.org"] and "/account/reset#uid=" in message.body
        for message in mail.outbox
    )
    assert logged("password_reset_sent", user)


def test_log_out_everywhere(as_role, make_user):
    staff, _ = as_role(roles.STAFF)
    user = make_user()
    before = user.session_epoch
    bulk(staff, "sign_out", [user], reason="Lost phone")
    user.refresh_from_db()
    assert user.session_epoch == before + 1 and logged("signed_out_everywhere", user)
    assert notices(user) == 1


def test_deactivate_and_reactivate(admin_client, make_user):
    user = make_user()
    bulk(admin_client, "deactivate", [user], reason="Asked for a break")
    user.refresh_from_db()
    assert not user.is_active and logged("deactivated", user)
    assert Client().login(email=user.email, password=PASSWORD) is False
    bulk(admin_client, "reactivate", [user], reason="Back")
    user.refresh_from_db()
    assert user.is_active and logged("reactivated", user)


def export(client, users, **data):
    response = bulk(client, "export", users, **data)
    return list(csv.reader(io.StringIO(response.content.decode())))


def test_export_leaves_emails_out_unless_asked_and_logs_each(admin_client, members):
    rows = export(admin_client, members)
    assert rows[0] == ["Display name", "Tier", "Membership status", "Joined"]
    assert sorted(row[0] for row in rows[1:]) == [m.display_name for m in members]
    assert not any("@" in cell for row in rows for cell in row)
    with_email = export(admin_client, members, include_email="on")
    assert with_email[0][-1] == "Email"
    assert {row[-1] for row in with_email[1:]} == {m.email for m in members}
    assert AuditLog.objects.filter(action="member_csv").count() == 1
    entry = AuditLog.objects.get(action="member_csv_with_email")
    assert entry.category == AuditLog.Category.EXPORT and entry.reason


def test_erase_runs_the_full_erasure_and_removes_files(
    admin_actor, member_client, make_post, image_upload, private_root
):
    client, actor = admin_actor
    member_api, member = member_client(display_name="leaving_one")
    member_api.post(
        "/api/members/me/avatar/",
        {"image": image_upload(), "shows_face": "false"},
        format="multipart",
    )
    member.profile.refresh_from_db()
    post = make_post(member, images=2)
    files = [image.image.name for image in post.images.all()] + [member.profile.avatar.name]
    assert all((private_root / name).exists() for name in files)
    services.take_action(
        actor,
        member,
        services.ActionInput(kind="warning", rule=RULE, reason="Earlier"),
    )

    refused = bulk(client, "erase", [member], reason="Asked us", confirm="erase", code="1")
    assert "Type ERASE in capitals." in refused.content.decode()
    assert User.objects.filter(pk=member.pk).exists()

    bulk(client, "erase", [member], reason="Asked us", confirm="ERASE", code=fresh_code(actor))
    assert not User.objects.filter(pk=member.pk).exists()
    assert not any((private_root / name).exists() for name in files)
    assert not FeedPost.objects.filter(pk=post.pk).exists()
    kept = MemberAction.objects.get(rule=RULE)
    assert kept.member is None and kept.member_label == ERASED_MEMBER
    entries = AuditLog.objects.filter(action__in=("warning", "erase_account"))
    assert {entry.target_label for entry in entries} == {ERASED_MEMBER}
    assert not AuditLog.objects.filter(target_label__contains="leaving_one").exists()
    assert any(message.subject == "Your account has been closed" for message in mail.outbox)


# Bulk rules


def test_at_most_fifty_at_once(admin_client, make_user):
    users = [make_user() for _ in range(member_actions.MAX_USERS + 1)]
    response = bulk(admin_client, "sign_out", users, reason="Too many")
    assert "choose at most 50 members at a time; 51 were selected" in page_messages(response)[0]
    assert not AuditLog.objects.filter(action="signed_out_everywhere").exists()


def test_staff_and_superusers_are_skipped_and_listed(admin_actor, as_role, members, make_user):
    client, actor = admin_actor
    _, moderator = as_role(roles.MODERATOR)
    owner = make_user(display_name="other_owner", is_staff=True, is_superuser=True)
    response = bulk(
        client,
        "suspend_feed",
        [*members, moderator, owner, actor],
        length="7",
        rule=RULE,
        reason="Everyone",
    )
    done, skipped = page_messages(response)
    assert "done for 3" in done
    assert "skipped 3" in skipped
    for name in ("team_moderator", "other_owner", actor.display_name):
        assert name in skipped
    assert "your own account" in skipped
    moderator.profile.refresh_from_db()
    assert moderator.profile.feed_suspended_until is None
    for key in ("ban", "erase", "deactivate", "suspend_events"):
        assert member_actions.ACTIONS[key].protected


def test_ban_unban_and_erase_need_a_fresh_code(admin_actor, members):
    client, _ = admin_actor
    member = members[0]
    for key, data in (
        ("ban", {"rule": RULE, "reason": "x"}),
        ("unban", {"reason": "x"}),
        ("erase", {"reason": "x", "confirm": "ERASE"}),
    ):
        assert member_actions.ACTIONS[key].fresh_code
        response = bulk(client, key, [member], code="123456", **data)
        assert "That code did not work" in response.content.decode(), key
    assert User.objects.filter(pk=member.pk).exists()
    member.profile.refresh_from_db()
    assert member.profile.feed_banned_at is None


# Who may do what

EXPECTED = {
    "warn": roles.MODERATOR,
    "suspend_feed": roles.MODERATOR,
    "suspend_events": roles.MODERATOR,
    "lift_suspensions": roles.MODERATOR,
    "remove_content": roles.MODERATOR,
    "ban": roles.ADMIN,
    "unban": roles.ADMIN,
    "grant_feed": roles.ADMIN,
    "revoke_feed": roles.ADMIN,
    "confirm_email": roles.ADMIN,
    "password_reset": roles.STAFF,
    "sign_out": roles.STAFF,
    "deactivate": roles.ADMIN,
    "reactivate": roles.ADMIN,
    "export": roles.ADMIN,
    "erase": roles.ADMIN,
}


def test_every_action_is_listed_with_its_role():
    assert {key: spec.role for key, spec in member_actions.ACTIONS.items()} == EXPECTED


@pytest.mark.parametrize("role", roles.ROLES)
def test_each_role_sees_and_opens_only_its_actions(as_role, make_member, role):
    client, _ = as_role(role)
    member = make_member()
    page = client.get(CHANGELIST).content.decode()
    detail = client.get(reverse("admin:accounts_user_change", args=(member.pk,))).content
    for key, minimum in EXPECTED.items():
        allowed = roles.RANK[role] >= roles.RANK[minimum]
        assert (f'value="bulk_{key}"' in page) is allowed, (role, key)
        assert (detail_url(member, key).encode() in detail) is allowed, (role, key)
        assert (client.get(detail_url(member, key)).status_code == 200) is allowed, (role, key)


def test_people_without_a_team_role_cannot_open_members(desk_staff, make_member):
    client = staff_login(Client(), desk_staff)
    assert client.get(CHANGELIST).status_code == 403
    response = client.post(
        CHANGELIST, {"action": "bulk_warn", "_selected_action": [make_member().pk], "apply": "1"}
    )
    assert response.status_code == 403
    assert not MemberAction.objects.exists()


# Delete is gone


def test_no_admin_path_deletes_a_user_without_the_erasure(admin_client, make_member, monkeypatch):
    member = make_member()
    erased = []
    monkeypatch.setattr("apps.accounts.erasure.erase_account", erased.append)
    for model_admin in [a for m, a in admin.site._registry.items() if m is User]:
        assert model_admin.has_delete_permission(None) is False
        assert "delete_selected" not in model_admin.get_actions(_superuser_request(admin_client))
    page = admin_client.get(reverse("admin:accounts_user_change", args=(member.pk,))).content
    assert b"/delete/" not in page
    assert admin_client.get(f"{CHANGELIST}{member.pk}/delete/").status_code == 403
    assert admin_client.post(f"{CHANGELIST}{member.pk}/delete/", {"post": "yes"}).status_code == 403
    admin_client.post(CHANGELIST, {"action": "delete_selected", "_selected_action": [member.pk]})
    assert User.objects.filter(pk=member.pk).exists() and erased == []


def _superuser_request(client):
    from django.test import RequestFactory

    request = RequestFactory().get(CHANGELIST)
    request.user = User.objects.get(is_superuser=True)
    return request


def test_the_profile_page_cannot_change_suspensions_bans_or_the_grant(admin_client, make_member):
    member = make_member()
    page = admin_client.get(
        reverse("admin:accounts_profile_change", args=(member.profile.pk,))
    ).content.decode()
    for field in (
        "feed_suspended_until",
        "events_suspended_until",
        "feed_banned_at",
        "do_not_admit_at",
        "feed_access_granted",
    ):
        assert f'name="{field}"' not in page, field


# The account page


def test_the_account_page_has_the_action_bar_history_and_membership(
    admin_actor, make_member, make_membership, make_post
):
    client, actor = admin_actor
    member = make_member(display_name="history_one")
    membership = make_membership(user=member)
    reporter = make_member(display_name="secret_reporter")
    post = make_post(member)
    report = Report.objects.create(
        reporter=reporter, target_type="post", post=post, reason="harassment"
    )
    services.take_action(
        actor, member, services.ActionInput(kind="warning", rule=RULE, reason="Be kind")
    )
    page = client.get(reverse("admin:accounts_user_change", args=(member.pk,))).content.decode()
    for text in ("Moderation", "Account", "Send a warning", "Erase account"):
        assert text in page
    assert "Moderation history" in page and "Be kind" in page and RULE in page
    assert "secret_reporter" not in page and "Hidden" in page
    assert membership.reference_code in page
    assert reverse("admin:memberships_membership_change", args=(membership.pk,)) in page

    reveal = reverse("admin:accounts_user_reveal_reporter", args=(member.pk, report.pk))
    assert reveal in page
    assert "secret_reporter" not in client.get(reveal).content.decode()
    shown = client.post(reveal).content.decode()
    assert "secret_reporter" in shown
    assert AuditLog.objects.filter(action="reveal_reporter", actor=actor).count() == 1


def test_only_admins_reveal_a_reporter(as_role, make_member, make_post):
    moderator, _ = as_role(roles.MODERATOR)
    member = make_member()
    report = Report.objects.create(
        reporter=make_member(), target_type="post", post=make_post(member), reason="spam"
    )
    page = moderator.get(reverse("admin:accounts_user_change", args=(member.pk,))).content
    reveal = reverse("admin:accounts_user_reveal_reporter", args=(member.pk, report.pk))
    assert reveal.encode() not in page
    assert moderator.post(reveal).status_code == 403
    assert not AuditLog.objects.filter(action="reveal_reporter").exists()


def test_a_single_account_action_from_its_page(as_role, make_member):
    moderator, _ = as_role(roles.MODERATOR)
    member = make_member()
    form = moderator.get(detail_url(member, "warn")).content.decode()
    assert member.display_name in form and "Rule broken" in form
    response = moderator.post(
        detail_url(member, "warn"),
        {"apply": "1", "rule": RULE, "reason": "From the page"},
        follow=True,
    )
    assert response.redirect_chain[-1][0] == reverse(
        "admin:accounts_user_change", args=(member.pk,)
    )
    assert MemberAction.objects.filter(member=member, reason="From the page").exists()
