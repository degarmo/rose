from rest_framework import serializers

from apps.core.consent_images import consent_image_payload

from .content import with_club_name
from .models import FAQItem, SiteSettings, SocialLink, StaffProfile


class SocialLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialLink
        fields = ["label", "url"]


class SiteSettingsSerializer(serializers.ModelSerializer):
    social_links = SocialLinkSerializer(many=True, read_only=True)

    class Meta:
        model = SiteSettings
        fields = [
            "tagline",
            "hours_text",
            "address_text",
            "directions_text",
            "phone_text",
            "contact_email",
            "quick_exit_url",
            "nonprofit_status_text",
            "social_links",
        ]


class FAQItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQItem
        fields = ["id", "question", "answer"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Questions and answers may name the club through tokens, like page copy.
        return {key: with_club_name(value) if key != "id" else value for key, value in data.items()}


class StaffProfileSerializer(serializers.ModelSerializer):
    """A display name, a role and a few words. Never the account behind it."""

    photo = serializers.SerializerMethodField()

    class Meta:
        model = StaffProfile
        fields = ["slug", "display_name", "role_title", "bio", "photo"]

    def get_photo(self, obj):
        return consent_image_payload(obj, "photo", self.context.get("request"))
