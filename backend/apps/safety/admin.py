"""Read-only views of moderation decisions and appeals in the admin.

Decisions are taken, reversed and appealed in the staff section (/members/staff), where
the rules for who may act live (apps.safety.services). Here they are a record to look up:
nothing can be added, changed or deleted, and the reporter is never shown.
"""

from django.conf import settings
from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import Appeal, MemberAction


class RecordAdmin(ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


def _staff_link(path, label):
    return format_html('<a href="{}{}">{}</a>', settings.SITE_URL, path, label)


@admin.register(MemberAction)
class MemberActionAdmin(RecordAdmin):
    """The moderation log: every decision about a member, newest first."""

    list_display = ("member", "decision", "rule", "created_at", "state", "created_by")
    list_filter = ("kind", ("reversed_at", admin.EmptyFieldListFilter), "created_at")
    search_fields = ("member__display_name", "rule")
    date_hierarchy = "created_at"
    list_select_related = ("member", "created_by")
    fields = (
        "member",
        "kind",
        "rule",
        "reason",
        "ends_at",
        "created_by",
        "created_at",
        "reversed_at",
        "reversed_by",
        "reversal_reason",
        "open_in_staff",
    )
    readonly_fields = fields

    @display(
        description="Decision",
        label={
            "Warning": "warning",
            "Remove content": "warning",
            "Feed suspension": "danger",
            "Event suspension": "danger",
            "Ban": "danger",
        },
    )
    def decision(self, obj):
        return obj.get_kind_display()

    @display(
        description="State", label={"In force": "danger", "Reversed": "success", "Ended": "info"}
    )
    def state(self, obj):
        if obj.reversed_at:
            return "Reversed"
        return "In force" if obj.is_in_force() else "Ended"

    @display(description="Staff section")
    def open_in_staff(self, obj):
        return _staff_link(f"/members/staff/members/{obj.member.display_name}", "Open the member")


@admin.register(Appeal)
class AppealAdmin(RecordAdmin):
    """Appeals against decisions; decided in the staff section by someone else."""

    list_display = (
        "member",
        "decision",
        "appeal_status",
        "assigned_to",
        "created_at",
        "decided_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("action__member__display_name",)
    list_select_related = ("action__member", "assigned_to")
    fields = (
        "decision",
        "member",
        "text",
        "status",
        "assigned_to",
        "decided_by",
        "decided_at",
        "decision_note",
        "created_at",
        "open_in_staff",
    )
    readonly_fields = fields

    @display(description="Member")
    def member(self, obj):
        return obj.action.member

    @display(description="Decision appealed")
    def decision(self, obj):
        return obj.action.get_kind_display()

    @display(
        description="Status",
        ordering="status",
        label={"Open": "warning", "Upheld": "info", "Reversed": "success"},
    )
    def appeal_status(self, obj):
        return obj.get_status_display()

    @display(description="Staff section")
    def open_in_staff(self, obj):
        return _staff_link(f"/members/staff/appeals/{obj.pk}", "Decide in the staff section")
