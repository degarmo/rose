from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils import timezone
from django_otp.plugins.otp_static.admin import StaticDeviceAdmin as BaseStaticDeviceAdmin
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.admin import TOTPDeviceAdmin as BaseTOTPDeviceAdmin
from django_otp.plugins.otp_totp.models import TOTPDevice
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.decorators import display
from unfold.forms import AdminPasswordChangeForm

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


class ProfileInline(StackedInline):
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
class UserAdmin(BaseUserAdmin, ModelAdmin):
    """Members: everyone with an account. The legal name and phone stay private."""

    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    inlines = [ProfileInline]

    def save_formset(self, request, form, formset, change):
        if formset.model is Profile:
            for inline_form in formset.forms:
                if inline_form.has_changed():
                    record_grant(inline_form.instance, request.user)
        super().save_formset(request, form, formset, change)

    ordering = ("display_name",)
    list_display = ("display_name", "email", "account_status", "team", "in_feed", "date_joined")
    list_filter = ("is_active", "is_staff", "profile__participates_in_feed", "groups")
    search_fields = ("display_name", "email", "legal_name")
    # Long page: one tab per part (Unfold shows fieldsets with the "tab" class as tabs).
    fieldsets = (
        (
            "Account",
            {
                "classes": ["tab"],
                "fields": ("email", "display_name", "password"),
                "description": "The display name is the only name other members ever see.",
            },
        ),
        (
            "Private details",
            {
                "classes": ["tab"],
                "fields": ("legal_name", "phone"),
                "description": "Never shown to members or the public. Leave empty unless needed.",
            },
        ),
        (
            "Permissions",
            {
                "classes": ["tab"],
                "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
                "description": "Staff can sign in to the admin. Roles (Moderator, Staff, Admin) "
                "are the groups; manage them in the staff section's Team page.",
            },
        ),
        ("Dates", {"classes": ["tab"], "fields": ("last_login", "date_joined")}),
    )

    @display(description="Status", label={"Active": "success", "Inactive": "danger"})
    def account_status(self, obj):
        return "Active" if obj.is_active else "Inactive"

    @display(description="Team", label=True)
    def team(self, obj):
        if obj.is_superuser:
            return "Owner"
        roles = ", ".join(group.name for group in obj.groups.all())
        return roles or ("Staff" if obj.is_staff else "")

    @display(description="In the feed", boolean=True)
    def in_feed(self, obj):
        return obj.profile.participates_in_feed

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("profile").prefetch_related("groups")

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "display_name", "password1", "password2"),
            },
        ),
    )


admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    """Team and roles: the Moderator, Staff and Admin roles, and the door desk group."""

    list_display = ("name", "members")

    @display(description="People")
    def members(self, obj):
        return obj.user_set.count()


# The two-step login's authenticators and backup codes, in the admin's look (django-otp
# registers them with Django's own classes).
admin.site.unregister(TOTPDevice)
admin.site.unregister(StaticDevice)


@admin.register(TOTPDevice)
class TOTPDeviceAdmin(BaseTOTPDeviceAdmin, ModelAdmin):
    pass


class StaticTokenInline(TabularInline):
    model = StaticToken
    extra = 0


@admin.register(StaticDevice)
class StaticDeviceAdmin(BaseStaticDeviceAdmin, ModelAdmin):
    inlines = [StaticTokenInline]


@admin.register(Profile)
class ProfileAdmin(ModelAdmin):
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

    @display(boolean=True, description="Banned")
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
