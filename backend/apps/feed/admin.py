from collections import defaultdict

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from apps.accounts.models import Profile, User
from apps.core.admin_display import chip, flag
from apps.core.models import AuditLog
from apps.core.private_media import private_media
from apps.memberships.access import age_gate_passes

from . import services
from .models import (
    Announcement,
    FeedComment,
    FeedImage,
    FeedPost,
    Guidelines,
    ModerationActionType,
    Notification,
    Report,
)

QUEUE_PERMISSION = "feed.change_feedpost"


@admin.register(Guidelines)
class GuidelinesAdmin(ModelAdmin):
    list_display = ("version", "title", "published_at", "created_at")
    actions = ["publish"]
    fields = ("title", "body", "version", "published_at")
    readonly_fields = ("version", "published_at")

    def get_readonly_fields(self, request, obj=None):
        # A published version is a record of what people agreed to, so it never changes.
        if obj is not None and obj.published_at is not None:
            return ("title", "body", "version", "published_at")
        return self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        return obj is None or obj.published_at is None

    @admin.action(description="Publish (members must accept again before posting)")
    def publish(self, request, queryset):
        drafts = list(queryset.filter(published_at__isnull=True).order_by("version"))
        for draft in drafts:
            draft.published_at = timezone.now()
            draft.save(update_fields=["published_at"])
        if drafts:
            participants = User.objects.filter(profile__participates_in_feed=True)
            Notification.objects.bulk_create(
                Notification(
                    recipient=user,
                    kind=Notification.Kind.GUIDELINES,
                    message="The community guidelines have been updated. Please read and "
                    "accept them before your next post.",
                )
                for user in participants
            )
            self.message_user(request, f"Published version {drafts[-1].version}.")


class ModerationForm(forms.Form):
    target_type = forms.ChoiceField(
        choices=[("post", "Post"), ("comment", "Comment"), ("profile", "Profile"), ("user", "User")]
    )
    target_ref = forms.CharField(max_length=40)
    action = forms.ChoiceField(choices=ModerationActionType.choices)
    reason = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    days = forms.IntegerField(required=False, min_value=1, max_value=365)
    confirm = forms.CharField(required=False)


def resolve_target(target_type, ref):
    if target_type == "post":
        return get_object_or_404(FeedPost.objects.select_related("author"), public_id=ref)
    if target_type == "comment":
        return get_object_or_404(FeedComment.objects.select_related("author"), public_id=ref)
    return get_object_or_404(User.objects.select_related("profile"), display_name=ref)


