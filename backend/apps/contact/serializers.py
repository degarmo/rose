import re

from rest_framework import serializers

from .models import ContactMessage

PHONE_PATTERN = re.compile(r"^[0-9+().\-\s]{7,32}$")


class ContactMessageSerializer(serializers.ModelSerializer):
    # Honeypot: hidden from people, filled in by most bots.
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = ContactMessage
        fields = ["name", "email", "phone", "topic", "message", "website"]
        extra_kwargs = {
            "name": {"max_length": 120},
            "message": {"max_length": 5000},
        }

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Please tell us what to call you.")
        return value

    def validate_phone(self, value):
        value = value.strip()
        if value and not PHONE_PATTERN.match(value):
            raise serializers.ValidationError("Enter a valid phone number, or leave it blank.")
        return value

    def validate_message(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError("Please write a little more so we can help.")
        return value

    def create(self, validated_data):
        validated_data.pop("website", None)
        return super().create(validated_data)
