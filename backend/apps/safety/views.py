"""The staff section's API (/api/staff/), the member's own notices and appeals
(/api/account/notices/, /api/account/reports/) and the concern form (/api/concerns/).

Nothing here describes a reporter to anyone but an admin who asks (and that is logged),
and nothing describes a member's activity: staff see reports about them and the actions
taken, never what they do in the app.
"""

from datetime import datetime

from django.conf import settings
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django_ratelimit.core import is_ratelimited
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.core.api import CsrfProtectedAPIView, too_many_requests
from apps.core.models import AuditLog, audit
from apps.core.ratelimit import hashed_ip_key
from apps.events.models import Event
from apps.feed.models import FeedImage, Report
from apps.feed.views import deliver_image
from apps.pages.content import page_entries

from . import metrics, roles, services
from .api import StaffAPIView
from .models import Appeal, MemberAction
from .services import ActionInput, SafetyError

PAGE = 50


# Shapes


def _person(user):
    return {"display_name": user.display_name} if user else None


def _when(moment):
    return moment.isoformat() if moment else None


def action_payload(action, for_member=False):
    data = {
        "id": action.pk,
        "kind": action.kind,
        "kind_label": action.get_kind_display(),
        "rule": action.rule,
        "reason": action.reason,
        "created_at": _when(action.created_at),
        "ends_at": _when(action.ends_at),
        "in_force": action.is_in_force(),
        "reversed_at": _when(action.reversed_at),
        "reversal_reason": action.reversal_reason,
        "appeal": None,
    }
    # A missing one-to-one row raises an AttributeError subclass, so getattr's default applies.
    appeal = getattr(action, "appeal", None)
    if appeal is not None:
        data["appeal"] = {
            "id": appeal.pk,
            "status": appeal.status,
            "status_label": appeal.get_status_display(),
            "created_at": _when(appeal.created_at),
            "decided_at": _when(appeal.decided_at),
        }
    if not for_member:
        data["created_by"] = _person(action.created_by)
        data["reversed_by"] = _person(action.reversed_by)
        data["member"] = _person(action.member)
        data["report_id"] = action.report_id
    return data


def _excerpt(text, length=140):
    text = " ".join(text.split())
    return text if len(text) <= length else f"{text[: length - 1]}…"


def report_summary(report):
    member = report.reported_member
    if report.target_type == Report.TargetType.EVENT:
        preview = report.details
        subject = report.reported_name or None
    elif report.target_type == Report.TargetType.POST:
        preview = report.post.caption if report.post else ""
        subject = member.display_name if member else None
    elif report.target_type == Report.TargetType.COMMENT:
        preview = report.comment.body if report.comment else ""
        subject = member.display_name if member else None
    else:
        preview = ""
        subject = member.display_name if member else None
    return {
        "id": report.pk,
        "kind": report.target_type,
        "kind_label": report.get_target_type_display(),
        "reason": report.reason,
        "reason_label": report.get_reason_display(),
        "status": report.status,
        "status_label": report.get_status_display(),
        "created_at": _when(report.created_at),
        "assigned_to": _person(report.assigned_to),
        "subject": subject,
        "subject_is_member": member is not None,
        "preview": _excerpt(preview),
        "from_website": report.target_type == Report.TargetType.EVENT and not report.reporter_id,
    }


def _content(report):
    """What was reported, for staff. Pictures go through the staff media path."""
    kind = report.target_type
    if kind == Report.TargetType.POST and report.post:
        post = report.post
        return {
            "caption": post.caption,
            "status": post.status,
            "is_sensitive": post.is_sensitive,
            "images": [
                f"/api/staff/media/{image.public_id}/"
                for image in post.images.order_by("position")
                if image.image
            ],
        }
    if kind == Report.TargetType.COMMENT and report.comment:
        comment = report.comment
        return {
            "body": comment.body,
            "status": comment.status,
            "post_caption": comment.post.caption,
        }
    if kind == Report.TargetType.PROFILE and report.profile_user:
        profile = report.profile_user.profile
        return {"bio": profile.bio, "has_avatar": bool(profile.avatar)}
    if kind == Report.TargetType.EVENT:
        return {
            "event": report.event.title if report.event else None,
            "event_starts_at": _when(report.event.starts_at) if report.event else None,
            "event_date": report.event_date.isoformat() if report.event_date else None,
            "reported_name": report.reported_name,
        }
    return {"removed": True}


