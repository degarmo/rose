from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import UserChangeForm, UserCreationForm
from .models import Profile, User


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    fields = ("participates_in_feed", "visibility", "feed_status_changed_at")
    readonly_fields = ("feed_status_changed_at",)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    inlines = [ProfileInline]
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
    list_display = ("user", "participates_in_feed", "visibility", "updated_at")
    list_filter = ("participates_in_feed", "visibility")
    search_fields = ("user__display_name",)
    readonly_fields = ("feed_status_changed_at", "updated_at")
