from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Read-only. Nothing here can be added, edited or deleted."""

    list_display = ("created_at", "category", "action", "target_label", "actor_label", "reason")
    list_filter = ("category", "action", "target_type")
    search_fields = ("target_label", "target_ref", "actor_label", "reason")
    date_hierarchy = "created_at"
    fields = (
        "created_at",
        "category",
        "action",
        "target_type",
        "target_label",
        "target_ref",
        "actor_label",
        "reason",
    )
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