def report_detail(report, viewer):
    member = report.reported_member
    history = services.history(member) if member else None
    return {
        **report_summary(report),
        "details": report.details,
        "content": _content(report),
        "reporter": {"hidden": True, "can_reveal": roles.has_role(viewer, roles.ADMIN)},
        "member": (
            {
                "display_name": member.display_name,
                "prior_reports": max(0, history["reports"] - 1),
                "actions": [action_payload(a) for a in history["actions"]],
            }
            if member
            else None
        ),
        "notes": [
            {"author": _person(n.author), "body": n.body, "created_at": _when(n.created_at)}
            for n in report.notes.select_related("author")
        ],
        "actions": [action_payload(a) for a in report.actions.select_related("created_by")],
        "team": [_person(p) for p in roles.team_members()],
    }


def appeal_payload(appeal, viewer):
    action = appeal.action
    return {
        "id": appeal.pk,
        "status": appeal.status,
        "status_label": appeal.get_status_display(),
        "text": appeal.text,
        "created_at": _when(appeal.created_at),
        "assigned_to": _person(appeal.assigned_to),
        "decided_by": _person(appeal.decided_by),
        "decided_at": _when(appeal.decided_at),
        "decision_note": appeal.decision_note,
        "action": action_payload(action),
        "may_decide": services.may_decide(viewer, appeal),
    }


# Staff: overview, metrics and the team


class OverviewView(StaffAPIView):
    """Badge counts for the staff navigation."""

    def get(self, request):
        role = roles.role_of(request.user)
        return Response(
            {
                "role": role,
                "open_reports": Report.objects.filter(
                    status__in=[Report.Status.OPEN, Report.Status.IN_REVIEW]
                ).count(),
                "open_appeals": Appeal.objects.filter(status=Appeal.Status.OPEN).count(),
                "can_see_metrics": roles.has_role(request.user, roles.STAFF),
                "can_manage_team": roles.has_role(request.user, roles.ADMIN),
            }
        )


class MetricsView(StaffAPIView):
    minimum_role = roles.STAFF

    def get(self, request):
        return Response(metrics.dashboard(request.query_params.get("range", "30d")))


class MetricsExportView(StaffAPIView):
    minimum_role = roles.STAFF

    def post(self, request):
        range_key = str(request.data.get("range", "30d"))
        data = metrics.dashboard(range_key)
        audit(
            AuditLog.Category.EXPORT,
            "metrics_export",
            request.user,
            f"Staff metrics ({data['range']})",
            "metrics",
        )
        response = HttpResponse(metrics.export_csv(data), content_type="text/csv; charset=utf-8")
        stamp = timezone.localdate().isoformat()
        response["Content-Disposition"] = (
            f'attachment; filename="metrics-{data["range"]}-{stamp}.csv"'
        )
        response["Cache-Control"] = "private, no-store"
        return response


class TeamView(StaffAPIView):
    minimum_role = roles.ADMIN

    def get(self, request):
        return Response(
            [
                {
                    "display_name": person.display_name,
                    "role": roles.role_of(person),
                    "is_superuser": person.is_superuser,
                    "is_self": person == request.user,
                }
                for person in roles.team_members()
            ]
        )

    def post(self, request):
        lookup = str(request.data.get("person", "")).strip()
        role = request.data.get("role") or None
        user = User.objects.filter(
            Q(email__iexact=lookup) | Q(display_name__iexact=lookup), is_active=True
        ).first()
        if user is None:
            return Response(
                {"detail": "Nobody has that email or display name.", "code": "person"}, status=400
            )
        services.change_role(request.user, user, role)
        return self.get(request)


# Staff: reports, members and actions


class ReportListView(StaffAPIView):
    def get(self, request):
        status_filter = request.query_params.get("status", Report.Status.OPEN)
        reports = Report.objects.select_related(
            "post__author", "comment__author", "profile_user", "assigned_to"
        )
        if status_filter in Report.Status.values:
            reports = reports.filter(status=status_filter)
        if request.query_params.get("mine") == "1":
            reports = reports.filter(assigned_to=request.user)
        reports = reports.order_by("-created_at")[:PAGE]
        return Response([report_summary(report) for report in reports])


def _report(pk):
    return get_object_or_404(
        Report.objects.select_related(
            "post__author", "comment__author", "comment__post", "profile_user__profile", "event"
        ),
        pk=pk,
    )


class ReportDetailView(StaffAPIView):
    def get(self, request, pk):
        return Response(report_detail(_report(pk), request.user))


