"""Serializers that describe people.

PublicUserSerializer is the only one allowed to describe a person to anyone
else, and it exposes the display name and nothing more. AccountSerializer is
marked `self_only` and is returned only for the signed-in person's own
account. tests/test_privacy.py enforces both rules for every serializer.
"""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.urls import reverse
from rest_framework import serializers

from .models import User, display_name_validator


class PublicUserSerializer(serializers.ModelSerializer):
    """For anything a visitor or another member can see, e.g. an author byline."""

    class Meta:
        model = User
        fields = ["display_name"]
        read_only_fields = fields


class AccountSerializer(serializers.ModelSerializer):
    """The signed-in person's own details. Only ever returned for request.user."""

    self_only = True
    email_verified = serializers.BooleanField(read_only=True)
    has_membership = serializers.SerializerMethodField()
    staff_guide_url = serializers.SerializerMethodField()
    feed_access = serializers.SerializerMethodField()
    feed_controls = serializers.SerializerMethodField()
    member_app = serializers.SerializerMethodField()
    age_check = serializers.SerializerMethodField()
    staff = serializers.SerializerMethodField()
    calendar_details = serializers.BooleanField(source="profile.calendar_details", read_only=True)
    unread_notices = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "display_name",
            "email",
            "email_verified",
            "has_membership",
            "staff_guide_url",
            "feed_access",
            "feed_controls",
            "member_app",
            "age_check",
            "staff",
            "calendar_details",
            "unread_notices",
            "appearance",
        ]
        read_only_fields = ["email", "email_verified", "appearance"]

    def get_unread_notices(self, user):
        """New decisions about this account, or updates to them, not yet seen in Settings."""
        from apps.safety.services import unread_notices

        return unread_notices(user)

    def get_age_check(self, user):
        """The in-person age check the member feed needs, while the club has it switched on.
        `needed` shows the verify card (on Home and in Settings) to anyone it would unlock
        something for: feed access waiting for it, or a membership that is open or on its
        way. `notice` says the check was switched on after they had the feed. With the check
        switched off, nothing is needed and the card is hidden."""
        from apps.feed.access import awaiting_age_check
        from apps.memberships.access import age_check_required, is_age_verified
        from apps.memberships.models import Membership

        verified = is_age_verified(user)
        needed = (
            age_check_required()
            and not verified
            and (
                awaiting_age_check(user)
                or Membership.objects.non_terminal().filter(user=user).exists()
            )
        )
        profile = getattr(user, "profile", None)
        return {
            "verified": verified,
            "needed": needed,
            "notice": bool(needed and profile and profile.age_check_notice_at),
        }

    def get_has_membership(self, user):
        return user.memberships.exists()

    def get_staff_guide_url(self, user):
        """Staff only, so the admin's address never reaches anyone else's browser."""
        return reverse("admin:staff_guide") if user.is_staff and user.is_active else None

    def get_feed_access(self, user):
        """Whether the member app opens for this person (the website shows "My feed")."""
        from apps.feed.access import can_view_feed

        return can_view_feed(user)

    def get_member_app(self, user):
        """Where the member app stands for this person: "open" (it opens now), "join" (it
        would after joining), "verify" (entitled, but waiting for the in-person age check),
        "paused" (a suspension or ban closes it) or None."""
        from django.conf import settings

        from apps.feed.access import (
            awaiting_age_check,
            can_join_feed,
            can_view_feed,
            has_feed_entitlement,
        )

        if not settings.FEED_ENABLED:
            return None
        if can_view_feed(user):
            return "open"
        if can_join_feed(user):
            return "join"
        if awaiting_age_check(user):
            return "verify"
        profile = user.profile
        if has_feed_entitlement(user) and (profile.is_feed_banned or profile.is_feed_suspended()):
            return "paused"
        return None

    def get_staff(self, user):
        """The team and door volunteers only: their role (none for a volunteer), whether they
        may use the door desk, and whether this session passed the two-step login the staff
        section needs (with where to do it if not)."""
        from urllib.parse import quote

        from django.conf import settings
        from django_otp.plugins.otp_totp.models import TOTPDevice

        from apps.core.preview import preview_active
        from apps.memberships.access import age_check_required
        from apps.memberships.age import can_change_setting
        from apps.memberships.desk import DESK_PERMISSION
        from apps.safety import roles

        role = roles.role_of(user)
        # Door volunteers hold the door desk permission without a team role.
        door_desk = bool(user.is_active and user.is_staff and user.has_perm(DESK_PERMISSION))
        if role is None and not door_desk:
            return None
        verified = roles.is_verified(user)
        door = f"{settings.SITE_URL}/members/staff/door" if door_desk else ""
        back = quote(door if role is None else f"{settings.SITE_URL}/members/staff", safe="")
        admin = settings.ADMIN_BASE_URL
        return {
            "role": role,
            "door_desk": door_desk,
            "verified": verified,
            "verify_url": None if verified else f"{admin}{reverse('admin:login')}?next={back}",
            # No authenticator yet: the two-step login starts by setting one up.
            "needs_enrollment": not TOTPDevice.objects.filter(user=user, confirmed=True).exists(),
            # The admin dashboard: where Staff and Admin land after logging in.
            "admin_url": f"{admin}{reverse('admin:index')}",
            # Off: the staff section shows a banner; admins open it to change the setting on
            # its admin page (a reason and a fresh two-step code).
            "age_check_required": age_check_required(),
            "can_change_age_check": can_change_setting(user),
            "age_check_url": f"{admin}{reverse('admin:pages_sitesettings_age_verification')}",
            # A staging preview: the staff section shows a thin strip saying so.
            "preview_mode": preview_active(),
        }

    def get_feed_controls(self, user):
        """Whether /account has feed controls for this person, so the page asks for them
        only when they exist (the endpoint answers 404 otherwise)."""
        from django.conf import settings

        from apps.feed.access import feed_account_visible

        return bool(settings.FEED_ENABLED and feed_account_visible(user))


