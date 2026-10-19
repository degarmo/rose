from rest_framework import serializers

from .models import Availability, Interest, VolunteerSignup


class VolunteerSignupSerializer(serializers.ModelSerializer):
    """Accepts a signup. The view answers with a fixed message, never the record."""

    # Honeypot: hidden from people, filled in by most bots.
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)
    interests = serializers.ListField(
        child=serializers.ChoiceField(choices=Interest.choices), allow_empty=False, max_length=8
    )
    availability = serializers.ListField(
        child=serializers.ChoiceField(choices=Availability.choices),
        allow_empty=False,
        max_length=4,
    )

    class Meta:
        model = VolunteerSignup
        fields = [
            "contact_name",
            "contact_email",
            "interests",
            "availability",
            "experience_note",
            "website",
        ]
        extra_kwargs = {
            "contact_name": {"max_length": 120},
            "experience_note": {"max_length": 2000},
        }

    def validate_contact_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Please tell us what to call you.")
        return value

    def validate_interests(self, value):
        return list(dict.fromkeys(value))

    def validate_availability(self, value):
        return list(dict.fromkeys(value))

    def validate_experience_note(self, value):
        return value.strip()

    def create(self, validated_data):
        validated_data.pop("website", None)
        return super().create(validated_data)