class ReportStatusView(StaffAPIView):
    def post(self, request, pk):
        report = services.set_status(request.user, _report(pk), str(request.data.get("status", "")))
        return Response(report_detail(report, request.user))


class ReportAssignView(StaffAPIView):
    def post(self, request, pk):
        name = request.data.get("assignee")
        assignee = None
        if name:
            assignee = get_object_or_404(User, display_name__iexact=str(name), is_active=True)
        report = services.assign(request.user, _report(pk), assignee)
        return Response(report_detail(report, request.user))


class ReportNoteView(StaffAPIView):
    def post(self, request, pk):
        report = _report(pk)
        services.add_note(request.user, report, str(request.data.get("body", "")))
        return Response(report_detail(report, request.user), status=201)


class ReportRevealView(StaffAPIView):
    minimum_role = roles.ADMIN

    def post(self, request, pk):
        return Response(services.reveal_reporter(request.user, _report(pk)))


class RulesView(StaffAPIView):
    """Suggestions for an action's rule: the house rules' titles and the guidelines."""

    def get(self, request):
        entries = page_entries("rules")
        titles = [
            entries[key]["value"]
            for key in sorted(entries, key=_rule_order)
            if key.startswith("rules.") and key.endswith(".title") and entries[key]["value"]
        ]
        return Response(titles + ["Community guidelines", "Membership agreement"])


def _rule_order(key):
    parts = key.split(".")
    return int(parts[1]) if len(parts) > 2 and parts[1].isdigit() else 0


def _member(handle):
    return get_object_or_404(User.objects.select_related("profile"), display_name__iexact=handle)


def member_payload(member):
    from apps.memberships.join import open_membership

    profile = member.profile
    membership = open_membership(member)
    history = services.history(member)
    now = timezone.now()
    return {
        "display_name": member.display_name,
        "membership": (
            {"tier": membership.tier.name, "status": membership.get_status_display()}
            if membership
            else None
        ),
        "flags": {
            "feed_suspended_until": _when(profile.feed_suspended_until)
            if profile.is_feed_suspended(now)
            else None,
            "events_suspended_until": _when(profile.events_suspended_until)
            if profile.is_events_suspended(now)
            else None,
            "banned": profile.do_not_admit_at is not None or profile.is_feed_banned,
        },
        "reports_about": history["reports"],
        "actions": [action_payload(a) for a in history["actions"]],
    }


class MemberSearchView(StaffAPIView):
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return Response([])
        people = User.objects.filter(display_name__icontains=query, is_active=True).order_by(
            "display_name"
        )[:10]
        return Response([_person(person) for person in people])


class MemberDetailView(StaffAPIView):
    def get(self, request, handle):
        return Response(member_payload(_member(handle)))


def _parse_until(value):
    if not value:
        return None
    day = parse_date(str(value))
    if day is None:
        raise SafetyError("until", "Choose a date.")
    return timezone.make_aware(datetime.combine(day, datetime.max.time()))


class MemberActionView(StaffAPIView):
    parser_classes = [JSONParser]

    def post(self, request, handle):
        member = _member(handle)
        data = request.data
        report = None
        post = comment = None
        if data.get("report_id"):
            report = _report(data["report_id"])
            if report.reported_member != member:
                raise SafetyError("report", "That report is not about this member.")
        kind = str(data.get("kind", ""))
        if kind == MemberAction.Kind.REMOVE_CONTENT:
            if report is None or report.target_type not in (
                Report.TargetType.POST,
                Report.TargetType.COMMENT,
            ):
                raise SafetyError("target", "Remove content from the report about it.")
            post, comment = report.post, report.comment
        try:
            days = int(data["days"]) if data.get("days") else None
        except (TypeError, ValueError) as exc:
            raise SafetyError("days", "Choose how many days.") from exc
        action = services.take_action(
            request.user,
            member,
            ActionInput(
                kind=kind,
                rule=str(data.get("rule", "")),
                reason=str(data.get("reason", "")),
                report=report,
                post=post,
                comment=comment,
                days=days,
                until=_parse_until(data.get("until")),
                block_email=bool(data.get("block_email")),
            ),
        )
        return Response(action_payload(action), status=201)


class ActionReverseView(StaffAPIView):
    def post(self, request, pk):
        action = get_object_or_404(MemberAction.objects.select_related("member__profile"), pk=pk)
        services.reverse_action(request.user, action, str(request.data.get("reason", "")))
        action.refresh_from_db()
        return Response(action_payload(action))


