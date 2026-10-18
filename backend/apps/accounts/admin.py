from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone

from .forms import UserChangeForm, UserCreationForm
from .models import Profile, User


def record_grant(profile, actor):
    """Stamp who granted feed access, and when. Revoking clears the stamp."""
    if profile.feed_access_granted and profile.feed_access_granted_at is None:
        profile.feed_access_granted_by = actor
        profile.feed_access_granted_at = timezone.now()
    elif not profile.feed_access_granted:
        profile.feed_access_granted_by = None
        profile.feed_access_granted_at = None


PROFILE_READONLY = (
    "feed_access_granted_by",
    "feed_access_granted_at",
    "joined_feed_at",
    "feed_status_changed_at",
    "participates_in_feed",
)


class ProfileInline(admin.StackedInline):
    model = Profile
    fk_name = "user"
    can_delete = False
    fields = (
        "feed_access_granted",
        "feed_access_granted_by",
        "feed_access_granted_at",
        "participates_in_feed",
        "joined_feed_at",
        "feed_status_changed_at",
        "visibility",
    )
    readonly_fields = PROFILE_READONLY


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    inlines = [ProfileInline]

    def save_formset(self, request, form, formset, change):
        if formset.model is Profile:
            for inline_form in formset.forms:
                if inline_form.has_changed():
                    record_grant(inline_form.instance, request.user)
        super().save_formset(request, form, formset, change)

    ordering = ("display_name",)
    list_display = ("display_name", "email", "is_active", "is_staff", "date_joined")
    list_filter = ("is_active", "is_staff", "profile__participates_in_feed")
    search_fields = ("display_name", "email", "legal_name")
    fieldsets = (
        (None, {"fields": ("email", "display_name", "password")}),
        ("Private details", {"fields": ("legal_name", "phone")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "display_name", "password1", "password2"),
            },
        ),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "feed_access_granted",
        "participates_in_feed",
        "feed_suspended_until",
        "banned",
        "updated_at",
    )
    list_filter = ("feed_access_granted", "participates_in_feed", "hide_from_directory")
    search_fields = ("user__display_name",)
    actions = ["grant_feed_access", "revoke_feed_access"]
    # The avatar lives in private storage and has no URL; staff review it in moderation.
    fields = (
        "user",
        "feed_access_granted",
        "feed_access_granted_by",
        "feed_access_granted_at",
        "participates_in_feed",
        "joined_feed_at",
        "feed_status_changed_at",
        "bio",
        "hide_from_directory",
        "always_show_sensitive",
        "hidden_by_report",
        "feed_suspended_until",
        "feed_banned_at",
        "posting_cooldown_until",
        "visibility",
        "updated_at",
    )
    readonly_fields = (*PROFILE_READONLY, "user", "updated_at")

    def has_add_permission(self, request):
        return False

    @admin.display(boolean=True, description="Banned")
    def banned(self, obj):
        return obj.is_feed_banned

    def save_model(self, request, obj, form, change):
        record_grant(obj, request.user)
        super().save_model(request, obj, form, change)

    @admin.action(description="Grant member feed access")
    def grant_feed_access(self, request, queryset):
        for profile in queryset.filter(feed_access_granted=False):
            profile.feed_access_granted = True
            record_grant(profile, request.user)
            profile.save()

    @admin.action(description="Revoke member feed access")
    def revoke_feed_access(self, request, queryset):
        for profile in queryset.filter(feed_access_granted=True):
            profile.feed_access_granted = False
            record_grant(profile, request.user)
            profile.save()
