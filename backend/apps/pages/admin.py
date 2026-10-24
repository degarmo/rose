import math

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.views.decorators.http import require_POST
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display
from unfold.widgets import UnfoldAdminDecimalFieldWidget, UnfoldAdminTextareaWidget

from apps.core.admin_display import image_preview
from apps.core.models import AuditLog, audit
from apps.core.samples import SampleBadgeAdmin
from apps.safety.roles import STAFF, has_role

from .models import (
    FAQItem,
    PageContent,
    Redirect,
    SiteImage,
    SiteImageVersion,
    SiteSettings,
    SocialLink,
    StaffProfile,
)
from .site_content import ContentError, load_guarded, parse_texts

MAX_CONTENT_FILE_BYTES = 200_000


class SocialLinkInline(TabularInline):
    model = SocialLink
    extra = 0


@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
    inlines = [SocialLinkInline]
    readonly_fields = ("updated_at", "age_verification")
    fieldsets = (
        (
            "Member feed",
            {
                "fields": ("age_verification",),
                "description": "Changed on its own page: admins only, with a reason and a "
                "fresh code from your authenticator app. Every change is logged.",
            },
        ),
        (
            None,
            {
                "fields": (
                    "site_display_name",
                    "site_short_name",
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

    @display(description="Age verification for the member feed")
    def age_verification(self, obj):
        url = reverse("admin:pages_sitesettings_age_verification")
        state = "On" if obj.require_age_verification_for_feed else "Off"
        return format_html(
            '<span class="rose-chip {}">{}</span> <a class="rose-link" href="{}">Open</a>',
            "rose-chip-open" if obj.require_age_verification_for_feed else "rose-chip-wait",
            state,
            url,
        )

    def get_urls(self):
        return [
            path(
                "age-verification/",
                self.admin_site.admin_view(self.age_verification_view),
                name="pages_sitesettings_age_verification",
            ),
            *super().get_urls(),
        ]

    def age_verification_view(self, request):
        """The confirmation page for the member feed's age check: what changes, a reason and
        a fresh two-step code. Everyone on the team who can open site settings sees it; only
        admins can change it (apps.memberships.age)."""
        from apps.core.models import AuditLog
        from apps.memberships.age import (
            AgeCheckError,
            can_change_setting,
            set_age_check_required,
            setting_summary,
        )

        if not (request.user.has_perm("pages.view_sitesettings") or request.user.is_staff):
            raise PermissionDenied
        error = ""
        if request.method == "POST":
            if not can_change_setting(request.user):
                raise PermissionDenied
            try:
                set_age_check_required(
                    request.user,
                    request.POST.get("required") == "on",
                    request.POST.get("reason", ""),
                    request.POST.get("code", ""),
                )
            except AgeCheckError as exc:
                error = str(exc)
            else:
                self.message_user(request, "Age verification for the member feed was changed.")
                return redirect(reverse("admin:pages_sitesettings_age_verification"))
        context = {
            **self.admin_site.each_context(request),
            "title": "Age verification for the member feed",
            "opts": self.model._meta,
            "setting": setting_summary(request.user),
            "can_change": can_change_setting(request.user),
            "changes": AuditLog.objects.filter(
                category=AuditLog.Category.SETTINGS, action__startswith="age_verification"
            )[:5],
            "error": error,
            "reason": request.POST.get("reason", "") if error else "",
        }
        return TemplateResponse(request, "admin/pages/age_verification.html", context)

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        settings_obj = SiteSettings.load()
        return redirect(reverse("admin:pages_sitesettings_change", args=[settings_obj.pk]))


@admin.register(FAQItem)
class FAQItemAdmin(SampleBadgeAdmin, ModelAdmin):
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
    overwrite = forms.BooleanField(
        required=False,
        label="Replace copy edited here in the admin",
        help_text="Left unticked, copy staff have changed here stays as it is.",
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
                    overwrite=form.cleaned_data["overwrite"],
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

    def save_model(self, request, obj, form, change):
        # Staff wrote these words: a later load_site_content keeps them unless told otherwise.
        if form.has_changed():
            obj.edited_in_admin = True
        super().save_model(request, obj, form, change)

    @admin.display(description="Text")
    def short_value(self, obj):
        return obj.value if len(obj.value) <= 80 else f"{obj.value[:77]}..."


@admin.register(Redirect)
class RedirectAdmin(ModelAdmin):
    list_display = ("old_path", "new_path", "updated_at")
    search_fields = ("old_path", "new_path")


# Page images


def edits_page_images(user):
    """Staff and Admin change page images; Moderators do not."""
    return has_role(user, STAFF)


def ratio_value(ratio):
    width, _, height = ratio.partition("/")
    return float(width) / float(height)


# A picture this much wider or taller than its slot loses a lot to cropping.
FAR_OFF_RATIO = 1.35


def size_warnings(slot):
    """Worth knowing, never blocking: too small, or a very different shape."""
    if not slot.image or not slot.image_width:
        return []
    warnings = []
    if slot.image_width < slot.recommended_width:
        warnings.append(
            f"{slot.label}: the picture is {slot.image_width} pixels wide, smaller than the "
            f"recommended {slot.recommended_width}. It may look soft on large screens."
        )
    shape = slot.image_width / slot.image_height
    if abs(math.log(shape / ratio_value(slot.aspect_ratio))) > math.log(FAR_OFF_RATIO):
        warnings.append(
            f"{slot.label}: the picture's shape is far from {slot.aspect_ratio}, so much of it "
            "will be cropped. Check the focal point and the previews."
        )
    return warnings


class SiteImageForm(forms.ModelForm):
    class Meta:
        model = SiteImage
        fields = [
            "image",
            "image_alt",
            "image_faces_visible",
            "image_consent_confirmed",
            "credit",
            "focal_x",
            "focal_y",
        ]
        labels = {
            "image": "Picture",
            "image_alt": "Alt text",
            "image_faces_visible": "Faces visible",
            "image_consent_confirmed": "Consent confirmed",
            "focal_x": "Focal point, across (0 to 1)",
            "focal_y": "Focal point, down (0 to 1)",
        }
        widgets = {
            "focal_x": UnfoldAdminDecimalFieldWidget(
                attrs={"step": "0.01", "min": "0", "max": "1"}
            ),
            "focal_y": UnfoldAdminDecimalFieldWidget(
                attrs={"step": "0.01", "min": "0", "max": "1"}
            ),
        }


@admin.register(SiteImage)
class SiteImageAdmin(ModelAdmin):
    """Content > Page images: every fixed picture on the public pages, page by page."""

    form = SiteImageForm
    readonly_fields = ("about_slot", "focal_point_picker", "history", "last_updated")
    fieldsets = (
        (None, {"fields": ("about_slot",)}),
        (
            "Picture",
            {
                "fields": (
                    "image",
                    "image_alt",
                    "image_faces_visible",
                    "image_consent_confirmed",
                    "credit",
                ),
                "description": "Choose a new file to replace the picture, or clear it to "
                "go back to the page's texture. Metadata is stripped on upload.",
            },
        ),
        ("Cropping", {"fields": ("focal_point_picker", "focal_x", "focal_y")}),
        ("History", {"fields": ("history", "last_updated")}),
    )

    class Media:
        js = ("pages/focal-point.js",)

    # Who may do what

    def has_module_permission(self, request):
        return edits_page_images(request.user)

    def has_view_permission(self, request, obj=None):
        return edits_page_images(request.user)

    def has_change_permission(self, request, obj=None):
        return edits_page_images(request.user)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # The page-by-page list

    def changelist_view(self, request, extra_context=None):
        if not edits_page_images(request.user):
            raise PermissionDenied
        slots = SiteImage.objects.select_related("updated_by").prefetch_related("versions")
        open_page = request.GET.get("page", SiteImage.Page.HOME)
        # The link to a page's words only for those who may open Page copy.
        sees_copy = request.user.has_perm("pages.view_pagecontent")
        groups = []
        for page, name in SiteImage.Page.choices:
            rows = [slot for slot in slots if slot.page == page]
            if rows:
                groups.append(
                    {
                        "page": page,
                        "name": name,
                        "open": page == open_page,
                        "slots": rows,
                        "copy_url": reverse("admin:pages_pagecontent_changelist")
                        + f"?page__exact={page}"
                        if sees_copy
                        else "",
                        "site_url": rows[0].get_absolute_url(),
                    }
                )
        context = {
            **self.admin_site.each_context(request),
            "title": "Page images",
            "opts": self.model._meta,
            "groups": groups,
        }
        return TemplateResponse(request, "admin/pages/siteimage/page_images.html", context)

    # Remove and restore

    def get_urls(self):
        return [
            path(
                "<int:pk>/remove/",
                self.admin_site.admin_view(require_POST(self.remove_view)),
                name="pages_siteimage_remove",
            ),
            path(
                "<int:pk>/restore/<int:version>/",
                self.admin_site.admin_view(require_POST(self.restore_view)),
                name="pages_siteimage_restore",
            ),
            path(
                "<int:pk>/restore-previous/",
                self.admin_site.admin_view(require_POST(self.restore_previous_view)),
                name="pages_siteimage_restore_previous",
            ),
            *super().get_urls(),
        ]

    def _slot(self, request, pk):
        if not edits_page_images(request.user):
            raise PermissionDenied
        return get_object_or_404(SiteImage, pk=pk)

    def _back(self, request, slot):
        if request.POST.get("next") == "change":
            return redirect(reverse("admin:pages_siteimage_change", args=[slot.pk]))
        return redirect(reverse("admin:pages_siteimage_changelist") + f"?page={slot.page}")

    def remove_view(self, request, pk):
        slot = self._slot(request, pk)
        if slot.image:
            slot.image = ""
            slot.updated_by = request.user
            slot.save()
            self._audit("site_image_removed", request.user, slot)
            self.message_user(request, f"{slot.label}: removed. The page shows its texture.")
        return self._back(request, slot)

    def restore_view(self, request, pk, version):
        slot = self._slot(request, pk)
        chosen = get_object_or_404(SiteImageVersion, pk=version, site_image=slot)
        self._restore(request, slot, chosen)
        return self._back(request, slot)

    def restore_previous_view(self, request, pk):
        slot = self._slot(request, pk)
        chosen = slot.versions.first()
        if chosen is None:
            self.message_user(
                request, f"{slot.label}: there is no previous picture.", messages.WARNING
            )
        else:
            self._restore(request, slot, chosen)
        return self._back(request, slot)

    def _restore(self, request, slot, version):
        with transaction.atomic():
            slot.restore(version, request.user)
            self._audit("site_image_restored", request.user, slot)
        self.message_user(request, f"{slot.label}: the previous picture is back.")
        for warning in size_warnings(slot):
            self.message_user(request, warning, messages.WARNING)

    # Saving

    def save_model(self, request, obj, form, change):
        before = SiteImage.objects.filter(pk=obj.pk).values_list("image", flat=True).first()
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        if not obj.image and before:
            action = "site_image_removed"
        elif obj.image and obj.image.name != before:
            action = "site_image_replaced"
        else:
            action = "site_image_edited"
        self._audit(action, request.user, obj)
        for warning in size_warnings(obj):
            self.message_user(request, warning, messages.WARNING)

    def _audit(self, action, actor, slot):
        audit(
            AuditLog.Category.CONTENT, action, actor, slot.label, "site_image", target_ref=slot.slot
        )

    # The change page's read-only parts

    @admin.display(description="Slot")
    def about_slot(self, obj):
        return render_to_string("admin/pages/siteimage/about_slot.html", {"slot": obj})

    @admin.display(description="Focal point")
    def focal_point_picker(self, obj):
        return render_to_string("admin/pages/siteimage/focal_point.html", {"slot": obj})

    @admin.display(description="Previous pictures")
    def history(self, obj):
        return render_to_string(
            "admin/pages/siteimage/history.html",
            {"slot": obj, "versions": obj.versions.select_related("replaced_by")},
        )

    @admin.display(description="Last updated")
    def last_updated(self, obj):
        who = obj.updated_by.display_name if obj.updated_by else "the site's set-up"
        return format_html("{} by {}", f"{obj.updated_at:%d %b %Y, %H:%M}", who)