class AppealListView(StaffAPIView):
    def get(self, request):
        appeals = Appeal.objects.select_related(
            "action__member", "action__created_by", "assigned_to", "decided_by"
        )
        status_filter = request.query_params.get("status", Appeal.Status.OPEN)
        if status_filter in Appeal.Status.values:
            appeals = appeals.filter(status=status_filter)
        return Response([appeal_payload(a, request.user) for a in appeals[:PAGE]])


class AppealDetailView(StaffAPIView):
    def get(self, request, pk):
        return Response(appeal_payload(get_object_or_404(Appeal, pk=pk), request.user))


class AppealDecideView(StaffAPIView):
    def post(self, request, pk):
        appeal = get_object_or_404(Appeal.objects.select_related("action__member"), pk=pk)
        services.decide_appeal(
            request.user,
            appeal,
            str(request.data.get("decision", "")),
            str(request.data.get("note", "")),
        )
        appeal.refresh_from_db()
        return Response(appeal_payload(appeal, request.user))


class StaffMediaView(StaffAPIView):
    """A reported post's picture for the team, watermarked with the viewer's name."""

    def get(self, request, public_id):
        image = (
            FeedImage.objects.filter(public_id=public_id, post__reports__isnull=False)
            .exclude(image="")
            .first()
        )
        if image is None:
            raise Http404
        return deliver_image(request, image.image.name)


# Members: their own notices, appeals and reports


class NoticeListView(APIView):
    """The signed-in person's own moderation decisions. Never who reported them."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        actions = MemberAction.objects.filter(member=request.user).select_related("appeal")
        return Response([action_payload(a, for_member=True) for a in actions])


class NoticesSeenView(CsrfProtectedAPIView):
    """Opening Settings > Notices marks everything there as seen."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        services.mark_notices_seen(request.user)
        return Response({"unread_notices": 0})


class NoticeAppealView(CsrfProtectedAPIView):
    permission_classes = [IsAuthenticated]
    write_limit = "ACCOUNT_WRITE_RATE_LIMIT"

    def post(self, request, pk):
        action = get_object_or_404(MemberAction, pk=pk, member=request.user)
        try:
            services.submit_appeal(request.user, action, str(request.data.get("text", "")))
        except SafetyError as exc:
            return Response({"detail": exc.message, "code": exc.code}, status=exc.status)
        action = MemberAction.objects.select_related("appeal").get(pk=action.pk)
        return Response(action_payload(action, for_member=True), status=201)


class MyReportsView(APIView):
    """Reports and concerns you sent: received, then reviewed. Never the outcome."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        reports = Report.objects.filter(reporter=request.user).order_by("-created_at")[:PAGE]
        return Response(
            [
                {
                    "id": report.pk,
                    "kind_label": report.get_target_type_display(),
                    "created_at": _when(report.created_at),
                    "status": report.reporter_status,
                }
                for report in reports
            ]
        )


class ConcernView(CsrfProtectedAPIView):
    """Report a concern: anyone, signed in or not. Staff are told without the text."""

    def post(self, request):
        if is_ratelimited(
            request._request,
            group="concern",
            key=hashed_ip_key,
            rate=settings.CONTACT_RATE_LIMIT,
            method="POST",
            increment=True,
        ):
            return too_many_requests("Too many messages. Please try again later.")
        data = request.data
        if data.get("website"):
            # Honeypot tripped: look successful, store nothing.
            return Response({"ok": True}, status=status.HTTP_201_CREATED)
        details = str(data.get("details", ""))
        if len(details) > 4000:
            return Response({"detail": "Please keep it under 4,000 characters."}, status=400)
        event = None
        if data.get("event"):
            event = Event.objects.visible_to(request.user).filter(slug=str(data["event"])).first()
        event_date = parse_date(str(data["event_date"])) if data.get("event_date") else None
        contact_email = str(data.get("contact_email", "")).strip()
        if contact_email and "@" not in contact_email:
            return Response({"detail": "Check the email address.", "code": "contact_email"}, 400)
        reporter = request.user if request.user.is_authenticated else None
        try:
            services.file_concern(
                reporter,
                details,
                event=event,
                event_date=event_date,
                reported_name=str(data.get("reported_name", ""))[:60],
                contact_email=contact_email[:254],
            )
        except SafetyError as exc:
            return Response({"detail": exc.message, "code": exc.code}, status=exc.status)
        return Response({"ok": True}, status=status.HTTP_201_CREATED)
