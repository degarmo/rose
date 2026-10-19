import csv
from collections import defaultdict
from datetime import timedelta

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from apps.core.admin_auth import qr_data_uri
from apps.core.email import site_link
from apps.core.models import AuditLog, audit
from apps.donations.services import DonationError, record_desk_donation

from . import desk
from .models import (
    AgreementSignature,
    IdCheck,
    Membership,
    MembershipAgreement,
    Payment,
    Tier,
    WebhookEvent,
    has_id_check,
)

DESK_PERMISSION = "memberships.change_membership"
DONATION_DESK_METHODS = [
    ("cash", "Cash"),
    ("card_in_person", "Card in person"),
    ("check", "Check"),
]
REPORT_PERMISSION = "memberships.view_membership"


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class TierForm(forms.ModelForm):
    benefits_text = forms.CharField(
        label="Benefits",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="One short line per benefit.",
    )

    class Meta:
        model = Tier
        fields = [
            "name",
            "slug",
            "description",
            "benefits_text",
            "price_cents",
            "interval",
            "duration_days",
            "grants_feed_access",
            "grants_members_events",
            "grants_members_education",
            "is_guest_pass",
            "is_active",
            "sort_order",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["benefits_text"].initial = "\n".join(self.instance.benefits)

    def clean(self):
        cleaned = super().clean()
        self.instance.benefits = [
            line.strip() for line in cleaned.get("benefits_text", "").splitlines() if line.strip()
        ]
        return cleaned


@admin.register(Tier)
class TierAdmin(admin.ModelAdmin):
    form = TierForm
    list_display = (
        "name",
        "price",
        "interval",
        "is_guest_pass",
        "is_active",
        "is_placeholder",
        "sort_order",
    )
    list_filter = ("is_active", "interval", "is_guest_pass")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("is_placeholder",)

    @admin.display(description="Price")
    def price(self, obj):
        return f"{obj.price_cents / 100:.2f} {obj.currency}"


@admin.register(MembershipAgreement)
class MembershipAgreementAdmin(admin.ModelAdmin):
    list_display = ("version", "title", "published_at", "is_placeholder")
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


class PaymentInline(admin.TabularInline):
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

    list_display = ("created_at", "membership", "status", "method", "amount", "recorded_by")
    list_filter = ("status", "method")
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

    @admin.display(description="Amount")
    def amount(self, obj):
        return f"{obj.amount_cents / 100:.2f}"


@admin.register(IdCheck)
class IdCheckAdmin(ReadOnlyAdmin):
    list_display = ("membership", "checked_by", "checked_at", "verified_18_plus")
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


def find_memberships(query):
    query = query.strip()
    if not query:
        return Membership.objects.none()
    code = query.upper().replace(" ", "")
    if len(code) == 6 and "-" not in code:
        code = f"{code[:3]}-{code[3:]}"
    return (
        Membership.objects.filter(Q(reference_code=code) | Q(user__display_name__icontains=query))
        .select_related("tier", "user")
        .order_by("-updated_at")[:10]
    )


def cents(value):
    try:
        return max(0, round(float(value) * 100))
    except (TypeError, ValueError):
        return None


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = (
        "reference_code",
        "member",
        "tier",
        "status",
        "current_period_end",
        "source",
        "desk_link",
    )
    list_filter = ("status", "tier", "source")
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

    @admin.display(description="Door desk")
    def desk_link(self, obj):
        return format_html(
            '<a href="{}?q={}">Open</a>', reverse("admin:memberships_door_desk"), obj.reference_code
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
        if not request.user.has_perm(DESK_PERMISSION):
            raise PermissionDenied
        revealed = {}
        if request.method == "POST":
            revealed = self._handle_desk_action(request)
            if revealed is None:
                query = request.POST.get("q", "")
                return HttpResponseRedirect(f"{request.path}?q={query}")
        query = request.GET.get("q", "") or request.POST.get("q", "")
        results = []
        for membership in find_memberships(query):
            results.append(
                {
                    "membership": membership,
                    "is_guest_pass": membership.tier.is_guest_pass,
                    "id_checked": has_id_check(membership.user) if membership.user else False,
                    "payments": list(membership.payments.all()[:5]),
                    "default_amount": f"{membership.tier.price_cents / 100:.2f}",
                    "signature_name": revealed.get(membership.pk),
                }
            )
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
            "donation_methods": DONATION_DESK_METHODS,
        }
        # The camera policy for this page is set by PrivacyHeadersMiddleware.
        return TemplateResponse(request, "admin/memberships/door_desk.html", context)

    def _handle_desk_action(self, request):
        """Returns {membership_pk: name} for a signature reveal, or None after an action."""
        data = request.POST
        action = data.get("action")
        try:
            if action == "record_donation":
                amount = cents(data.get("amount"))
                if not amount:
                    raise desk.DeskError("Enter an amount.")
                try:
                    donation = record_desk_donation(
                        request.user,
                        amount,
                        data.get("method", ""),
                        donor_display=data.get("donor_display", ""),
                        acknowledgement_email=data.get("acknowledgement_email", ""),
                        note=data.get("note", ""),
                    )
                except DonationError as exc:
                    raise desk.DeskError(str(exc)) from exc
                self.message_user(request, f"Donation of {donation.amount_display} recorded.")
                return None
            if action == "refund":
                payment = get_object_or_404(Payment, pk=data.get("payment"))
                amount = cents(data.get("amount"))
                if amount is None:
                    raise desk.DeskError("Enter an amount.")
                desk.refund(request.user, payment, amount, data.get("note", ""))
                self.message_user(request, "Refund recorded.")
                return None
            membership = get_object_or_404(
                Membership.objects.select_related("tier", "user"), pk=data.get("membership")
            )
            id_checked = data.get("id_checked") == "on"
            if action == "activate":
                amount = cents(data.get("amount"))
                if amount is None:
                    raise desk.DeskError("Enter an amount.")
                desk.record_payment_and_activate(
                    request.user,
                    membership,
                    data.get("method"),
                    amount,
                    data.get("note", ""),
                    id_checked,
                )
                self.message_user(request, f"{membership.reference_code} is active.")
            elif action == "guest_visit":
                amount = cents(data.get("amount"))
                if amount is None:
                    raise desk.DeskError("Enter an amount.")
                desk.guest_visit(
                    request.user,
                    membership,
                    data.get("method"),
                    amount,
                    data.get("note", ""),
                    id_checked,
                )
                self.message_user(request, f"{membership.reference_code} is in for tonight.")
            elif action == "activate_paid":
                desk.activate_paid_online(request.user, membership, id_checked)
                self.message_user(request, f"{membership.reference_code} is active.")
            elif action == "renew":
                amount = cents(data.get("amount"))
                if amount is None:
                    raise desk.DeskError("Enter an amount.")
                desk.renew(
                    request.user, membership, data.get("method"), amount, data.get("note", "")
                )
                self.message_user(request, f"{membership.reference_code} renewed.")
            elif action == "comp":
                desk.comp(request.user, membership, data.get("reason", ""), id_checked)
                self.message_user(
                    request, f"{membership.reference_code} is a complimentary membership."
                )
            elif action == "suspend":
                desk.suspend(request.user, membership, data.get("reason", ""))
                self.message_user(request, f"{membership.reference_code} is suspended.")
            elif action == "reinstate":
                desk.reinstate(request.user, membership, data.get("reason", ""))
                self.message_user(request, f"{membership.reference_code} is reinstated.")
            elif action == "show_signature":
                return {
                    membership.pk: desk.reveal_signature_name(request.user, membership)
                    or "No signature on file"
                }
            else:
                raise desk.DeskError("Unknown action.")
        except desk.DeskError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
        return None

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
