import re

from django.utils import timezone
from rest_framework import serializers

from .models import MAX_DURATION_HOURS, MAX_PARTY_SIZE, RentalInquiry

PHONE_PATTERN = re.compile(r"^[0-9+().\-\s]{7,32}$")
PHOTOSHOOT_ACKNOWLEDGEMENT = (
    "Please confirm everyone photographed will consent, and no other guests or members "
    "will appear in any image."
)


class RentalInquirySerializer(serializers.ModelSerializer):
    """Write-only in effect: the view answers with a fixed message, never the inquiry."""

    # Honeypot: hidden from people, filled in by most bots.
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)
    start_time = serializers.TimeField()
    duration_hours = serializers.IntegerField(min_value=1, max_value=MAX_DURATION_HOURS)
    party_size = serializers.IntegerField(min_value=1, max_value=MAX_PARTY_SIZE)

    class Meta:
        model = RentalInquiry
        fields = [
            "contact_name",
            "contact_email",
            "contact_phone",
            "type",
            "preferred_date",
            "alternate_date",
            "start_time",
            "duration_hours",
            "party_size",
            "notes",
            "photoshoot_acknowledged",
            "website",
        ]
        extra_kwargs = {
            "contact_name": {"required": True, "allow_blank": False, "max_length": 120},
            "contact_email": {"required": True, "allow_blank": False},
            "notes": {"max_length": 3000},
        }

    def validate_contact_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Please tell us what to call you.")
        return value

    def validate_contact_phone(self, value):
        value = value.strip()
        if value and not PHONE_PATTERN.match(value):
            raise serializers.ValidationError("Enter a valid phone number, or leave it blank.")
        return value

    def validate_preferred_date(self, value):
        if value <= timezone.localdate():
            raise serializers.ValidationError("Choose a date from tomorrow onwards.")
        return value

    def validate_notes(self, value):
        return value.strip()

    def validate(self, data):
        alternate = data.get("alternate_date")
        if alternate is not None:
            if alternate <= timezone.localdate():
                raise serializers.ValidationError(
                    {"alternate_date": "Choose a date from tomorrow onwards."}
                )
            if alternate == data.get("preferred_date"):
                raise serializers.ValidationError(
                    {"alternate_date": "Choose a different date from your first choice."}
                )
        if data.get("type") == RentalInquiry.Type.PHOTOSHOOT and not data.get(
            "photoshoot_acknowledged"
        ):
            raise serializers.ValidationError(
                {"photoshoot_acknowledged": PHOTOSHOOT_ACKNOWLEDGEMENT}
            )
        return data

    def create(self, validated_data):
        validated_data.pop("website", None)
        return super().create(validated_data)
