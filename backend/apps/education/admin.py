from django.contrib import admin

from .models import Opportunity


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "level", "starts_at", "is_published", "sort_order")
    list_editable = ("is_published", "sort_order")
    list_filter = ("is_published", "category", "level")
    search_fields = ("title", "summary", "body")
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        (None, {"fields": ("title", "slug", "summary", "body")}),
        ("Details", {"fields": ("category", "level", "starts_at", "location_label")}),
        ("Call to action", {"fields": ("cta_label", "cta_url")}),
        (
            "Image",
            {
                "fields": (
                    "hero_image",
                    "hero_image_alt",
                    "hero_image_faces_visible",
                    "hero_image_consent_confirmed",
                )
            },
        ),
        ("Publishing", {"fields": ("is_published", "sort_order")}),
    )