@admin.register(FeedPost)
class FeedPostAdmin(ModelAdmin):
    """Posts are reviewed in the moderation queue; this list is for finding them."""

    list_display = ("public_id", "author", "status_chip", "created_at", "queue_link")
    status_chip = chip(
        "status",
        {
            "Pending review": "warning",
            "Published": "success",
            "Hidden by report": "danger",
            "Removed": "danger",
        },
    )
    list_filter = ("status", "is_sensitive")
    search_fields = ("public_id", "author__display_name")
    fields = (
        "public_id",
        "author",
        "status",
        "caption",
        "is_sensitive",
        "comments_enabled",
        "consent_attested_at",
        "created_at",
        "edited_at",
        "removed_reason",
    )
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Moderation")
    def queue_link(self, obj):
        return format_html('<a href="{}">Open queue</a>', reverse("admin:feed_moderation"))

    def get_urls(self):
        extra = [
            path(
                "moderation/", self.admin_site.admin_view(self.queue_view), name="feed_moderation"
            ),
            path(
                "moderation/image/<str:public_id>/",
                self.admin_site.admin_view(self.image_view),
                name="feed_moderation_image",
            ),
            path(
                "moderation/avatar/<str:key>/",
                self.admin_site.admin_view(self.avatar_view),
                name="feed_moderation_avatar",
            ),
        ]
        return extra + super().get_urls()

    def _require(self, request):
        if not request.user.has_perm(QUEUE_PERMISSION):
            raise PermissionDenied

    def queue_view(self, request):
        self._require(request)
        form = ModerationForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            data = form.cleaned_data
            target = resolve_target(data["target_type"], data["target_ref"])
            try:
                if data["action"] == ModerationActionType.ERASE:
                    member = target if isinstance(target, User) else target.author
                    services.staff_erase(request.user, member, data["confirm"])
                else:
                    services.moderate(
                        request.user,
                        data["action"],
                        data["target_type"],
                        target,
                        reason=data["reason"],
                        days=data["days"],
                    )
                self.message_user(request, "Done. The action has been logged.")
            except services.FeedError as exc:
                self.message_user(request, exc.message, level=messages.ERROR)
            return HttpResponseRedirect(request.path)

        groups = defaultdict(list)
        # Concerns about events have no feed item; they are handled in the staff inbox.
        open_reports = Report.objects.filter(resolved_at__isnull=True).exclude(
            target_type=Report.TargetType.EVENT
        )
        for report in open_reports.select_related(
            "post__author", "comment__author", "profile_user__profile", "reporter"
        ):
            key = (
                report.target_type,
                report.post_id or report.comment_id or report.profile_user_id,
            )
            groups[key].append(report)
        age_checked = age_gate_passes(request.user)
        report_groups = []
        for (target_type, _), reports in groups.items():
            target = reports[0].target
            report_groups.append(
                {
                    "target_type": target_type,
                    "target": target,
                    "ref": getattr(target, "public_id", None) or target.display_name,
                    "reports": reports,
                    "reasons": sorted({r.get_reason_display() for r in reports}),
                    "reporter_count": len({r.reporter_id for r in reports}),
                    "hidden": self._is_hidden(target_type, target),
                    "under_18": any(r.reason == Report.Reason.UNDER_18 for r in reports),
                    "images": self._images(target_type, target) if age_checked else [],
                }
            )
        # Possibly under 18 first, then whatever is hidden, then the most reported.
        report_groups.sort(key=lambda g: (not g["under_18"], not g["hidden"], -g["reporter_count"]))

        pending = (
            FeedPost.objects.filter(status=FeedPost.Status.PENDING, is_processing=False)
            .select_related("author")
            .prefetch_related("images")
            .order_by("created_at")
        )
        context = {
            **self.admin_site.each_context(request),
            "title": "Feed moderation",
            "opts": self.model._meta,
            "pending": pending,
            "report_groups": report_groups,
            "age_checked": age_checked,
            "actions_log": AuditLog.objects.filter(category=AuditLog.Category.MODERATION)[:50],
            "action_labels": dict(ModerationActionType.choices),
        }
        return TemplateResponse(request, "admin/feed/moderation.html", context)

    @staticmethod
    def _is_hidden(target_type, target):
        if target_type == "post":
            return target.status == FeedPost.Status.HIDDEN_BY_REPORT
        if target_type == "comment":
            return target.status == FeedComment.Status.HIDDEN_BY_REPORT
        return target.profile.hidden_by_report

    @staticmethod
    def _images(target_type, target):
        if target_type == "post":
            return [
                reverse("admin:feed_moderation_image", args=[image.public_id])
                for image in target.images.exclude(image="")
            ]
        if target_type == "profile" and target.profile.avatar_key:
            return [reverse("admin:feed_moderation_avatar", args=[target.profile.avatar_key])]
        return []

    def _require_age_check(self, request):
        """Member pictures, here too, only for staff the member feed's age gate lets through."""
        self._require(request)
        if not age_gate_passes(request.user):
            raise Http404

    def image_view(self, request, public_id):
        self._require_age_check(request)
        image = FeedImage.objects.filter(public_id=public_id).exclude(image="").first()
        if image is None:
            raise Http404
        return private_media().deliver(request, image.image.name)

    def avatar_view(self, request, key):
        self._require_age_check(request)
        profile = Profile.objects.filter(avatar_key=key).exclude(avatar="").first()
        if profile is None or not key:
            raise Http404
        return private_media().deliver(request, profile.avatar.name)


@admin.register(Report)
class ReportAdmin(ModelAdmin):
    """Read-only. Decisions are made in the moderation queue so they get logged."""

    list_display = ("created_at", "target_type", "reason", "resolved_at", "resolution")
    list_filter = ("reason", "target_type", "resolved_at")
    fields = ("created_at", "target_type", "reason", "details", "resolved_at", "resolution")
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Announcement)
class AnnouncementAdmin(ModelAdmin):
    """Short notices shown as a "News" story in the member app between start and end."""

    list_display = ["title", "starts_at", "ends_at", "is_published_chip"]
    is_published_chip = flag("is_published", "Published", "Draft", "Status")
    list_filter = ["is_published"]
    search_fields = ["title"]
    fields = ["title", "body", "link_label", "link_url", "starts_at", "ends_at", "is_published"]
