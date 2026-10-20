from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from unfold.admin import ModelAdmin
from unfold.decorators import action

from apps.core.admin_display import chip

from . import services
from .models import RentalInquiry

CHANGE_PERMISSION = "rentals.change_rentalinquiry"


def describe_events(events):
    return format_html_join(
        "",
        "<li>{} ({})</li>",
        (
            (
                "Private rental hold" if event.is_private_hold else event.title,
                timezone.localtime(event.starts_at).strftime("%a %b %d, %I:%M %p"),
            )
            for event in events
        ),
    )


class ConfirmForm(forms.Form):
    create_hold = forms.BooleanField(
        required=False,
        initial=True,
        label="Add a private placeholder to the calendar",
        help_text="Holds the time so nobody double-books it. It is never published or shown "
        "on the site.",
    )
    reason = forms.CharField(required=False, max_length=300, label="Note for the log")


@admin.register(RentalInquiry)
class RentalInquiryAdmin(ModelAdmin):
    list_display = (
        "__str__",
        "type",
        "preferred_date",
        "status_chip",
        "conflict",
        "created_at",
    )
    status_chip = chip(
        "status",
        {"New": "warning", "In discussion": "info", "Quoted": "info", "Confirmed": "success"},
    )
    list_filter = ("status", "type")
    date_hierarchy = "preferred_date"
    # The status form sits outside the change form (forms cannot be nested).
    change_form_outer_before_template = "admin/rentals/status_tools.html"
    actions_list = ["open_pipeline"]
    actions_detail = ["confirm_inquiry", "open_pipeline_from_detail"]
    readonly_fields = (
        "conflict_warning",
        "status",
        "user",
        "hold",
        "closed_at",
        "contact_purged_at",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (None, {"fields": ("status", "conflict_warning")}),
        ("Contact", {"fields": ("contact_name", "contact_email", "contact_phone", "user")}),
        (
            "Request",
            {
                "fields": (
                    "type",
                    "preferred_date",
                    "alternate_date",
                    "start_time",
                    "duration_hours",
                    "party_size",
                    "notes",
                    "photoshoot_acknowledged",
                )
            },
        ),
        ("Staff", {"fields": ("quoted_amount_cents", "staff_notes", "hold")}),
        ("Record", {"fields": ("closed_at", "contact_purged_at", "created_at", "updated_at")}),
    )
    actions = ["mark_in_discussion", "mark_quoted", "mark_declined", "mark_cancelled"]

    def has_add_permission(self, request):
        # Inquiries come from the site's form.
        return False

    @admin.display(boolean=True, description="Clash")
    def conflict(self, obj):
        found = services.conflicts(obj)
        return bool(found["preferred"] or found["alternate"])

    @admin.display(description="Calendar")
    def conflict_warning(self, obj):
        if obj.pk is None:
            return "-"
        found = services.conflicts(obj)
        if not (found["preferred"] or found["alternate"]):
            return "Nothing else is on the calendar at the requested times."
        parts = []
        if found["preferred"]:
            parts.append(
                format_html(
                    "<p><strong>First choice overlaps:</strong></p><ul>{}</ul>",
                    describe_events(found["preferred"]),
                )
            )
        if found["alternate"]:
            parts.append(
                format_html(
                    "<p><strong>Second choice overlaps:</strong></p><ul>{}</ul>",
                    describe_events(found["alternate"]),
                )
            )
        return format_html_join("", "{}", ((part,) for part in parts))

    def _bulk(self, request, queryset, status):
        if not request.user.has_perm(CHANGE_PERMISSION):
            raise PermissionDenied
        changed = 0
        for inquiry in queryset:
            try:
                services.change_status(request.user, inquiry, status)
                changed += 1
            except services.RentalError as exc:
                self.message_user(request, f"{inquiry.label}: {exc}", level=messages.ERROR)
        self.message_user(request, f"{changed} updated.")

    @admin.action(description="Mark in discussion", permissions=["change"])
    def mark_in_discussion(self, request, queryset):
        self._bulk(request, queryset, RentalInquiry.Status.IN_DISCUSSION)

    @admin.action(description="Mark quoted", permissions=["change"])
    def mark_quoted(self, request, queryset):
        self._bulk(request, queryset, RentalInquiry.Status.QUOTED)

    @admin.action(description="Mark declined", permissions=["change"])
    def mark_declined(self, request, queryset):
        self._bulk(request, queryset, RentalInquiry.Status.DECLINED)

    @admin.action(description="Mark cancelled", permissions=["change"])
    def mark_cancelled(self, request, queryset):
        self._bulk(request, queryset, RentalInquiry.Status.CANCELLED)

    @action(description="Pipeline view", icon="view_kanban", url_path="pipeline-view")
    def open_pipeline(self, request):
        return HttpResponseRedirect(reverse("admin:rentals_pipeline"))

    @action(description="Pipeline view", icon="view_kanban", url_path="pipeline-view-from-inquiry")
    def open_pipeline_from_detail(self, request, object_id):
        return HttpResponseRedirect(reverse("admin:rentals_pipeline"))

    @action(description="Mark confirmed", icon="event_available", permissions=["change"])
    def confirm_inquiry(self, request, object_id):
        return HttpResponseRedirect(reverse("admin:rentals_confirm", args=[object_id]))

    def get_urls(self):
        extra = [
            path(
                "pipeline/",
                self.admin_site.admin_view(self.pipeline_view),
                name="rentals_pipeline",
            ),
            path(
                "<int:pk>/confirm/",
                self.admin_site.admin_view(self.confirm_view),
                name="rentals_confirm",
            ),
            path(
                "<int:pk>/status/",
                self.admin_site.admin_view(self.status_view),
                name="rentals_status",
            ),
        ]
        return extra + super().get_urls()

    def pipeline_view(self, request):
        """Every open inquiry, grouped by status, with clashes flagged."""
        if not request.user.has_perm("rentals.view_rentalinquiry"):
            raise PermissionDenied
        columns = []
        inquiries = RentalInquiry.objects.select_related("hold").order_by("preferred_date")
        for status in RentalInquiry.PIPELINE:
            rows = []
            for inquiry in inquiries.filter(status=status, contact_purged_at__isnull=True):
                found = services.conflicts(inquiry)
                rows.append(
                    {
                        "inquiry": inquiry,
                        "conflicts": found["preferred"] + found["alternate"],
                        "url": reverse("admin:rentals_rentalinquiry_change", args=[inquiry.pk]),
                    }
                )
            columns.append({"label": RentalInquiry.Status(status).label, "rows": rows})
        context = {
            **self.admin_site.each_context(request),
            "title": "Rental pipeline",
            "opts": self.model._meta,
            "columns": columns,
        }
        return TemplateResponse(request, "admin/rentals/pipeline.html", context)

    def status_view(self, request, pk):
        """POST only: move one inquiry along the pipeline (confirming has its own page)."""
        if request.method != "POST" or not request.user.has_perm(CHANGE_PERMISSION):
            raise PermissionDenied
        inquiry = get_object_or_404(RentalInquiry, pk=pk)
        status = request.POST.get("status", "")
        if status == RentalInquiry.Status.CONFIRMED:
            return HttpResponseRedirect(reverse("admin:rentals_confirm", args=[inquiry.pk]))
        try:
            services.change_status(
                request.user, inquiry, status, request.POST.get("reason", "")[:300]
            )
        except services.RentalError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
        else:
            self.message_user(request, f"{inquiry.label} updated.")
        return HttpResponseRedirect(
            reverse("admin:rentals_rentalinquiry_change", args=[inquiry.pk])
        )

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = {
            **(extra_context or {}),
            "status_choices": RentalInquiry.Status.choices,
        }
        return super().change_view(request, object_id, form_url, extra_context)

    def confirm_view(self, request, pk):
        if not request.user.has_perm(CHANGE_PERMISSION):
            raise PermissionDenied
        inquiry = get_object_or_404(RentalInquiry, pk=pk)
        form = ConfirmForm(request.POST if request.method == "POST" else None)
        if request.method == "POST" and form.is_valid():
            try:
                services.confirm(
                    request.user,
                    inquiry,
                    create_hold=form.cleaned_data["create_hold"],
                    reason=form.cleaned_data["reason"],
                )
            except services.RentalError as exc:
                self.message_user(request, str(exc), level=messages.ERROR)
            else:
                self.message_user(request, f"{inquiry.label} is confirmed.")
            return HttpResponseRedirect(
                reverse("admin:rentals_rentalinquiry_change", args=[inquiry.pk])
            )
        context = {
            **self.admin_site.each_context(request),
            "title": f"Confirm {inquiry.label}",
            "opts": self.model._meta,
            "inquiry": inquiry,
            "form": form,
            "conflicts": services.conflicts(inquiry),
        }
        return TemplateResponse(request, "admin/rentals/confirm.html", context)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change and form.changed_data:
            services.log_action(
                request.user,
                "edit",
                obj,
                f"Changed: {', '.join(sorted(form.changed_data))}",
            )

    def delete_model(self, request, obj):
        services.log_action(request.user, "delete", obj)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for inquiry in queryset:
            services.log_action(request.user, "delete", inquiry)
        super().delete_queryset(request, queryset)
