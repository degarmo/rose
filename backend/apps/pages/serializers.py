from rest_framework import serializers

from .models import FAQItem, SiteSettings, SocialLink


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
            "contact_email",
            "quick_exit_url",
            "social_links",
        ]


class FAQItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQItem
        fields = ["id", "question", "answer"]