def validate_display_name_available(value, exclude_pk=None):
    taken = User.objects.filter(display_name__iexact=value)
    if exclude_pk:
        taken = taken.exclude(pk=exclude_pk)
    if taken.exists():
        raise serializers.ValidationError("That display name is taken. Please choose another.")
    return value


class DisplayNameSerializer(serializers.Serializer):
    display_name = serializers.CharField(max_length=30, validators=[display_name_validator])

    def validate_display_name(self, value):
        return validate_display_name_available(value, exclude_pk=self.context["user"].pk)


class SessionUpdateSerializer(DisplayNameSerializer):
    """Changes to your own account from the session endpoint: either field, or both."""

    display_name = serializers.CharField(
        max_length=30, validators=[display_name_validator], required=False
    )
    appearance = serializers.ChoiceField(choices=User.Appearance.choices, required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Nothing to change.")
        return attrs


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    display_name = serializers.CharField(max_length=30, validators=[display_name_validator])
    password = serializers.CharField(write_only=True, max_length=256)

    def validate_email(self, value):
        return value.strip().lower()

    def validate_display_name(self, value):
        return validate_display_name_available(value)

    def validate(self, attrs):
        candidate = User(email=attrs["email"], display_name=attrs["display_name"])
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=256)


class TokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=512)


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)


class NewPasswordMixin:
    def validate_new_password(self, value):
        try:
            validate_password(value, user=self.context.get("user"))
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value


class PasswordResetConfirmSerializer(NewPasswordMixin, serializers.Serializer):
    uid = serializers.CharField(max_length=64)
    token = serializers.CharField(max_length=128)
    new_password = serializers.CharField(max_length=256)


class ChangePasswordSerializer(NewPasswordMixin, serializers.Serializer):
    current_password = serializers.CharField(max_length=256)
    new_password = serializers.CharField(max_length=256)

    def validate_current_password(self, value):
        if not self.context["user"].check_password(value):
            raise serializers.ValidationError("That is not your current password.")
        return value


class DeleteAccountSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=256)

    def validate_password(self, value):
        if not self.context["user"].check_password(value):
            raise serializers.ValidationError("That password is not correct.")
        return value
