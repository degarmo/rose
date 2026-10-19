"""Reports, member actions and appeals. Every step that changes something is logged in
core.AuditLog (moderation category), which can never be edited or deleted.

Privacy rules kept here:
- The reported member never learns who reported them; reporters only learn that their
  report was received, then reviewed.
- Emails are discreet: a neutral subject and a link to Settings, never what
  happened or what was said.
"""

from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone

from apps.core.models import AuditLog, audit
from apps.feed.models import FeedComment, FeedPost, Notification, Report
from apps.feed.services import notify

from . import emails, roles
from .models import Appeal, BlockedEmail, MemberAction, ReportNote, email_hash

MAX_SUSPENSION_DAYS = 3650


class SafetyError(Exception):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def _on_commit(func):
    transaction.on_commit(func)


def _log(actor, action, label, target_type, target_user=None, ref="", reason=""):
    return audit(
        AuditLog.Category.MODERATION,
        action,
        actor,
        label,
        target_type,
        target_user=target_user,
        target_ref=str(ref),
        reason=reason,
    )


def _team_alert():
    recipients = list(roles.team_members().values_list("email", flat=True))
    _on_commit(lambda: emails.alert_team(recipients))


# Concerns


def file_concern(
    reporter, details, event=None, event_date=None, reported_name="", contact_email=""
):
    """Something that happened at an event or the club, from the app or the website."""
    details = details.strip()
    if not details:
        raise SafetyError("details", "Tell us what happened.")
    report = Report.objects.create(
        reporter=reporter,
        target_type=Report.TargetType.EVENT,
        reason=Report.Reason.OTHER,
        details=details,
        event=event,
        event_date=event_date,
        reported_name=reported_name.strip(),
        contact_email="" if reporter else contact_email.strip(),
    )
    _team_alert()
    if report.contact_email:
        address = report.contact_email
        _on_commit(lambda: emails.concern_received(address))
    return report


# The report workflow


def assign(actor, report, assignee):
    if assignee is not None and not roles.has_role(assignee, roles.MODERATOR):
        raise SafetyError("assignee", "Choose someone on the team.")
    report.assigned_to = assignee
    if assignee is not None and report.status == Report.Status.OPEN:
        report.status = Report.Status.IN_REVIEW
    report.save(update_fields=["assigned_to", "status"])
    who = assignee.display_name if assignee else "nobody"
    _log(actor, "report_assigned", f"Report {report.pk}", "report", ref=report.pk, reason=who)
    return report


def add_note(actor, report, body):
    body = body.strip()
    if not body:
        raise SafetyError("body", "Write a note first.")
    note = ReportNote.objects.create(report=report, author=actor, body=body)
    _log(actor, "report_note", f"Report {report.pk}", "report", ref=report.pk)
    return note


def set_status(actor, report, status, resolution=""):
    """Move a report through open, in review, resolved and dismissed."""
    if status not in Report.Status.values:
        raise SafetyError("status", "Choose a status.")
    was_closed = report.status in Report.CLOSED
    report.status = status
    if status in Report.CLOSED:
        report.resolved_at = report.resolved_at or timezone.now()
        report.resolution = resolution or status
    else:
        report.resolved_at = None
        report.resolution = ""
    contact = report.contact_email
    if status in Report.CLOSED:
        report.contact_email = ""
    report.save(update_fields=["status", "resolved_at", "resolution", "contact_email"])
    _log(actor, f"report_{status}", f"Report {report.pk}", "report", ref=report.pk)
    if status in Report.CLOSED and not was_closed:
        _tell_reporter_reviewed(report, contact)
    return report


def _tell_reporter_reviewed(report, contact_email):
    """Neutral: that it was reviewed, never what was decided."""
    if report.reporter_id:
        notify(
            report.reporter,
            Notification.Kind.NOTICE,
            "A report you sent has been reviewed. Thank you for telling us.",
        )
    elif contact_email:
        _on_commit(lambda: emails.concern_reviewed(contact_email))


def reveal_reporter(actor, report):
    """Admins only. The reveal itself is logged."""
    if not roles.has_role(actor, roles.ADMIN):
        raise SafetyError("forbidden", "Only an admin can see who sent a report.", 403)
    audit(
        AuditLog.Category.PRIVATE_DATA,
        "reveal_reporter",
        actor,
        f"Report {report.pk}",
        "report",
        target_user=report.reporter,
        target_ref=str(report.pk),
    )
    if report.reporter_id:
        return {"display_name": report.reporter.display_name, "contact_email": ""}
    return {"display_name": None, "contact_email": report.contact_email}


def history(member):
    """A member's moderation history, as staff see it: reports about them and actions."""
    about = Report.objects.filter(
        Q(post__author=member) | Q(comment__author=member) | Q(profile_user=member)
    )
    return {
        "reports": about.count(),
        "actions": list(member.moderation_actions.select_related("created_by")),
    }


# Member actions


@dataclass
class ActionInput:
    kind: str
    rule: str
    reason: str
    report: Report | None = None
    post: FeedPost | None = None
    comment: FeedComment | None = None
    days: int | None = None
    until: object = None
    block_email: bool = False


