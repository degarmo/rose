from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse

from .models import FAQItem, SiteSettings, SocialLink


class SocialLinkInline(admin.TabularInline):
    model = SocialLink
    extra = 0


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    inlines = [SocialLinkInline]
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        settings_obj = SiteSettings.load()
        return redirect(reverse("admin:pages_sitesettings_change", args=[settings_obj.pk]))


@admin.register(FAQItem)
class FAQItemAdmin(admin.ModelAdmin):
    list_display = ("question", "sort_order", "is_published")
    list_editable = ("sort_order", "is_published")
    list_filter = ("is_published",)
    search_fields = ("question", "answer")
