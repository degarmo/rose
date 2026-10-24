import calendar
import csv
from datetime import timedelta

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import action, display
from unfold.widgets import UnfoldBooleanWidget

from apps.core.admin_display import chip, image_preview
from apps.core.admin_widgets import RichTextWidget
from apps.core.models import AuditLog, audit
from apps.core.samples import SampleBadgeAdmin, with_sample_flag
from apps.memberships import usage
from apps.safety import roles

from .models import RSVP, AttendeeExport, Event, EventTag, PastEvent
from .recurrence import duplicate, repeat_weekly

CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value):
    """Stop spreadsheet apps treating a display name as a formula."""
    text = str(value)
    return f"'{text}" if text.startswith(CSV_FORMULA_PREFIXES) else text


class RepeatWeeklyForm(forms.Form):
    weeks = forms.IntegerField(
        min_value=1, max_value=26, initial=4, help_text="How many weeks forward to create."
    )


EVENT_FIELDSETS = (
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
            "fields": ("is_published", "is_featured", "take_feature", "is_private_hold"),
            "description": "Unpublished events are drafts; nobody outside the admin sees them. "
            "One event at a time can be featured at the top of the Events page and Home.",
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
EVENT_READONLY = (
    "hero_image_preview",
    "final_going_count",
    "final_checked_in_count",
    "rsvps_purged_at",
    "is_private_hold",
)


class EventAdminForm(forms.ModelForm):
    """Featuring an event takes the feature from the one featured now, so it asks first,
    naming that event."""

    take_feature = forms.BooleanField(
        required=False,
        label="Yes, take the feature from the event featured now",
        widget=UnfoldBooleanWidget,
    )

    class Meta:
        model = Event
        # The admin adds the rest of the fieldsets' fields.
        fields = ("is_featured",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current = Event.objects.featured().exclude(pk=self.instance.pk).first()
        self.fields["take_feature"].help_text = (
            f"Featured now: {self.current}." if self.current else "No other event is featured now."
        )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("is_featured") and self.current and not cleaned.get("take_feature"):
            self.add_error(
                "is_featured",
                f"{self.current} is featured now. Featuring this event takes the feature from "
                "it: tick “Yes, take the feature from the event featured now” to confirm.",
            )
        return cleaned


MISSING_ALT = (
    "This event's picture has no alt text. Describe what it shows (Image tab), so people "
    "using screen readers know; until then the site uses the event's title."
)


def warn_missing_alt(model_admin, request, object_id):
    """Pictures saved before alt text was required may still lack it."""
    event = Event.objects.filter(pk=object_id).only("hero_image", "hero_image_alt").first()
    if event is not None and event.hero_image and not event.hero_image_alt.strip():
        model_admin.message_user(request, MISSING_ALT, messages.WARNING)


def _is_main_list(request):
    match = request.resolver_match
    return bool(match and match.url_name == "events_event_changelist")


@admin.register(Event)
class EventAdmin(SampleBadgeAdmin, ModelAdmin):
    """Events still to come or happening now, soonest first. Once over, an event moves to
    Past events (PastEventAdmin) on its own, and back if its dates move ahead."""

    form = EventAdminForm
    hero_image_preview = image_preview("hero_image")
    list_display = (
        "title",
        "starts_at",
        "category",
        "audience_chip",
        "state",
        "featured",
        "going",
        "door_list_link",
    )
    list_filter = ("is_published", "is_private_hold", "category", "audience", "starts_at")
    search_fields = ("title", "summary")
    ordering = ("starts_at", "title")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "starts_at"
    autocomplete_fields = ("opportunity",)
    filter_horizontal = ("access_tags",)
    readonly_fields = EVENT_READONLY
    actions = ["repeat_weekly_action"]
    list_before_template = "admin/events/archive_link.html"
    # A long page: one tab per part.
    fieldsets = EVENT_FIELDSETS

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
        label={
            "Upcoming": "success",
            "Happening now": "primary",
            "Draft": "warning",
            "Private hold": "info",
            "Past": "info",
        },
    )
    def state(self, obj):
        if obj.is_private_hold:
            return "Private hold"
        if not obj.is_published:
            return "Draft"
        return obj.timing.label

    @display(description="Featured", boolean=True, ordering="is_featured")
    def featured(self, obj):
        return obj.is_featured

    def get_queryset(self, request):
        events = super().get_queryset(request).with_going_total()
        return events.not_past() if _is_main_list(request) else events

    def changelist_view(self, request, extra_context=None):
        extra_context = {
            **(extra_context or {}),
            "past_count": Event.objects.past().count(),
            "archive_url": reverse("admin:events_pastevent_changelist"),
        }
        return super().changelist_view(request, extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        """A past event opens in the archive, read-only unless edited anyway."""
        event = Event.objects.filter(pk=object_id).first()
        if event is not None and event.is_past:
            url = reverse("admin:events_pastevent_change", args=(event.pk,))
            return redirect(f"{url}?{request.GET.urlencode()}" if request.GET else url)
        if request.method == "GET":
            warn_missing_alt(self, request, object_id)
        return super().change_view(request, object_id, form_url, extra_context)

    @admin.display(description="Going", ordering="going_total")
    def going(self, obj):
        """The same figure as the RSVP counts page (apps.core.metrics), small ones withheld."""
        from apps.core import metrics

        going = metrics.count(obj.final_going_count if obj.rsvps_purged_at else obj.going_total)
        capacity = f" / {obj.capacity}" if obj.capacity else ""
        return f"{going['display']}{capacity}"

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
        """RSVPs as numbers per event (upcoming first, then the last month), from
        apps.core.metrics like every other number; no names."""
        from apps.core import metrics

        if not request.user.has_perm("events.view_rsvp"):
            raise PermissionDenied
        since = timezone.now() - timedelta(days=30)
        events = Event.objects.filter(starts_at__gte=since, is_private_hold=False).order_by(
            "starts_at"
        )
        context = {
            **self.admin_site.each_context(request),
            "title": "RSVPs",
            "opts": RSVP._meta,
            "rows": metrics.event_counts(events),
            "small": metrics.SMALL,
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


class YearFilter(admin.SimpleListFilter):
    title = "year"
    parameter_name = "year"

    def lookups(self, request, model_admin):
        years = Event.objects.past().dates("starts_at", "year", order="DESC")
        return [(str(day.year), str(day.year)) for day in years]

    def queryset(self, request, queryset):
        return queryset.filter(starts_at__year=self.value()) if self.value() else queryset


class MonthFilter(admin.SimpleListFilter):
    title = "month"
    parameter_name = "month"

    def lookups(self, request, model_admin):
        return [(str(number), name) for number, name in enumerate(calendar.month_name) if number]

    def queryset(self, request, queryset):
        return queryset.filter(starts_at__month=self.value()) if self.value() else queryset


class TagFilter(admin.RelatedFieldListFilter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "tags"


class DuplicateForm(forms.Form):
    """A new start for each event being duplicated."""

    def __init__(self, events, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.events = list(events)
        for event in self.events:
            self.fields[f"start_{event.pk}"] = forms.DateTimeField(
                label=str(event),
                help_text="Chicago time. The end and the RSVP window move with it.",
                widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
            )

    def clean(self):
        cleaned = super().clean()
        for event in self.events:
            start = cleaned.get(f"start_{event.pk}")
            if start is not None and start <= timezone.now():
                self.add_error(f"start_{event.pk}", "Choose a time in the future.")
        return cleaned

    def starts(self):
        return [(event, self.cleaned_data[f"start_{event.pk}"]) for event in self.events]


@admin.register(PastEvent)
class PastEventAdmin(SampleBadgeAdmin, ModelAdmin):
    """Past events: the archive, newest first. Read-only unless someone presses "Edit
    anyway", which is logged; editing the dates into the future moves an event back to the
    main list. Only admins may delete."""

    form = EventAdminForm
    hero_image_preview = image_preview("hero_image")
    list_display = ("title", "date", "category", "going", "checked_in", "published")
    list_display_links = ("title",)
    list_filter = (
        YearFilter,
        MonthFilter,
        "category",
        ("access_tags", TagFilter),
    )
    search_fields = ("title",)
    ordering = ("-starts_at", "title")
    fieldsets = EVENT_FIELDSETS
    readonly_fields = EVENT_READONLY
    filter_horizontal = ("access_tags",)
    autocomplete_fields = ("opportunity",)
    actions = ["duplicate_action", "unpublish_action"]
    actions_detail = ["edit_anyway"]
    change_form_before_template = "admin/events/past_notice.html"

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "body":
            kwargs["widget"] = RichTextWidget
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def get_queryset(self, request):
        from apps.core import metrics

        return with_sample_flag(metrics.with_event_counts(PastEvent.objects.all()))

    # Who may do what: the same as for events, but read-only until "Edit anyway".

    def has_module_permission(self, request):
        return request.user.has_perm("events.view_event")

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("events.view_event")

    def has_add_permission(self, request):
        return False

    def _editing(self, request):
        return request.GET.get("edit") == "1"

    def has_change_permission(self, request, obj=None):
        allowed = request.user.has_perm("events.change_event")
        return allowed if obj is None else allowed and self._editing(request)

    def has_delete_permission(self, request, obj=None):
        return roles.has_role(request.user, roles.ADMIN)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        if request.method == "GET":
            warn_missing_alt(self, request, object_id)
        return super().change_view(request, object_id, form_url, extra_context)

    def has_edit_anyway_permission(self, request, object_id=None):
        return request.user.has_perm("events.change_event") and not self._editing(request)

    @action(description="Edit anyway", url_path="edit-anyway", permissions=["edit_anyway"])
    def edit_anyway(self, request, object_id):
        url = reverse("admin:events_pastevent_change", args=(object_id,))
        return redirect(f"{url}?edit=1")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        audit(
            AuditLog.Category.CONTENT,
            "edit_past_event",
            request.user,
            f"Event {obj.title}"[:120],
            "event",
            target_ref=obj.slug,
            reason="Changed: " + (", ".join(form.changed_data) or "nothing"),
        )

    # Columns

    @display(description="Date", ordering="starts_at")
    def date(self, obj):
        return timezone.localtime(obj.starts_at).strftime("%b %-d, %Y")

    def _figure(self, obj, name):
        from apps.core import metrics

        return render_to_string(
            "admin/rose/metric.html", {"metric": metrics.event_figures(obj)[name]}
        )

    @display(description="Published", boolean=True, ordering="is_published")
    def published(self, obj):
        return obj.is_published

    @display(description="Going")
    def going(self, obj):
        return self._figure(obj, "going")

    @display(description="Checked in")
    def checked_in(self, obj):
        return self._figure(obj, "checked_in")

    # Actions

    @admin.action(description="Duplicate as new event")
    def duplicate_action(self, request, queryset):
        events = queryset.order_by("starts_at")
        if not request.user.has_perm("events.add_event"):
            raise PermissionDenied
        form = DuplicateForm(events, request.POST if "apply" in request.POST else None)
        if form.is_bound and form.is_valid():
            drafts = [duplicate(event, start) for event, start in form.starts()]
            for draft in drafts:
                audit(
                    AuditLog.Category.CONTENT,
                    "duplicate_event",
                    request.user,
                    f"Event {draft.title}"[:120],
                    "event",
                    target_ref=draft.slug,
                )
            self.message_user(
                request,
                f"Created {len(drafts)} draft{'s' if len(drafts) != 1 else ''}, unpublished and "
                "with no RSVPs: " + ", ".join(str(draft) for draft in drafts) + ".",
            )
            if len(drafts) == 1:
                return redirect(reverse("admin:events_event_change", args=(drafts[0].pk,)))
            return redirect(reverse("admin:events_event_changelist"))
        context = {
            **self.admin_site.each_context(request),
            "title": "Duplicate as new event",
            "opts": self.model._meta,
            "form": form,
            "events": events,
            "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
        }
        return TemplateResponse(request, "admin/events/duplicate.html", context)

    @admin.action(description="Unpublish")
    def unpublish_action(self, request, queryset):
        if not request.user.has_perm("events.change_event"):
            raise PermissionDenied
        events = list(queryset.filter(is_published=True))
        for event in events:
            event.is_published = False
            event.save(update_fields=["is_published", "updated_at"])
            audit(
                AuditLog.Category.CONTENT,
                "unpublish_event",
                request.user,
                f"Event {event.title}"[:120],
                "event",
                target_ref=event.slug,
            )
        self.message_user(request, f"Unpublished {len(events)} event(s).")


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