def _ends_at(data, now):
    if data.until is not None:
        if data.until <= now:
            raise SafetyError("until", "Choose an end date in the future.")
        return data.until
    if not data.days or not 1 <= data.days <= MAX_SUSPENSION_DAYS:
        raise SafetyError("days", "Choose how long it lasts.")
    return now + timedelta(days=data.days)


def _latest_end(member, kind, now, exclude=None):
    """The furthest end of the member's other suspensions of this kind still in force."""
    others = MemberAction.objects.filter(member=member, kind=kind, reversed_at__isnull=True)
    if exclude is not None:
        others = others.exclude(pk=exclude.pk)
    return others.filter(ends_at__gt=now).aggregate(end=Max("ends_at"))["end"]


def _end_memberships(member):
    from apps.memberships.account import close_for_deleted_account

    close_for_deleted_account(member)


def take_action(actor, member, data):
    """Apply one action. A reason and the rule it relates to are always required."""
    K = MemberAction.Kind
    if data.kind not in K.values:
        raise SafetyError("kind", "Choose an action.")
    if not data.rule.strip():
        raise SafetyError("rule", "Choose the rule this relates to.")
    if not data.reason.strip():
        raise SafetyError("reason", "Give a reason.")
    if member == actor:
        raise SafetyError("member", "You cannot take an action on your own account.")
    now = timezone.now()
    profile = member.profile
    action = MemberAction(
        member=member,
        kind=data.kind,
        rule=data.rule.strip(),
        reason=data.reason.strip(),
        report=data.report,
        created_by=actor,
    )
    with transaction.atomic():
        if data.kind == K.REMOVE_CONTENT:
            target = data.post or data.comment
            if target is None or target.author_id != member.pk:
                raise SafetyError("target", "Choose a post or comment by this member.")
            action.post, action.comment = data.post, data.comment
            action.previous_status = target.status
            if data.post:
                data.post.status = FeedPost.Status.REMOVED
                data.post.removed_reason = action.reason
                data.post.removed_by = actor
                data.post.save(update_fields=["status", "removed_reason", "removed_by"])
            else:
                data.comment.status = FeedComment.Status.REMOVED
                data.comment.save(update_fields=["status"])
        elif data.kind == K.FEED_SUSPENSION:
            action.ends_at = _ends_at(data, now)
            profile.feed_suspended_until = max(
                filter(None, [profile.feed_suspended_until, action.ends_at])
            )
            profile.save(update_fields=["feed_suspended_until", "updated_at"])
        elif data.kind == K.EVENT_SUSPENSION:
            action.ends_at = _ends_at(data, now)
            profile.events_suspended_until = max(
                filter(None, [profile.events_suspended_until, action.ends_at])
            )
            profile.save(update_fields=["events_suspended_until", "updated_at"])
        elif data.kind == K.BAN:
            action.block_email = data.block_email
            profile.feed_banned_at = profile.feed_banned_at or now
            profile.do_not_admit_at = profile.do_not_admit_at or now
            profile.save(update_fields=["feed_banned_at", "do_not_admit_at", "updated_at"])
            _end_memberships(member)
            from apps.events.services import release_places_held_by

            release_places_held_by(member)
        action.save()
        if data.kind == K.BAN and data.block_email:
            BlockedEmail.objects.get_or_create(
                email_hash=email_hash(member.email), defaults={"action": action}
            )
        if data.report is not None and data.report.status not in Report.CLOSED:
            set_status(actor, data.report, Report.Status.RESOLVED, resolution=data.kind)
        _log(
            actor,
            data.kind,
            f"Member {member.display_name}",
            "user",
            target_user=member,
            ref=action.pk,
            reason=f"{action.rule}: {action.reason}",
        )
        _tell_member(member, "A moderation decision about your account was recorded.")
    return action


def _tell_member(member, message):
    """An in-app notice that opens Settings > Notices, and a discreet email pointing there."""
    details = "The details are in Settings, under Notices."
    notify(member, Notification.Kind.NOTICE, f"{message} {details}")
    address = member.email
    _on_commit(lambda: emails.account_update(address))


