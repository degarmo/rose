import csv
from datetime import timedelta

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display

from apps.core.admin_display import chip, image_preview
from apps.core.admin_widgets import RichTextWidget
from apps.memberships import usage

from .models import RSVP, AttendeeExport, Event, EventTag
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
class EventAdmin(ModelAdmin):
    hero_image_preview = image_preview("hero_image")
    list_display = (
        "title",
        "starts_at",
        "category",
        "audience_chip",
        "state",
        "going",
        "door_list_link",
    )
    list_filter = ("is_published", "is_private_hold", "category", "audience", "starts_at")
    search_fields = ("title", "summary")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "starts_at"
    autocomplete_fields = ("opportunity",)
    filter_horizontal = ("access_tags",)
    readonly_fields = (
        "hero_image_preview",
        "final_going_count",
        "final_checked_in_count",
        "rsvps_purged_at",
        "is_private_hold",
    )
    actions = ["repeat_weekly_action"]
    # A long page: one tab per part.
    fieldsets = (
        (
            "Details",
            {
                "classes": ["tab"],
                "fields": ("title", "slug", "summary", "body", "category"),
                "description": "The summary shows on event cards; the body on the event page.",
            },
        ),
        (
            "When and where",
            {
                "classes": ["tab"],
                "fields": ("starts_at", "ends_at", "location_label"),
                "description": "Times are Chicago time. Leave the place general if it is private.",
            },
        ),
        (
            "RSVP",
            {
                "classes": ["tab"],
                "description": "Who may RSVP, how many, and when. Members-only events can be "
                "limited to tiers by tag.",
                "fields": (
                    "audience",
                    "access_tags",
                    "capacity",
                    "waitlist_enabled",
                    "max_party_size",
                    "guest_allowance",
                    "rsvp_opens_at",
                    "rsvp_closes_at",
                    "show_attendee_count",
                ),
            },
        ),
        ("Linked class", {"classes": ["tab"], "fields": ("opportunity",)}),
        (
            "Image",
            {
                "classes": ["tab"],
                "description": "Images that may show a person stay hidden until faces and "
                "consent are confirmed.",
                "fields": (
                    "hero_image_preview",
                    "hero_image",
                    "hero_image_alt",
                    "hero_image_faces_visible",
                    "hero_image_consent_confirmed",
                ),
            },
        ),
        (
            "Publishing",
            {
                "classes": ["tab"],
                "fields": ("is_published", "is_private_hold"),
                "description": "Unpublished events are drafts; nobody outside the admin sees them.",
            },
        ),
        (
            "After the event",
            {
                "classes": ["tab"],
                "fields": ("final_going_count", "final_checked_in_count", "rsvps_purged_at"),
                "description": "RSVPs are deleted after the event; only these totals are kept.",
            },
        ),
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "body":
            kwargs["widget"] = RichTextWidget
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    @display(
        description="Audience",
        label={"Members only": "primary", "Signed-in accounts only": "info", "Everyone": "success"},
    )
    def audience_chip(self, obj):
        return {"members": "Members only", "account": "Signed-in accounts only"}.get(
            obj.audience, "Everyone"
        )

    @display(
        description="Status",
        label={"Published": "success", "Draft": "warning", "Private hold": "info"},
    )
    def state(self, obj):
        if obj.is_private_hold:
            return "Private hold"
        if not obj.is_published:
            return "Draft"
        return "Past" if obj.ends_at < timezone.now() else "Published"

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
        return format_html('<a class="rose-link" href="{}">Door list</a>', url)

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
                "rsvp-counts/",
                self.admin_site.admin_view(self.rsvp_counts_view),
                name="events_rsvp_counts",
            ),
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

    def rsvp_counts_view(self, request):
        """RSVPs as numbers per event (upcoming first, then the last month); no names."""
        if not request.user.has_perm("events.view_rsvp"):
            raise PermissionDenied
        since = timezone.now() - timedelta(days=30)
        events = (
            Event.objects.filter(starts_at__gte=since, is_private_hold=False)
            .annotate(
                going=Coalesce(
                    Sum("rsvps__party_size", filter=Q(rsvps__status=RSVP.Status.GOING)), 0
                ),
                waiting=Count("rsvps", filter=Q(rsvps__status=RSVP.Status.WAITLIST)),
                checked=Coalesce(Sum("rsvps__party_size", filter=Q(rsvps__checked_in=True)), 0),
            )
            .order_by("starts_at")
        )
        context = {
            **self.admin_site.each_context(request),
            "title": "RSVPs",
            "opts": RSVP._meta,
            "events": events,
            "now": timezone.now(),
        }
        return TemplateResponse(request, "admin/events/rsvp_counts.html", context)

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


@admin.register(EventTag)
class EventTagAdmin(ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(RSVP)
class RSVPAdmin(ModelAdmin):
    list_display = ("event", "attendee", "status_chip", "party_size", "checked_in", "created_at")
    status_chip = chip("status", {"Going": "success", "Waitlist": "warning"})
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

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # A status changed by hand still keeps the member's monthly count right.
        usage.sync(obj)

    @admin.display(description="Attendee", ordering="user__display_name")
    def attendee(self, obj):
        return obj.user.display_name


@admin.register(AttendeeExport)
class AttendeeExportAdmin(ModelAdmin):
    list_display = ("event_label", "exported_by_label", "exported_at", "row_count")
    readonly_fields = ("event_label", "exported_by_label", "exported_at", "row_count")
    fields = readonly_fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
