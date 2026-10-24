from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.core.admin_display import ButtonFields, image_preview
from apps.core.samples import SampleBadgeAdmin

from .models import Opportunity


@admin.register(Opportunity)
class OpportunityAdmin(SampleBadgeAdmin, ButtonFields, ModelAdmin):
    hero_image_preview = image_preview("hero_image")
    readonly_fields = ("hero_image_preview",)
    list_display = (
        "title",
        "category",
        "level",
        "starts_at",
        "members_only",
        "is_published",
        "sort_order",
    )
    list_editable = ("is_published", "sort_order")
    list_filter = ("is_published", "members_only", "category", "level")
    search_fields = ("title", "summary", "body")
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        (None, {"fields": ("title", "slug", "summary", "body")}),
        ("Details", {"fields": ("category", "level", "starts_at", "location_label")}),
        ("Button", {"fields": ("cta_label", "cta_url")}),
        (
            "Image",
            {
                "fields": (
                    "hero_image_preview",
                    "hero_image",
                    "hero_image_alt",
                    "hero_image_faces_visible",
                    "hero_image_consent_confirmed",
                )
            },
        ),
        ("Publishing", {"fields": ("is_published", "members_only", "sort_order")}),
    )