def reverse_action(actor, action, reason):
    """Undo an action. Only the log stays as it was."""
    K = MemberAction.Kind
    if not reason.strip():
        raise SafetyError("reason", "Give a reason for reversing it.")
    if action.is_reversed:
        raise SafetyError("reversed", "This action has already been reversed.")
    now = timezone.now()
    member = action.member
    profile = member.profile
    with transaction.atomic():
        if action.kind == K.REMOVE_CONTENT:
            target = action.post or action.comment
            if target is not None and target.status in (
                FeedPost.Status.REMOVED,
                FeedComment.Status.REMOVED,
            ):
                target.status = action.previous_status
                fields = ["status"]
                if action.post is not None:
                    target.removed_reason = ""
                    target.removed_by = None
                    fields += ["removed_reason", "removed_by"]
                target.save(update_fields=fields)
        elif action.kind == K.FEED_SUSPENSION:
            profile.feed_suspended_until = _latest_end(member, action.kind, now, exclude=action)
            profile.save(update_fields=["feed_suspended_until", "updated_at"])
        elif action.kind == K.EVENT_SUSPENSION:
            profile.events_suspended_until = _latest_end(member, action.kind, now, exclude=action)
            profile.save(update_fields=["events_suspended_until", "updated_at"])
        elif action.kind == K.BAN:
            other_bans = MemberAction.objects.filter(
                member=member, kind=K.BAN, reversed_at__isnull=True
            ).exclude(pk=action.pk)
            if not other_bans.exists():
                profile.feed_banned_at = None
                profile.do_not_admit_at = None
                profile.save(update_fields=["feed_banned_at", "do_not_admit_at", "updated_at"])
            action.blocked_emails.all().delete()
        action.reversed_at = now
        action.reversed_by = actor
        action.reversal_reason = reason.strip()
        action.save(update_fields=["reversed_at", "reversed_by", "reversal_reason"])
        _log(
            actor,
            f"reverse_{action.kind}",
            f"Member {member.display_name}",
            "user",
            target_user=member,
            ref=action.pk,
            reason=action.reversal_reason,
        )
        _tell_member(member, "A moderation decision about your account was reversed.")
    return action


# Appeals


def _reviewer_for(action):
    """Someone on the team other than the moderator who acted, with the fewest open appeals."""
    candidates = roles.team_members().exclude(pk=action.created_by_id)
    return min(candidates, key=lambda person: (_open_appeals(person), person.pk), default=None)


def _open_appeals(person):
    return Appeal.objects.filter(assigned_to=person, status=Appeal.Status.OPEN).count()


def submit_appeal(member, action, text):
    if action.member_id != member.pk:
        raise SafetyError("action", "That decision is not yours to appeal.", 404)
    text = text.strip()
    if not text:
        raise SafetyError("text", "Tell us why you think this was wrong.")
    if action.is_reversed:
        raise SafetyError("reversed", "This decision has already been reversed.")
    if Appeal.objects.filter(action=action).exists():
        raise SafetyError("exists", "You have already appealed this decision.", 409)
    appeal = Appeal.objects.create(action=action, text=text, assigned_to=_reviewer_for(action))
    _log(
        member,
        "appeal_submitted",
        f"Appeal on action {action.pk}",
        "appeal",
        target_user=member,
        ref=appeal.pk,
    )
    _team_alert()
    return appeal


def may_decide(actor, appeal):
    """Not the moderator who acted, unless nobody else on the team could."""
    if actor.pk != appeal.action.created_by_id:
        return True
    return not roles.team_members().exclude(pk=actor.pk).exists()


def decide_appeal(actor, appeal, decision, note):
    if appeal.status != Appeal.Status.OPEN:
        raise SafetyError("decided", "This appeal has already been decided.")
    if not may_decide(actor, appeal):
        raise SafetyError(
            "reviewer", "Someone other than the moderator who acted must review this appeal.", 403
        )
    if decision not in ("uphold", "reverse"):
        raise SafetyError("decision", "Choose to uphold or reverse the decision.")
    if not note.strip():
        raise SafetyError("note", "Give a reason for the decision.")
    with transaction.atomic():
        if decision == "reverse":
            reverse_action(actor, appeal.action, note)
            appeal.status = Appeal.Status.REVERSED
        else:
            appeal.status = Appeal.Status.UPHELD
            _tell_member(appeal.action.member, "Your appeal has been reviewed.")
        appeal.decided_by = actor
        appeal.decided_at = timezone.now()
        appeal.decision_note = note.strip()
        appeal.save(update_fields=["status", "decided_by", "decided_at", "decision_note"])
        _log(
            actor,
            f"appeal_{appeal.status}",
            f"Appeal on action {appeal.action_id}",
            "appeal",
            target_user=appeal.action.member,
            ref=appeal.pk,
            reason=appeal.decision_note,
        )
    return appeal


# Team


def change_role(actor, user, role):
    if not roles.has_role(actor, roles.ADMIN):
        raise SafetyError("forbidden", "Only an admin can change the team.", 403)
    if role is not None and role not in roles.ROLES:
        raise SafetyError("role", "Choose a role.")
    if user == actor:
        raise SafetyError("self", "Ask another admin to change your own role.")
    if user.is_superuser:
        raise SafetyError("superuser", "A superuser is always an admin.")
    roles.set_role(user, role)
    audit(
        AuditLog.Category.SECURITY,
        "team_role",
        actor,
        f"Member {user.display_name}",
        "user",
        target_user=user,
        reason=roles.LABELS.get(role, "No role"),
    )


# The member's own Notices


def unread_notices(member):
    """Decisions about this member, or updates to them (an appeal decided, a reversal),
    since they last opened Settings > Notices."""
    actions = MemberAction.objects.filter(member=member)
    seen = member.profile.notices_seen_at
    if seen is not None:
        actions = actions.filter(
            Q(created_at__gt=seen) | Q(reversed_at__gt=seen) | Q(appeal__decided_at__gt=seen)
        )
    return actions.distinct().count()


def mark_notices_seen(member):
    member.profile.notices_seen_at = timezone.now()
    member.profile.save(update_fields=["notices_seen_at", "updated_at"])
