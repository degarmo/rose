import csv
from collections import defaultdict
from datetime import timedelta

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from unfold.widgets import UnfoldAdminCheckboxSelectMultipleWidget, UnfoldAdminTextareaWidget

from apps.core.admin_auth import qr_data_uri
from apps.core.admin_widgets import RichTextWidget
from apps.core.email import site_link
from apps.core.models import AuditLog, audit

from . import desk
from .models import (
    AgreementSignature,
    IdCheck,
    Membership,
    MembershipAgreement,
    Payment,
    Tier,
    WebhookEvent,
)

REPORT_PERMISSION = "memberships.view_membership"


class ReadOnlyAdmin(ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class TierForm(forms.ModelForm):
    perks_text = forms.CharField(
        label="Perks",
        required=False,
        widget=UnfoldAdminTextareaWidget(attrs={"rows": 4}),
        help_text="One short line per perk, shown with a tick on the membership page.",
    )

    class Meta:
        model = Tier
        fields = [
            "name",
            "slug",
            "description",
            "perks_text",
            "price_cents",
            "interval",
            "duration_days",
            "renews",
            "events_per_month",
            "guests_included_per_event",
            "guest_discount",
            "premium_discord",
            "event_access",
            "allowed_event_tags",
            "grants_feed_access",
            "grants_members_events",
            "grants_members_education",
            "is_guest_pass",
            "is_featured",
            "is_active",
            "sort_order",
        ]
        widgets = {"allowed_event_tags": UnfoldAdminCheckboxSelectMultipleWidget}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["perks_text"].initial = "\n".join(self.instance.perks)

    def clean(self):
        cleaned = super().clean()
        self.instance.perks = [
            line.strip() for line in cleaned.get("perks_text", "").splitlines() if line.strip()
        ]
        if cleaned.get("event_access") == Tier.EventAccess.TAGGED and not cleaned.get(
            "allowed_event_tags"
        ):
            self.add_error("allowed_event_tags", "Choose at least one tag for tagged access.")
        return cleaned


STATUS_LABELS = {
    "Active": "success",
    "Grace period": "warning",
    "Waiting for payment": "warning",
    "Suspended": "danger",
}


@admin.register(Tier)
class TierAdmin(ModelAdmin):
    form = TierForm
    list_display = (
        "name",
        "price",
        "interval",
        "events_per_month",
        "grants_feed_access",
        "is_featured",
        "is_guest_pass",
        "offered",
        "sort_order",
    )
    list_filter = ("is_active", "interval", "is_guest_pass", "is_free")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("is_placeholder",)
    # A long page: one tab per part.
    fieldsets = (
        (
            "Plan",
            {
                "classes": ["tab"],
                "fields": ("name", "slug", "description", "perks_text", "is_featured", "is_active"),
                "description": "How the plan reads on the membership page. Inactive plans are "
                "kept for the people already on them but not offered.",
            },
        ),
        (
            "Price",
            {
                "classes": ["tab"],
                "fields": ("price_cents", "interval", "duration_days", "renews"),
                "description": "Price in cents (2500 is $25.00). A one-time pass runs for its "
                "number of days.",
            },
        ),
        (
            "Events",
            {
                "classes": ["tab"],
                "fields": (
                    "events_per_month",
                    "guests_included_per_event",
                    "guest_discount",
                    "event_access",
                    "allowed_event_tags",
                ),
                "description": "Leave events per month empty for unlimited. Tagged access "
                "reaches only members-only events with one of the chosen tags.",
            },
        ),
        (
            "Access",
            {
                "classes": ["tab"],
                "fields": (
                    "grants_feed_access",
                    "grants_members_events",
                    "grants_members_education",
                    "premium_discord",
                    "is_guest_pass",
                ),
                "description": "What the plan unlocks. "
                "A guest pass is one night, sold at the door.",
            },
        ),
        ("Order", {"classes": ["tab"], "fields": ("sort_order", "is_placeholder")}),
    )

    @display(
        description="Offered", label={"Offered": "success", "Not offered": None, "Demo": "warning"}
    )
    def offered(self, obj):
        if obj.is_placeholder:
            return "Demo"
        return "Offered" if obj.is_active else "Not offered"

    @admin.display(description="Price")
    def price(self, obj):
        return f"{obj.price_cents / 100:.2f} {obj.currency}"


@admin.register(MembershipAgreement)
class MembershipAgreementAdmin(ModelAdmin):
    list_display = ("version", "title", "published_at", "agreement_state")
    actions = ["publish"]
    fields = ("title", "body", "version", "published_at", "is_placeholder")
    readonly_fields = ("version", "published_at", "is_placeholder")

    def get_readonly_fields(self, request, obj=None):
        # What people signed never changes once it is published.
        if obj is not None and obj.published_at is not None:
            return ("title", "body", "version", "published_at", "is_placeholder")
        return self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        return obj is None or obj.published_at is None

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "body":
            kwargs["widget"] = RichTextWidget
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    @display(description="State", label={"Published": "success", "Draft": "warning"})
    def agreement_state(self, obj):
        if obj.is_placeholder:
            return "Demo"
        return "Published" if obj.published_at else "Draft"

    @admin.action(description="Publish (new members sign this version)")
    def publish(self, request, queryset):
        for agreement in queryset.filter(published_at__isnull=True):
            agreement.published_at = timezone.now()
            agreement.save(update_fields=["published_at"])


@admin.register(AgreementSignature)
class AgreementSignatureAdmin(ReadOnlyAdmin):
    """Staff only. The typed name is never shown anywhere else."""

    list_display = ("user", "agreement", "signed_at")
    fields = ("user", "agreement", "typed_name", "signed_at")
    readonly_fields = fields
    search_fields = ("user__display_name",)


class PaymentInline(TabularInline):
    model = Payment
    fk_name = "membership"
    fields = ("created_at", "status", "method", "amount", "recorded_by", "note")
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Amount")
    def amount(self, obj):
        return f"{obj.amount_cents / 100:.2f}"


@admin.register(Payment)
class PaymentAdmin(ReadOnlyAdmin):
    """Payments cannot be added, edited or deleted here. Refunds are recorded at the door desk."""

    list_display = ("created_at", "membership", "payment_status", "method", "amount", "recorded_by")
    list_filter = ("status", "method", "created_at")
    search_fields = ("membership__reference_code", "membership__user__display_name")
    date_hierarchy = "created_at"
    list_select_related = ("membership", "recorded_by")
    fields = (
        "membership",
        "status",
        "method",
        "amount_cents",
        "provider_payment_ref",
        "refund_of",
        "recorded_by",
        "note",
        "created_at",
    )
    readonly_fields = fields

    @display(description="Amount", ordering="amount_cents")
    def amount(self, obj):
        return f"${obj.amount_display}"

    @display(
        description="Status",
        ordering="status",
        label={"Succeeded": "success", "Refunded": "warning", "Failed": "danger"},
    )
    def payment_status(self, obj):
        return obj.get_status_display()


@admin.register(IdCheck)
class IdCheckAdmin(ReadOnlyAdmin):
    """Only that a valid photo ID showing 18+ was seen, by whom and when. Nothing else."""

    list_display = ("membership", "checked_by", "checked_at", "verified_18_plus")
    list_filter = ("checked_at",)
    search_fields = ("membership__reference_code", "membership__user__display_name")
    list_select_related = ("membership", "checked_by")
    fields = list_display
    readonly_fields = fields


@admin.register(WebhookEvent)
class WebhookEventAdmin(ReadOnlyAdmin):
    list_display = ("received_at", "provider", "event_id", "processed_at", "has_error")
    list_filter = ("provider",)
    fields = ("provider", "event_id", "payload", "received_at", "processed_at", "error")
    readonly_fields = fields

    @admin.display(boolean=True, description="Error")
    def has_error(self, obj):
        return bool(obj.error)


@admin.register(Membership)
class MembershipAdmin(ModelAdmin):
    list_display = (
        "reference_code",
        "member",
        "tier",
        "membership_status",
        "current_period_end",
        "source",
        "desk_link",
    )
    list_filter = ("status", "tier", "source", "paid_awaiting_id_check")
    list_select_related = ("tier", "user")
    search_fields = ("reference_code", "user__display_name")
    inlines = [PaymentInline]
    fields = (
        "reference_code",
        "user",
        "tier",
        "status",
        "source",
        "current_period_start",
        "current_period_end",
        "auto_renew",
        "cancel_at_period_end",
        "paid_awaiting_id_check",
        "provider",
        "created_at",
        "updated_at",
    )
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Member", ordering="user__display_name")
    def member(self, obj):
        return obj.user.display_name if obj.user else "Deleted account"

    @display(description="Status", ordering="status", label=STATUS_LABELS)
    def membership_status(self, obj):
        return obj.get_status_display()

    @display(description="Door desk")
    def desk_link(self, obj):
        return format_html(
            '<a class="rose-link" href="{}?q={}">Open</a>',
            reverse("admin:memberships_door_desk"),
            obj.reference_code,
        )

    def get_urls(self):
        extra = [
            path(
                "door-desk/",
                self.admin_site.admin_view(self.door_desk_view),
                name="memberships_door_desk",
            ),
            path(
                "summary/",
                self.admin_site.admin_view(self.summary_view),
                name="memberships_summary",
            ),
            path(
                "export/", self.admin_site.admin_view(self.export_view), name="memberships_export"
            ),
        ]
        return extra + super().get_urls()

    # Door desk

    def door_desk_view(self, request):
        if not request.user.has_perm(desk.DESK_PERMISSION):
            raise PermissionDenied
        revealed = {}
        if request.method == "POST":
            try:
                outcome = desk.perform(request.user, request.POST)
            except desk.DeskError as exc:
                self.message_user(request, str(exc), level=messages.ERROR)
                outcome = None
            if outcome is not None and outcome.signature:
                revealed = outcome.signature
            else:
                if outcome is not None:
                    self.message_user(request, outcome.message)
                query = request.POST.get("q", "")
                return HttpResponseRedirect(f"{request.path}?q={query}")
        query = request.GET.get("q", "") or request.POST.get("q", "")
        results = []
        for membership in desk.find_memberships(query):
            row = desk.card(membership)
            row["signature_name"] = revealed.get(membership.pk)
            results.append(row)
        context = {
            **self.admin_site.each_context(request),
            "title": "Door desk",
            "opts": self.model._meta,
            "query": query,
            "results": results,
            "searched": bool(query.strip()),
            # "Convert to member": the guest scans this and joins on their own phone,
            # signed in to their own account, so their signature stays theirs.
            "join_url": site_link("/join"),
            "join_qr": qr_data_uri(site_link("/join"))
            if any(r["is_guest_pass"] for r in results)
            else None,
            "donation_methods": desk.DONATION_METHODS,
            "tonight_events": list(desk.tonight_events()) if results else [],
            "staff_door_url": site_link("/members/staff/door"),
        }
        # The camera policy for this page is set by PrivacyHeadersMiddleware.
        return TemplateResponse(request, "admin/memberships/door_desk.html", context)

    # Reporting

    def summary_view(self, request):
        if not request.user.has_perm(REPORT_PERMISSION):
            raise PermissionDenied
        now = timezone.localtime()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        memberships = Membership.objects.exclude(tier__is_guest_pass=True)
        by_status = dict(memberships.values_list("status").annotate(n=Count("id")))
        by_tier = list(
            Membership.objects.filter(status__in=Membership.ENTITLED, tier__is_guest_pass=False)
            .values("tier__name")
            .annotate(n=Count("id"))
            .order_by("tier__name")
        )
        first_payments = {}
        new_this_month = renewed_this_month = 0
        for payment in Payment.objects.filter(
            status=Payment.Status.SUCCEEDED, membership__tier__is_guest_pass=False
        ).order_by("created_at"):
            is_first = payment.membership_id not in first_payments
            first_payments.setdefault(payment.membership_id, payment.created_at)
            if payment.created_at >= month_start:
                if is_first:
                    new_this_month += 1
                else:
                    renewed_this_month += 1
        expired_this_month = (
            Membership.objects.filter(status=Membership.Status.EXPIRED, ended_at__gte=month_start)
            .exclude(tier__is_guest_pass=True)
            .count()
        )

        months = []
        cursor = month_start
        for _ in range(12):
            months.append(cursor)
            cursor = (cursor - timedelta(days=1)).replace(day=1)
        revenue = defaultdict(lambda: defaultdict(int))
        oldest = months[-1]
        guest_visits = defaultdict(int)
        for created_at in Payment.objects.filter(
            created_at__gte=oldest,
            status=Payment.Status.SUCCEEDED,
            membership__tier__is_guest_pass=True,
        ).values_list("created_at", flat=True):
            guest_visits[timezone.localtime(created_at).strftime("%Y-%m")] += 1
        for payment in Payment.objects.filter(
            created_at__gte=oldest, status__in=[Payment.Status.SUCCEEDED, Payment.Status.REFUNDED]
        ):
            key = timezone.localtime(payment.created_at).strftime("%Y-%m")
            sign = -1 if payment.status == Payment.Status.REFUNDED else 1
            revenue[key][payment.method] += sign * payment.amount_cents
        methods = [m for m in Payment.Method.values if m != Payment.Method.COMP]
        revenue_rows = [
            {
                "month": month.strftime("%b %Y"),
                "cells": [f"{revenue[month.strftime('%Y-%m')][m] / 100:.2f}" for m in methods],
                "total": f"{sum(revenue[month.strftime('%Y-%m')][m] for m in methods) / 100:.2f}",
            }
            for month in months
        ]
        context = {
            **self.admin_site.each_context(request),
            "title": "Membership summary",
            "opts": self.model._meta,
            "status_rows": [
                (label, by_status.get(value, 0)) for value, label in Membership.Status.choices
            ],
            "tier_rows": by_tier,
            "new_this_month": new_this_month,
            "renewed_this_month": renewed_this_month,
            "expired_this_month": expired_this_month,
            "method_labels": [Payment.Method(m).label for m in methods],
            "revenue_rows": revenue_rows,
            "guest_rows": [
                {"month": month.strftime("%b %Y"), "visits": guest_visits[month.strftime("%Y-%m")]}
                for month in months
            ],
            "can_include_email": request.user.is_superuser,
        }
        return TemplateResponse(request, "admin/memberships/summary.html", context)

    def export_view(self, request):
        if request.method != "POST" or not request.user.has_perm(REPORT_PERMISSION):
            raise PermissionDenied
        include_email = request.POST.get("include_email") == "on"
        if include_email and not request.user.is_superuser:
            raise PermissionDenied
        rows = Membership.objects.select_related("tier", "user").order_by(
            "status", "user__display_name"
        )
        audit(
            AuditLog.Category.EXPORT,
            "membership_csv_with_email" if include_email else "membership_csv",
            request.user,
            f"Membership export ({rows.count()} rows)",
            "export",
            reason="Included contact email" if include_email else "",
        )
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="memberships-{timezone.localdate():%Y-%m-%d}.csv"'
        )
        response["Cache-Control"] = "private, no-store"
        writer = csv.writer(response)
        header = ["Display name", "Tier", "Status", "Period end", "Source"]
        if include_email:
            header.append("Email")
        writer.writerow(header)
        for membership in rows:
            name = membership.user.display_name if membership.user else "Deleted account"
            row = [
                f"'{name}" if name[:1] in "=+-@" else name,
                membership.tier.name,
                membership.get_status_display(),
                timezone.localtime(membership.current_period_end).strftime("%Y-%m-%d")
                if membership.current_period_end
                else "",
                membership.get_source_display(),
            ]
            if include_email:
                row.append(membership.user.email if membership.user else "")
            writer.writerow(row)
        return response
