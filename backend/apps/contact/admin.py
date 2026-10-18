from django.contrib import admin

from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("priority_flag", "topic", "name", "created_at", "handled")
    list_display_links = ("topic", "name")
    list_filter = ("is_priority", "topic", "handled", "created_at")
    search_fields = ("name", "email", "message")
    readonly_fields = (
        "name",
        "email",
        "phone",
        "topic",
        "message",
        "created_at",
        "is_priority",
        "anonymized_at",
    )
    fields = readonly_fields + ("handled",)
    actions = ["mark_handled", "mark_unhandled"]
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    @admin.display(boolean=True, description="Priority", ordering="is_priority")
    def priority_flag(self, obj):
        return obj.is_priority

    @admin.action(description="Mark selected messages as handled")
    def mark_handled(self, request, queryset):
        queryset.update(handled=True)

    @admin.action(description="Mark selected messages as not handled")
    def mark_unhandled(self, request, queryset):
        queryset.update(handled=False)
