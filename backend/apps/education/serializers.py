from rest_framework import serializers

from apps.core.consent_images import consent_image_payload

from .models import Opportunity


class OpportunitySerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    level_label = serializers.CharField(source="get_level_display", read_only=True)
    hero_image = serializers.SerializerMethodField()

    class Meta:
        model = Opportunity
        fields = [
            "id",
            "title",
            "slug",
            "summary",
            "category",
            "category_label",
            "level",
            "level_label",
            "starts_at",
            "location_label",
            "cta_label",
            "cta_url",
            "hero_image",
        ]

    def get_hero_image(self, obj):
        """Withhold any image showing faces without confirmed consent."""
        return consent_image_payload(obj, "hero_image", self.context.get("request"))


class OpportunityDetailSerializer(OpportunitySerializer):
    class Meta(OpportunitySerializer.Meta):
        fields = OpportunitySerializer.Meta.fields + ["body"]
