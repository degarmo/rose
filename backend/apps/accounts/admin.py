"""Members in the admin: the account list with its filters and bulk actions, each account's
page with the same actions in its top bar, its moderation history and its membership.

The actions themselves, and their rules (roles, at most 50 at once, staff accounts skipped,
fresh two-step codes), live in apps.accounts.member_actions; this module only shows them.
Nobody can delete an account here: "Erase account" replaces Django's delete and runs the
full erasure (apps.accounts.erasure).
"""

import csv

from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.db.models import Exists, OuterRef, Q, Subquery
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html_join
from django_otp.plugins.otp_static.admin import StaticDeviceAdmin as BaseStaticDeviceAdmin
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.admin import TOTPDeviceAdmin as BaseTOTPDeviceAdmin
from django_otp.plugins.otp_totp.models import TOTPDevice
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.decorators import action, display
from unfold.enums import ActionVariant
from unfold.forms import AdminPasswordChangeForm

from apps.safety import roles
from apps.safety.services import rule_suggestions

from . import member_actions
from .admin_forms import MemberActionForm
from .forms import UserChangeForm, UserCreationForm
from .models import Profile, User

PROFILE_READONLY = (
    "feed_access_granted",
    "feed_access_granted_by",
    "feed_access_granted_at",
    "joined_feed_at",
    "feed_status_changed_at",
    "participates_in_feed",
)


FEED_ACCESS_LABELS = {
    "Granted": "success",
    "Included": "success",
    "Granted, awaiting ID check": "warning",
    "Awaiting ID check": "warning",
}


def feed_access_status(obj):
    """A staff grant gives nothing until the person's own ID check is recorded."""
    from apps.feed.access import feed_access_label

    user = getattr(obj, "user", obj)
    return feed_access_label(user) or "-"


def sees_members(user):
    """The Members list and pages: the team (Moderator and up) and anyone given the view."""
    return user.has_perm("accounts.view_user") or roles.has_role(user, roles.MODERATOR)


def is_admin(user):
    """Email addresses, private details and editing accounts: the Admin role (superusers
    count as admins)."""
    return roles.has_role(user, roles.ADMIN)


class ProfileInline(StackedInline):
    """The feed grant is given and taken back with the page's actions, never edited here."""

    model = Profile
    fk_name = "user"
    can_delete = False
    fields = (
        "feed_access_granted",
        "feed_access",
        "feed_access_granted_by",
        "feed_access_granted_at",
        "participates_in_feed",
        "joined_feed_at",
        "feed_status_changed_at",
        "visibility",
    )
    readonly_fields = (*PROFILE_READONLY, "feed_access")

    @display(description="Feed access", label=FEED_ACCESS_LABELS)
    def feed_access(self, obj):
        return feed_access_status(obj)


# The list's filters


class YesNoFilter(admin.SimpleListFilter):
    """A Yes/No filter; `yes` is the Q for "Yes"."""

    yes = Q()

    def lookups(self, request, model_admin):
        return (("yes", "Yes"), ("no", "No"))

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(self.yes)
        if self.value() == "no":
            return queryset.exclude(self.yes)
        return queryset


class MembershipStatusFilter(admin.SimpleListFilter):
    title = "membership status"
    parameter_name = "membership"

    def lookups(self, request, model_admin):
        from apps.memberships.models import Membership

        return [*Membership.Status.choices, ("none", "No membership")]

    def queryset(self, request, queryset):
        if self.value() == "none":
            return queryset.filter(membership_status__isnull=True)
        if self.value():
            return queryset.filter(membership_status=self.value())
        return queryset


class TierFilter(admin.SimpleListFilter):
    title = "tier"
    parameter_name = "tier"

    def lookups(self, request, model_admin):
        from apps.memberships.models import Tier

        return [(str(tier.pk), tier.name) for tier in Tier.objects.all()]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(membership_tier=self.value())
        return queryset


class IdVerifiedFilter(YesNoFilter):
    title = "ID verified"
    parameter_name = "id_verified"
    yes = Q(id_verified=True)


class FeedMemberFilter(YesNoFilter):
    title = "feed member"
    parameter_name = "feed_member"
    yes = Q(profile__participates_in_feed=True)


class SuspendedFilter(YesNoFilter):
    title = "suspended"
    parameter_name = "suspended"

    def queryset(self, request, queryset):
        now = timezone.now()
        self.yes = Q(profile__feed_suspended_until__gt=now) | Q(
            profile__events_suspended_until__gt=now
        )
        return super().queryset(request, queryset)


