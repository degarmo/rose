import csv

from django import forms
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone

from apps.core.models import AuditLog, audit

from .models import Availability, Interest, VolunteerSignup

VIEW_PERMISSION = "volunteers.view_volunteersignup"


def spreadsheet_safe(value):
    """A cell a spreadsheet will never run as a formula."""
    value = str(value)
    return f"'{value}" if value[:1] in "=+-@" else value


class InterestFilter(admin.SimpleListFilter):
    title = "interest"
    parameter_name = "interest"

    def lookups(self, request, model_admin):
        return Interest.choices

    def queryset(self, request, queryset):
        if self.value() in Interest.values:
            return queryset.filter(interests__contains=[self.value()])
        return queryset


class AvailabilityFilter(admin.SimpleListFilter):
    title = "availability"
    parameter_name = "availability"

    def lookups(self, request, model_admin):
        return Availability.choices

    def queryset(self, request, queryset):
        if self.value() in Availability.values:
            return queryset.filter(availability__contains=[self.value()])
        return queryset


class SignupForm(forms.ModelForm):
    interests = forms.MultipleChoiceField(
        choices=Interest.choices, widget=forms.CheckboxSelectMultiple
    )
    availability = forms.MultipleChoiceField(
        choices=Availability.choices, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = VolunteerSignup
        fields = [
            "contact_name",
            "contact_email",
            "interests",
            "availability",
            "experience_note",
            "status",
        ]


class ExportForm(forms.Form):
    interest = forms.ChoiceField(choices=[("", "Any interest"), *Interest.choices], required=False)
    status = forms.ChoiceField(
        choices=[("", "Any status"), *VolunteerSignup.Status.choices], required=False
    )
    include_email = forms.BooleanField(
        required=False, label="Include contact email (superusers only, logged separately)"
    )


@admin.register(VolunteerSignup)
class VolunteerSignupAdmin(admin.ModelAdmin):
    form = SignupForm
    list_display = ("__str__", "contact_name", "interest_list", "status", "created_at")
    list_filter = ("status", InterestFilter, AvailabilityFilter)
    search_fields = ("contact_name",)
    readonly_fields = ("user", "created_at", "updated_at")
    change_list_template = "admin/volunteers/change_list.html"
    actions = ["mark_contacted", "mark_active", "mark_inactive"]

    def has_add_permission(self, request):
        return False

    @admin.display(description="Interests")
    def interest_list(self, obj):
        return ", ".join(obj.interest_labels)

    def _mark(self, request, queryset, status):
        updated = 0
        for signup in queryset:
            signup.status = status
            signup.save(update_fields=["status", "updated_at"])
            updated += 1
        self.message_user(request, f"{updated} updated.")

    @admin.action(description="Mark contacted", permissions=["change"])
    def mark_contacted(self, request, queryset):
        self._mark(request, queryset, VolunteerSignup.Status.CONTACTED)

    @admin.action(description="Mark active", permissions=["change"])
    def mark_active(self, request, queryset):
        self._mark(request, queryset, VolunteerSignup.Status.ACTIVE)

    @admin.action(description="Mark inactive", permissions=["change"])
    def mark_inactive(self, request, queryset):
        self._mark(request, queryset, VolunteerSignup.Status.INACTIVE)

    def get_urls(self):
        extra = [
            path(
                "export/",
                self.admin_site.admin_view(self.export_view),
                name="volunteers_export",
            ),
        ]
        return extra + super().get_urls()

    def export_view(self, request):
        """GET shows the options; POST downloads the CSV and is logged."""
        if not request.user.has_perm(VIEW_PERMISSION):
            raise PermissionDenied
        form = ExportForm(request.POST if request.method == "POST" else None)
        if not request.user.is_superuser:
            del form.fields["include_email"]
        if request.method == "POST" and form.is_valid():
            return self._csv(request, form.cleaned_data)
        context = {
            **self.admin_site.each_context(request),
            "title": "Export volunteer signups",
            "opts": self.model._meta,
            "form": form,
        }
        return TemplateResponse(request, "admin/volunteers/export.html", context)

    def _csv(self, request, options):
        include_email = bool(options.get("include_email"))
        if include_email and not request.user.is_superuser:
            raise PermissionDenied
        rows = VolunteerSignup.objects.order_by("status", "contact_name")
        if options.get("interest"):
            rows = rows.filter(interests__contains=[options["interest"]])
        if options.get("status"):
            rows = rows.filter(status=options["status"])
        audit(
            AuditLog.Category.EXPORT,
            "volunteer_csv_with_email" if include_email else "volunteer_csv",
            request.user,
            f"Volunteer export ({rows.count()} rows)",
            "export",
            reason="Included contact email" if include_email else "",
        )
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="volunteers-{timezone.localdate():%Y-%m-%d}.csv"'
        )
        response["Cache-Control"] = "private, no-store"
        writer = csv.writer(response)
        header = ["Name", "Interests", "Availability", "Status", "Signed up"]
        if include_email:
            header.append("Email")
        writer.writerow(header)
        for signup in rows:
            row = [
                spreadsheet_safe(signup.contact_name),
                "; ".join(signup.interest_labels),
                "; ".join(signup.availability_labels),
                signup.get_status_display(),
                timezone.localtime(signup.created_at).strftime("%Y-%m-%d"),
            ]
            if include_email:
                row.append(spreadsheet_safe(signup.contact_email))
            writer.writerow(row)
        return response
