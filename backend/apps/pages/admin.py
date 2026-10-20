from django import forms
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action
from unfold.widgets import UnfoldAdminTextareaWidget

from apps.core.admin_display import image_preview

from .models import FAQItem, PageContent, Redirect, SiteSettings, SocialLink, StaffProfile
from .site_content import ContentError, load_guarded, parse_texts

MAX_CONTENT_FILE_BYTES = 200_000


class SocialLinkInline(TabularInline):
    model = SocialLink
    extra = 0


@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
    inlines = [SocialLinkInline]
    readonly_fields = ("updated_at",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "tagline",
                    "hours_text",
                    "address_text",
                    "phone_text",
                    "directions_text",
                    "contact_email",
                    "quick_exit_url",
                )
            },
        ),
        (
            "Giving",
            {
                "fields": ("nonprofit_status_text", "check_payable_to", "mailing_address"),
                "description": "Shown on the Donate page.",
            },
        ),
        (
            "For donation acknowledgements only",
            {
                "fields": ("legal_name", "ein"),
                "description": "Never shown on the site or in an email subject.",
            },
        ),
        (None, {"fields": ("updated_at",)}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        settings_obj = SiteSettings.load()
        return redirect(reverse("admin:pages_sitesettings_change", args=[settings_obj.pk]))


@admin.register(FAQItem)
class FAQItemAdmin(ModelAdmin):
    list_display = ("question", "sort_order", "is_published")
    list_editable = ("sort_order", "is_published")
    list_filter = ("is_published",)
    search_fields = ("question", "answer")


@admin.register(StaffProfile)
class StaffProfileAdmin(ModelAdmin):
    photo_preview = image_preview("photo")
    readonly_fields = ("photo_preview",)
    list_display = ("display_name", "role_title", "sort_order", "is_published")
    list_editable = ("sort_order", "is_published")
    list_filter = ("is_published",)
    prepopulated_fields = {"slug": ("display_name",)}
    autocomplete_fields = ("user",)
    fieldsets = (
        (None, {"fields": ("display_name", "slug", "role_title", "bio", "sort_order")}),
        (
            "Photo (optional)",
            {
                "fields": (
                    "photo_preview",
                    "photo",
                    "photo_alt",
                    "photo_faces_visible",
                    "photo_consent_confirmed",
                )
            },
        ),
        (
            "Account link (optional)",
            {
                "fields": ("user",),
                "description": "Only if the volunteer asks for it. Nothing about the account "
                "is ever shown on the site.",
            },
        ),
        ("Publishing", {"fields": ("is_published",)}),
    )


class PageContentForm(forms.ModelForm):
    class Meta:
        model = PageContent
        fields = ["page", "key", "format", "value"]
        widgets = {"value": UnfoldAdminTextareaWidget(attrs={"rows": 6})}


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": ".yaml,.yml"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single = super().clean
        return (
            [single(item, initial) for item in data]
            if isinstance(data, list | tuple)
            else [single(data, initial)]
        )


class LoadContentForm(forms.Form):
    files = MultipleFileField(label="YAML files", help_text="One or more files from /content.")
    commit = forms.BooleanField(
        required=False,
        label="Write the changes",
        help_text="Leave unticked first to see what would change.",
    )
    allow_draft = forms.BooleanField(
        required=False,
        label="Allow files still marked as drafts (production only; logged)",
    )

    def clean_files(self):
        texts = []
        for upload in self.cleaned_data["files"]:
            if upload.size > MAX_CONTENT_FILE_BYTES:
                raise forms.ValidationError(f"{upload.name} is too large.")
            try:
                texts.append((upload.name, upload.read().decode("utf-8")))
            except UnicodeDecodeError as exc:
                raise forms.ValidationError(f"{upload.name} is not UTF-8 text.") from exc
        return texts


@admin.register(PageContent)
class PageContentAdmin(ModelAdmin):
    """Words on the public pages. Changes show on the site within a minute."""

    form = PageContentForm
    list_display = ("page", "key", "short_value", "format", "updated_at")
    list_filter = ("page", "format")
    search_fields = ("key", "value")
    ordering = ("page", "key")
    actions_list = ["load_site_content"]

    def has_load_permission(self, request):
        return request.user.is_superuser

    @action(description="Load site content", icon="upload", permissions=["load"])
    def load_site_content(self, request):
        return redirect("admin:pages_load_content")

    def get_urls(self):
        extra = [
            path("load/", self.admin_site.admin_view(self.load_view), name="pages_load_content")
        ]
        return extra + super().get_urls()

    def load_view(self, request):
        """Superusers: upload the YAML drafts and load them, dry run first.

        The files never need to be in the repository, which keeps the
        organisation's name out of it.
        """
        if not request.user.is_superuser:
            raise PermissionDenied
        form = LoadContentForm(*((request.POST, request.FILES) if request.method == "POST" else ()))
        report = error = None
        committed = False
        if request.method == "POST" and form.is_valid():
            try:
                contents = parse_texts(form.cleaned_data["files"])
                report = load_guarded(
                    contents,
                    commit=form.cleaned_data["commit"],
                    allow_draft=form.cleaned_data["allow_draft"],
                    actor=request.user,
                )
                committed = form.cleaned_data["commit"]
            except ContentError as exc:
                error = f"{exc} Nothing was written."
        context = {
            **self.admin_site.each_context(request),
            "title": "Load site content",
            "opts": self.model._meta,
            "form": form,
            "report": list(report.lines()) if report else None,
            "committed": committed,
            "error": error,
        }
        return TemplateResponse(request, "admin/pages/load_content.html", context)

    @admin.display(description="Text")
    def short_value(self, obj):
        return obj.value if len(obj.value) <= 80 else f"{obj.value[:77]}..."


@admin.register(Redirect)
class RedirectAdmin(ModelAdmin):
    list_display = ("old_path", "new_path", "updated_at")
    search_fields = ("old_path", "new_path")