class BannedFilter(YesNoFilter):
    title = "banned"
    parameter_name = "banned"
    yes = Q(profile__feed_banned_at__isnull=False)


class DeactivatedFilter(YesNoFilter):
    title = "deactivated"
    parameter_name = "deactivated"
    yes = Q(is_active=False)


class EmailVerifiedFilter(YesNoFilter):
    title = "email verified"
    parameter_name = "email_verified"
    yes = Q(email_verified_at__isnull=False)


class StaffRoleFilter(admin.SimpleListFilter):
    title = "staff role"
    parameter_name = "role"

    def lookups(self, request, model_admin):
        return [
            ("superuser", "Superuser"),
            *((role, roles.LABELS[role]) for role in reversed(roles.ROLES)),
            ("door", "Door volunteer"),
            ("none", "Not staff"),
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if value == "superuser":
            return queryset.filter(is_superuser=True)
        if value in roles.ROLES:
            return queryset.filter(groups__name=roles.GROUP_NAMES[value]).distinct()
        if value == "door":
            team = Group.objects.filter(name__in=roles.GROUP_NAMES.values())
            return queryset.filter(is_staff=True, is_superuser=False).exclude(groups__in=team)
        if value == "none":
            return queryset.filter(is_staff=False)
        return queryset


def _bulk_action(key):
    """A list action: opens the action's confirmation page for the ticked members."""
    spec = member_actions.ACTIONS[key]

    def bulk(modeladmin, request, queryset):
        return modeladmin.member_action(request, key, queryset)

    bulk.__name__ = f"bulk_{key}"
    return admin.action(description=spec.label)(bulk)


def _detail_action(key):
    """A button in an account's top bar: the same confirmation page, for that account."""
    spec = member_actions.ACTIONS[key]

    def detail(self, request, object_id):
        user = get_object_or_404(User, pk=object_id)
        return self.member_action(request, key, User.objects.filter(pk=user.pk), single=user)

    detail.__name__ = f"detail_{key}"
    variant = ActionVariant.DANGER if spec.danger else ActionVariant.DEFAULT
    return action(description=spec.label, url_path=f"actions/{key}", variant=variant)(detail)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    """Members: everyone with an account. The legal name, phone and email stay with admins."""

    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    inlines = [ProfileInline]

    ordering = ("display_name",)
    list_display = (
        "display_name",
        "email",
        "tier",
        "membership",
        "id_verified",
        "feed_member",
        "badges",
        "joined",
    )
    list_filter = (
        MembershipStatusFilter,
        TierFilter,
        IdVerifiedFilter,
        FeedMemberFilter,
        SuspendedFilter,
        BannedFilter,
        DeactivatedFilter,
        EmailVerifiedFilter,
        StaffRoleFilter,
    )
    search_help_text = "Display name, or email for admins."
    actions = [_bulk_action(key) for key in member_actions.ACTIONS]
    actions_detail = [
        {"title": title, "items": [f"detail_{key}" for key in keys]}
        for title, keys in member_actions.GROUPS.items()
    ]
    readonly_fields = ("moderation_history", "membership_record")

    # Long page: one tab per part (Unfold shows fieldsets with the "tab" class as tabs).
    HISTORY = ("Moderation history", {"classes": ["tab"], "fields": ("moderation_history",)})
    MEMBERSHIP = ("Membership", {"classes": ["tab"], "fields": ("membership_record",)})
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
        HISTORY,
        MEMBERSHIP,
    )
    # Moderators and Staff: no email, private details or permissions.
    team_fieldsets = (
        ("Account", {"classes": ["tab"], "fields": ("display_name", "date_joined")}),
        HISTORY,
        MEMBERSHIP,
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

    # Who may do what

    def has_module_permission(self, request):
        return sees_members(request.user)

    def has_view_permission(self, request, obj=None):
        return sees_members(request.user)

    def has_add_permission(self, request):
        return is_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return is_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        """Never: "Erase account" replaces delete, so no account goes without erasure."""
        return False

    def delete_model(self, request, obj):
        raise PermissionDenied

    def delete_queryset(self, request, queryset):
        raise PermissionDenied

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        for key in member_actions.ACTIONS:
            if not member_actions.allowed(request.user, key):
                actions.pop(f"bulk_{key}", None)
        return actions

    def get_actions_detail(self, request, object_id):
        return [
            item
            for item in super().get_actions_detail(request, object_id)
            if member_actions.allowed(request.user, item.method.__name__.removeprefix("detail_"))
        ]

    def get_list_display(self, request):
        if is_admin(request.user):
            return self.list_display
        return tuple(name for name in self.list_display if name != "email")

    def get_search_fields(self, request):
        return ("display_name", "email") if is_admin(request.user) else ("display_name",)

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        return self.fieldsets if is_admin(request.user) else self.team_fieldsets

    def get_object(self, request, object_id, from_field=None):
        obj = super().get_object(request, object_id, from_field)
        if obj is not None:
            # The history tab shows "Reveal" to admins only.
            obj.viewer = request.user
        return obj

    def get_queryset(self, request):
        from apps.memberships.models import IdCheck, Membership

        latest = Membership.objects.filter(user=OuterRef("pk")).order_by("-created_at")
        return (
            super()
            .get_queryset(request)
            .select_related("profile")
            .annotate(
                membership_status=Subquery(latest.values("status")[:1]),
                membership_tier=Subquery(latest.values("tier_id")[:1]),
                tier_name=Subquery(latest.values("tier__name")[:1]),
                id_verified=Exists(IdCheck.valid().filter(user=OuterRef("pk"))),
            )
        )

    # Columns

    @display(description="Tier", ordering="tier_name")
    def tier(self, obj):
        return obj.tier_name or "-"

    @display(
        description="Membership",
        ordering="membership_status",
        label={
            "Active": "success",
            "Grace period": "warning",
            "Waiting for payment": "warning",
            "Suspended": "danger",
            "Expired": "info",
            "Cancelled": "info",
        },
    )
    def membership(self, obj):
        from apps.memberships.models import Membership

        if obj.membership_status is None:
            return "-"
        return Membership.Status(obj.membership_status).label

    @display(description="ID verified", boolean=True, ordering="id_verified")
    def id_verified(self, obj):
        return obj.id_verified

    @display(description="Feed member", boolean=True, ordering="profile__participates_in_feed")
    def feed_member(self, obj):
        return obj.profile.participates_in_feed

    @display(description="Status")
    def badges(self, obj):
        profile = obj.profile
        now = timezone.now()
        badges = []
        if not obj.is_active:
            badges.append(("rose-chip-alert", "Deactivated"))
        if profile.feed_banned_at:
            badges.append(("rose-chip-alert", "Banned"))
        for name, until in (
            ("feed", profile.feed_suspended_until),
            ("events", profile.events_suspended_until),
        ):
            if until and until > now:
                when = timezone.localtime(until).strftime("%b %-d, %Y")
                badges.append(("rose-chip-wait", f"Suspended from {name} until {when}"))
        if not badges:
            badges.append(("", "Active"))
        return format_html_join(" ", '<span class="rose-chip {}">{}</span>', badges)

    @display(description="Joined", ordering="date_joined")
    def joined(self, obj):
        return timezone.localtime(obj.date_joined).strftime("%b\u00a0%Y")

    # The account page's tabs

    @display(description="Moderation history")
    def moderation_history(self, obj):
        from apps.feed.models import Report

        reports = Report.objects.filter(
            Q(post__author=obj) | Q(comment__author=obj) | Q(profile_user=obj)
        ).order_by("-created_at")
        viewer = getattr(obj, "viewer", None)
        return render_to_string(
            "admin/accounts/moderation_history.html",
            {
                "member": obj,
                "actions": obj.moderation_actions.select_related(
                    "created_by", "reversed_by", "appeal"
                ),
                "reports": reports,
                "can_reveal": bool(viewer and is_admin(viewer)),
                "staff_page": f"/members/staff/members/{obj.display_name}",
            },
        )

    @display(description="Membership")
    def membership_record(self, obj):
        return render_to_string(
            "admin/accounts/membership_record.html",
            {"memberships": obj.memberships.select_related("tier").order_by("-created_at")},
        )

    # Actions

    def get_urls(self):
        return [
            path(
                "<path:object_id>/reveal-reporter/<int:report_id>/",
                self.admin_site.admin_view(self.reveal_reporter_view),
                name="accounts_user_reveal_reporter",
            ),
            *super().get_urls(),
        ]

    def member_action(self, request, key, queryset, single=None):
        """The confirmation page for one action (GET, or the list's first POST), then the
        action itself and its summary."""
        spec = member_actions.ACTIONS[key]
        if not member_actions.allowed(request.user, key):
            raise PermissionDenied
        back = (
            reverse("admin:accounts_user_change", args=(single.pk,))
            if single
            else reverse("admin:accounts_user_changelist")
        )
        users = list(queryset.select_related("profile").order_by("display_name"))
        if len(users) > member_actions.MAX_USERS:
            self.message_user(
                request,
                f"{spec.label}: choose at most {member_actions.MAX_USERS} members at a time; "
                f"{len(users)} were selected.",
                messages.ERROR,
            )
            return redirect(back)

        applying = request.method == "POST" and "apply" in request.POST
        form = MemberActionForm(spec, request.POST if applying else None)
        if applying and form.is_valid():
            try:
                summary = member_actions.run(
                    request.user,
                    key,
                    users,
                    form.cleaned_data,
                    code=form.cleaned_data.get("code", ""),
                )
            except member_actions.ActionError as exc:
                form.add_error(None, str(exc))
            else:
                if spec.batch and summary.rows:
                    return self._csv(summary.rows)
                self._report(request, spec, summary)
                return redirect(back)

        skipped = [
            user.display_name
            for user in users
            if user.pk == request.user.pk or (spec.protected and member_actions.is_protected(user))
        ]
        context = {
            **self.admin_site.each_context(request),
            "title": spec.label,
            "opts": self.model._meta,
            "spec": spec,
            "form": form,
            "users": users,
            "skipped": skipped,
            "rules": rule_suggestions() if "rule" in spec.fields else [],
            "single": single,
            "back": back,
            "action_name": f"bulk_{key}",
            "selected": [user.pk for user in users],
            "checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        }
        return TemplateResponse(request, "admin/accounts/member_action.html", context)

    def _report(self, request, spec, summary):
        """The result: who it was done for and who was skipped, and why."""
        if summary.done:
            names = ", ".join(f"{name} ({note})" if note else name for name, note in summary.done)
            self.message_user(
                request, f"{spec.label}: done for {len(summary.done)}: {names}.", messages.SUCCESS
            )
        if summary.skipped:
            names = "; ".join(f"{name}: {why}" for name, why in summary.skipped)
            self.message_user(
                request,
                f"{spec.label}: skipped {len(summary.skipped)}: {names}.",
                messages.WARNING,
            )

    def _csv(self, rows):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="members-{timezone.localdate():%Y-%m-%d}.csv"'
        )
        response["Cache-Control"] = "private, no-store"
        csv.writer(response).writerows(rows)
        return response

    def reveal_reporter_view(self, request, object_id, report_id):
        """Who sent a report about this member: admins only, after confirming, and logged."""
        from apps.feed.models import Report
        from apps.safety.services import reveal_reporter

        if not is_admin(request.user):
            raise PermissionDenied
        member = get_object_or_404(User, pk=object_id)
        report = get_object_or_404(Report, pk=report_id)
        revealed = None
        if request.method == "POST":
            revealed = reveal_reporter(request.user, report)
        context = {
            **self.admin_site.each_context(request),
            "title": f"Who sent report {report.pk}",
            "opts": self.model._meta,
            "member": member,
            "report": report,
            "revealed": revealed,
            "back": reverse("admin:accounts_user_change", args=(member.pk,)),
        }
        return TemplateResponse(request, "admin/accounts/reveal_reporter.html", context)


for _key in member_actions.ACTIONS:
    setattr(UserAdmin, f"detail_{_key}", _detail_action(_key))


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
    """Profiles, to look up. Suspensions, bans and the feed grant change only through the
    Members page's actions, which log them and tell the member."""

    list_display = (
        "user",
        "feed_access",
        "participates_in_feed",
        "feed_suspended_until",
        "banned",
        "updated_at",
    )
    list_filter = ("feed_access_granted", "participates_in_feed", "hide_from_directory")
    search_fields = ("user__display_name",)
    # The avatar lives in private storage and has no URL; staff review it in moderation.
    fields = (
        "user",
        "feed_access_granted",
        "feed_access",
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
        "events_suspended_until",
        "feed_banned_at",
        "do_not_admit_at",
        "posting_cooldown_until",
        "visibility",
        "updated_at",
    )
    readonly_fields = (
        *PROFILE_READONLY,
        "user",
        "updated_at",
        "feed_access",
        "hidden_by_report",
        "feed_suspended_until",
        "events_suspended_until",
        "feed_banned_at",
        "do_not_admit_at",
        "posting_cooldown_until",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @display(description="Feed access", label=FEED_ACCESS_LABELS)
    def feed_access(self, obj):
        return feed_access_status(obj)

    @display(boolean=True, description="Banned")
    def banned(self, obj):
        return obj.is_feed_banned
