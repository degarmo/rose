from rest_framework import serializers

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
        if not obj.hero_image_is_displayable:
            return None
        request = self.context.get("request")
        url = obj.hero_image.url
        return {
            "url": request.build_absolute_uri(url) if request else url,
            "alt": obj.hero_image_alt,
        }


class OpportunityDetailSerializer(OpportunitySerializer):
    class Meta(OpportunitySerializer.Meta):
        fields = OpportunitySerializer.Meta.fields + ["body"]
