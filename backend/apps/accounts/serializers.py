"""Serializers that describe people.

PublicUserSerializer is the only one allowed to describe a person to anyone
else, and it exposes the display name and nothing more. AccountSerializer is
marked `self_only` and is returned only for the signed-in person's own
account. tests/test_privacy.py enforces both rules for every serializer.
"""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
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

    class Meta:
        model = User
        fields = ["display_name", "email", "email_verified"]
        read_only_fields = ["email", "email_verified"]


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
