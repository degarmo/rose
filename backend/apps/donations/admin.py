from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from apps.core.admin_display import chip
from apps.core.models import AuditLog, audit

from . import services
from .models import Acknowledgement, AcknowledgementTemplate, Donation

VIEW_PERMISSION = "donations.view_donation"


class ReadOnlyAdmin(ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Donation)
class DonationAdmin(ReadOnlyAdmin):
    """Donations cannot be added, edited or deleted here. Gifts at the door are
    recorded on the door desk; online gifts arrive from the payment provider."""

    list_display = (
        "created_at",
        "reference",
        "donor_display",
        "amount",
        "method",
        "status_chip",
        "acknowledgement_link",
    )
    status_chip = chip("status", {"Received": "success", "Failed": "danger", "Refund": "warning"})
    list_filter = ("status", "method", "acknowledgement_requested")
    search_fields = ("reference",)
    fields = (
        "reference",
        "status",
        "method",
        "amount_cents",
        "currency",
        "donor_display",
        "donor",
        "acknowledgement_requested",
        "provider",
        "provider_payment_ref",
        "refund_of",
        "recorded_by",
        "note",
        "created_at",
    )
    readonly_fields = fields

    @admin.display(description="Amount", ordering="amount_cents")
    def amount(self, obj):
        return obj.amount_display

    @admin.display(description="Acknowledgement")
    def acknowledgement_link(self, obj):
        if obj.status != Donation.Status.SUCCEEDED:
            return "-"
        return format_html(
            '<a href="{}">Open</a>', reverse("admin:donations_acknowledgement", args=[obj.pk])
        )

    def get_urls(self):
        extra = [
            path(
                "<int:pk>/acknowledgement/",
                self.admin_site.admin_view(self.acknowledgement_view),
                name="donations_acknowledgement",
            ),
        ]
        return extra + super().get_urls()

    def acknowledgement_view(self, request, pk):
        """Printable acknowledgement. POST action=email sends it to the address on file."""
        if not request.user.has_perm(VIEW_PERMISSION):
            raise PermissionDenied
        donation = get_object_or_404(Donation, pk=pk, status=Donation.Status.SUCCEEDED)
        acknowledgement = Acknowledgement.objects.filter(donation=donation).first()
        if request.method == "POST":
            if request.POST.get("action") == "email" and acknowledgement is not None:
                try:
                    sent = services.send_acknowledgement(acknowledgement, staff=request.user)
                except services.DonationError as exc:
                    self.message_user(request, str(exc), level=messages.ERROR)
                else:
                    if sent:
                        self.message_user(request, "Acknowledgement emailed.")
                    else:
                        self.message_user(
                            request, "There is no address waiting for it.", level=messages.WARNING
                        )
            elif request.POST.get("action") == "printed":
                if acknowledgement is None:
                    acknowledgement = Acknowledgement.objects.create(donation=donation)
                acknowledgement.printed_at = timezone.now()
                acknowledgement.save(update_fields=["printed_at"])
                audit(
                    AuditLog.Category.DONATIONS,
                    "acknowledgement_printed",
                    request.user,
                    f"Donation {donation.reference}",
                    "donation",
                    target_ref=donation.reference,
                )
                self.message_user(request, "Marked as printed.")
            return HttpResponseRedirect(request.path)
        template = AcknowledgementTemplate.current()
        subject = body = None
        if template is not None:
            subject, body = services.render_acknowledgement(donation, template)
        context = {
            **self.admin_site.each_context(request),
            "title": f"Acknowledgement {donation.reference}",
            "opts": self.model._meta,
            "donation": donation,
            "acknowledgement": acknowledgement,
            "subject": subject,
            "body": body,
            "is_placeholder": template is not None and template.is_placeholder,
            "wording_url": reverse("admin:donations_acknowledgementtemplate_changelist"),
        }
        return TemplateResponse(request, "admin/donations/acknowledgement.html", context)


@admin.register(AcknowledgementTemplate)
class AcknowledgementTemplateAdmin(ModelAdmin):
    fields = ("subject", "body", "is_placeholder", "updated_at")
    readonly_fields = ("is_placeholder", "updated_at")

    def has_add_permission(self, request):
        return not AcknowledgementTemplate.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        template = AcknowledgementTemplate.objects.filter(pk=1).first()
        if template is None:
            return HttpResponseRedirect(reverse("admin:donations_acknowledgementtemplate_add"))
        return HttpResponseRedirect(
            reverse("admin:donations_acknowledgementtemplate_change", args=[template.pk])
        )

    def save_model(self, request, obj, form, change):
        # Staff wording replaces any development placeholder.
        obj.is_placeholder = False
        super().save_model(request, obj, form, change)
