from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin
from unfold.decorators import display
from unfold.widgets import UnfoldAdminSelectWidget

from apps.core.admin_display import chip
from apps.core.admin_widgets import RichTextWidget
from apps.core.models import AuditLog, audit
from apps.core.text import sanitize_rich_text

from . import services
from .models import Newsletter, Subscriber, Suppression

SEND_PERMISSION = "newsletter.change_newsletter"


class NewsletterForm(forms.ModelForm):
    status = forms.ChoiceField(
        choices=[
            (Newsletter.Status.DRAFT, "Draft"),
            (Newsletter.Status.SCHEDULED, "Scheduled"),
        ],
        help_text="Scheduled newsletters go out at the time below. Use Send to send now.",
        widget=UnfoldAdminSelectWidget,
    )

    class Meta:
        model = Newsletter
        fields = ["subject", "preheader", "body", "status", "scheduled_at"]
        widgets = {"body": RichTextWidget}

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk and self.instance.status == Newsletter.Status.SENT:
            raise ValidationError("A sent newsletter cannot be changed.")
        if cleaned.get("status") == Newsletter.Status.SCHEDULED:
            when = cleaned.get("scheduled_at")
            if when is None:
                self.add_error("scheduled_at", "Choose when it should go out.")
            elif when <= timezone.now():
                self.add_error("scheduled_at", "Choose a time in the future.")
        return cleaned


@admin.register(Newsletter)
class NewsletterAdmin(ModelAdmin):
    form = NewsletterForm
    list_display = ("subject", "status_chip", "scheduled_at", "sent_at", "sent_count")
    status_chip = chip("status", {"Draft": "warning", "Scheduled": "info", "Sent": "success"})
    list_filter = ("status",)
    # Preview and sending sit outside the change form (forms cannot be nested).
    change_form_outer_before_template = "admin/newsletter/send_tools.html"

    class Media:
        js = ("newsletter/inbox-preview.js",)

    readonly_fields = ("sent_at", "sent_count", "created_by")

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and obj.status == Newsletter.Status.SENT:
            return (
                "subject",
                "preheader",
                "body_preview",
                "status",
                "scheduled_at",
                *self.readonly_fields,
            )
        return self.readonly_fields

    def get_fields(self, request, obj=None):
        if obj is not None and obj.status == Newsletter.Status.SENT:
            return (
                "subject",
                "preheader",
                "body_preview",
                "status",
                "sent_at",
                "sent_count",
                "created_by",
            )
        return ("subject", "preheader", "body", "status", "scheduled_at")

    def has_delete_permission(self, request, obj=None):
        return obj is None or obj.status == Newsletter.Status.DRAFT

    @display(description="Body")
    def body_preview(self, obj):
        """As sent: the stored body is already sanitised (apps.core.text)."""
        return mark_safe(sanitize_rich_text(obj.body))

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_urls(self):
        extra = [
            path(
                "<int:pk>/send-test/",
                self.admin_site.admin_view(self.send_test_view),
                name="newsletter_send_test",
            ),
            path(
                "<int:pk>/send/",
                self.admin_site.admin_view(self.send_view),
                name="newsletter_send",
            ),
        ]
        return extra + super().get_urls()

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = {
            **(extra_context or {}),
            "recipient_count": sum(1 for _ in services.recipients()),
            "sender_name": settings.EMAIL_SENDER_NAME,
        }
        return super().change_view(request, object_id, form_url, extra_context)

    def _back(self, newsletter):
        return HttpResponseRedirect(
            reverse("admin:newsletter_newsletter_change", args=[newsletter.pk])
        )

    def send_test_view(self, request, pk):
        if request.method != "POST" or not request.user.has_perm(SEND_PERMISSION):
            raise PermissionDenied
        newsletter = get_object_or_404(Newsletter, pk=pk)
        try:
            services.send_test(newsletter, request.user)
        except services.NewsletterError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
        else:
            self.message_user(request, "A test was sent to your own address only.")
        return self._back(newsletter)

    def send_view(self, request, pk):
        if request.method != "POST" or not request.user.has_perm(SEND_PERMISSION):
            raise PermissionDenied
        newsletter = get_object_or_404(Newsletter, pk=pk)
        if request.POST.get("confirm") != "on":
            self.message_user(
                request, "Tick the box to confirm before sending.", level=messages.ERROR
            )
            return self._back(newsletter)
        try:
            services.queue_send(newsletter, request.user)
        except services.NewsletterError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
        else:
            self.message_user(request, "Sending has started. Refresh to see the count.")
        return self._back(newsletter)


@admin.register(Subscriber)
class SubscriberAdmin(ModelAdmin):
    """People join the list themselves, with double opt-in; staff cannot add anyone."""

    list_display = ("__str__", "email", "status_chip", "created_at", "confirmed_at")
    status_chip = chip("status", {"Waiting for confirmation": "warning", "Confirmed": "success"})
    list_filter = ("status",)
    search_fields = ("email",)
    fields = ("email", "status", "created_at", "confirmed_at", "unsubscribed_at")
    readonly_fields = fields
    actions = ["unsubscribe_selected"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.action(description="Unsubscribe the selected people", permissions=["delete"])
    def unsubscribe_selected(self, request, queryset):
        count = 0
        for subscriber in queryset.exclude(status=Subscriber.Status.UNSUBSCRIBED):
            services.unsubscribe(subscriber.token)
            count += 1
        audit(
            AuditLog.Category.NEWSLETTER,
            "unsubscribe_by_staff",
            request.user,
            f"{count} subscriber(s)",
            "subscriber",
        )
        self.message_user(request, f"{count} unsubscribed.")

    def delete_queryset(self, request, queryset):
        audit(
            AuditLog.Category.NEWSLETTER,
            "delete_subscribers",
            request.user,
            f"{queryset.count()} subscriber(s)",
            "subscriber",
        )
        super().delete_queryset(request, queryset)


@admin.register(Suppression)
class SuppressionAdmin(ModelAdmin):
    list_display = ("email_hash", "unsubscribed_on")
    fields = ("email_hash", "unsubscribed_on", "created_at")
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
