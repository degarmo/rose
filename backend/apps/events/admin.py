import csv

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import RSVP, AttendeeExport, Event
from .recurrence import repeat_weekly

CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value):
    """Stop spreadsheet apps treating a display name as a formula."""
    text = str(value)
    return f"'{text}" if text.startswith(CSV_FORMULA_PREFIXES) else text


class RepeatWeeklyForm(forms.Form):
    weeks = forms.IntegerField(
        min_value=1, max_value=26, initial=4, help_text="How many weeks forward to create."
    )


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "starts_at",
        "category",
        "audience",
        "is_published",
        "going",
        "door_list_link",
    )
    list_filter = ("is_published", "category", "audience", "starts_at")
    search_fields = ("title", "summary")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "starts_at"
    autocomplete_fields = ("opportunity",)
    readonly_fields = ("final_going_count", "final_checked_in_count", "rsvps_purged_at")
    actions = ["repeat_weekly_action"]
    fieldsets = (
        (None, {"fields": ("title", "slug", "summary", "body", "category")}),
        ("When and where", {"fields": ("starts_at", "ends_at", "location_label")}),
        (
            "RSVP",
            {
                "fields": (
                    "audience",
                    "capacity",
                    "waitlist_enabled",
                    "max_party_size",
                    "rsvp_opens_at",
                    "rsvp_closes_at",
                    "show_attendee_count",
                )
            },
        ),
        ("Linked class", {"fields": ("opportunity",)}),
        (
            "Image",
            {
                "fields": (
                    "hero_image",
                    "hero_image_alt",
                    "hero_image_faces_visible",
                    "hero_image_consent_confirmed",
                )
            },
        ),
        ("Publishing", {"fields": ("is_published",)}),
        (
            "After the event",
            {
                "classes": ("collapse",),
                "fields": ("final_going_count", "final_checked_in_count", "rsvps_purged_at"),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).with_going_total()

    @admin.display(description="Going", ordering="going_total")
    def going(self, obj):
        if obj.rsvps_purged_at:
            return obj.final_going_count
        capacity = f" / {obj.capacity}" if obj.capacity else ""
        return f"{obj.going_total}{capacity}"

    @admin.display(description="Door list")
    def door_list_link(self, obj):
        url = reverse("admin:events_event_door", args=[obj.pk])
        return format_html('<a href="{}">Door list</a>', url)

    @admin.action(description="Repeat weekly")
    def repeat_weekly_action(self, request, queryset):
        if "apply" in request.POST:
            form = RepeatWeeklyForm(request.POST)
            if form.is_valid():
                weeks = form.cleaned_data["weeks"]
                created_total, skipped_total = 0, []
                for event in queryset:
                    created, skipped = repeat_weekly(event, weeks)
                    created_total += len(created)
                    skipped_total += skipped
                self.message_user(
                    request, f"Created {created_total} event(s). RSVPs were not copied."
                )
                if skipped_total:
                    self.message_user(
                        request,
                        f"Skipped {len(skipped_total)} that already exist: "
                        + ", ".join(skipped_total),
                        level=messages.WARNING,
                    )
                return None
        else:
            form = RepeatWeeklyForm()
        context = {
            **self.admin_site.each_context(request),
            "title": "Repeat weekly",
            "events": queryset,
            "form": form,
            "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
            "opts": self.model._meta,
        }
        return TemplateResponse(request, "admin/events/repeat_weekly.html", context)

    def get_urls(self):
        extra = [
            path(
                "<int:event_id>/door/",
                self.admin_site.admin_view(self.door_list_view),
                name="events_event_door",
            ),
            path(
                "<int:event_id>/door/export/",
                self.admin_site.admin_view(self.door_export_view),
                name="events_event_door_export",
            ),
        ]
        return extra + super().get_urls()

    def _door_rsvps(self, event):
        return (
            event.rsvps.filter(status=RSVP.Status.GOING)
            .select_related("user")
            .order_by("user__display_name")
        )

    def door_list_view(self, request, event_id):
        if not request.user.has_perm("events.view_rsvp"):
            raise PermissionDenied
        event = get_object_or_404(Event, pk=event_id)
        if request.method == "POST":
            if not request.user.has_perm("events.change_rsvp"):
                raise PermissionDenied
            rsvp = get_object_or_404(RSVP, pk=request.POST.get("rsvp"), event=event)
            rsvp.checked_in = request.POST.get("checked_in") == "1"
            rsvp.save(update_fields=["checked_in", "updated_at"])
            return HttpResponseRedirect(f"{request.path}#rsvp-{rsvp.pk}")
        rsvps = self._door_rsvps(event)
        context = {
            **self.admin_site.each_context(request),
            "title": f"Door list: {event}",
            "event": event,
            "rsvps": rsvps,
            "going_total": sum(r.party_size for r in rsvps),
            "checked_in_total": sum(r.party_size for r in rsvps if r.checked_in),
            "waitlist_count": event.rsvps.filter(status=RSVP.Status.WAITLIST).count(),
            "can_change": request.user.has_perm("events.change_rsvp"),
            "can_export": request.user.has_perm("events.export_attendees"),
            "opts": self.model._meta,
        }
        return TemplateResponse(request, "admin/events/door_list.html", context)

    def door_export_view(self, request, event_id):
        if not request.user.has_perm("events.export_attendees"):
            raise PermissionDenied
        event = get_object_or_404(Event, pk=event_id)
        rsvps = list(self._door_rsvps(event))
        AttendeeExport.objects.create(
            event=event,
            event_label=str(event),
            exported_by=request.user,
            exported_by_label=request.user.display_name,
            row_count=len(rsvps),
        )
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        stamp = timezone.localtime(event.starts_at).strftime("%Y-%m-%d")
        response["Content-Disposition"] = f'attachment; filename="door-list-{stamp}.csv"'
        response["Cache-Control"] = "private, no-store"
        writer = csv.writer(response)
        writer.writerow(["Display name", "Party size", "Checked in", "Note to hosts"])
        for rsvp in rsvps:
            writer.writerow(
                [
                    csv_safe(rsvp.user.display_name),
                    rsvp.party_size,
                    "yes" if rsvp.checked_in else "no",
                    csv_safe(rsvp.note_to_hosts),
                ]
            )
        return response


@admin.register(RSVP)
class RSVPAdmin(admin.ModelAdmin):
    list_display = ("event", "attendee", "status", "party_size", "checked_in", "created_at")
    list_filter = ("status", "checked_in", "event")
    search_fields = ("user__display_name", "event__title")
    list_select_related = ("event", "user")
    readonly_fields = (
        "event",
        "user",
        "created_at",
        "updated_at",
        "waitlisted_at",
        "reminder_sent_at",
    )
    fields = (
        "event",
        "user",
        "status",
        "party_size",
        "note_to_hosts",
        "checked_in",
        "waitlisted_at",
        "reminder_sent_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    @admin.display(description="Attendee", ordering="user__display_name")
    def attendee(self, obj):
        return obj.user.display_name


@admin.register(AttendeeExport)
class AttendeeExportAdmin(admin.ModelAdmin):
    list_display = ("event_label", "exported_by_label", "exported_at", "row_count")
    readonly_fields = ("event_label", "exported_by_label", "exported_at", "row_count")
    fields = readonly_fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
