from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils import timezone

from apps.core.models import AuditLog, audit

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
    )

    class Meta:
        model = Newsletter
        fields = ["subject", "preheader", "body", "status", "scheduled_at"]
        widgets = {"body": forms.Textarea(attrs={"rows": 18})}

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
class NewsletterAdmin(admin.ModelAdmin):
    form = NewsletterForm
    list_display = ("subject", "status", "scheduled_at", "sent_at", "sent_count")
    list_filter = ("status",)
    change_form_template = "admin/newsletter/change_form.html"
    readonly_fields = ("sent_at", "sent_count", "created_by")

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and obj.status == Newsletter.Status.SENT:
            return ("subject", "preheader", "body", "status", "scheduled_at", *self.readonly_fields)
        return self.readonly_fields

    def get_fields(self, request, obj=None):
        if obj is not None and obj.status == Newsletter.Status.SENT:
            return ("subject", "preheader", "body", "status", "sent_at", "sent_count", "created_by")
        return ("subject", "preheader", "body", "status", "scheduled_at")

    def has_delete_permission(self, request, obj=None):
        return obj is None or obj.status == Newsletter.Status.DRAFT

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
class SubscriberAdmin(admin.ModelAdmin):
    """People join the list themselves, with double opt-in; staff cannot add anyone."""

    list_display = ("__str__", "email", "status", "created_at", "confirmed_at")
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
class SuppressionAdmin(admin.ModelAdmin):
    list_display = ("email_hash", "unsubscribed_on")
    fields = ("email_hash", "unsubscribed_on", "created_at")
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
