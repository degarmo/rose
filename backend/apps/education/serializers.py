from rest_framework import serializers

from apps.core.consent_images import consent_image_payload
from apps.memberships.access import MEMBERS_EDUCATION, entitlements

from .models import Opportunity


def unlocking_tiers():
    from apps.memberships.join import offered_tiers

    return [tier.name for tier in offered_tiers().filter(grants_members_education=True)]


class OpportunitySerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    level_label = serializers.CharField(source="get_level_display", read_only=True)
    hero_image = serializers.SerializerMethodField()
    locked = serializers.SerializerMethodField()
    paywall = serializers.SerializerMethodField()

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
            "members_only",
            "locked",
            "paywall",
        ]

    def get_hero_image(self, obj):
        """Withhold any image showing faces without confirmed consent."""
        return consent_image_payload(obj, "hero_image", self.context.get("request"))

    def is_locked(self, obj):
        if not obj.members_only:
            return False
        if "locked_cache" not in self.context:
            request = self.context.get("request")
            user = request.user if request else None
            self.context["locked_cache"] = MEMBERS_EDUCATION not in entitlements(user)
        return self.context["locked_cache"]

    def get_locked(self, obj):
        return self.is_locked(obj)

    def get_paywall(self, obj):
        if not self.is_locked(obj):
            return None
        if "tiers_cache" not in self.context:
            self.context["tiers_cache"] = unlocking_tiers()
        return {
            "tiers": self.context["tiers_cache"],
            "benefit": "Members-only classes come with membership.",
        }

    def to_representation(self, obj):
        data = super().to_representation(obj)
        if self.is_locked(obj):
            # Enforced here, not only in the UI: locked content never leaves the server.
            data["cta_label"] = ""
            data["cta_url"] = ""
            if "body" in data:
                data["body"] = None
        return data


class OpportunityDetailSerializer(OpportunitySerializer):
    class Meta(OpportunitySerializer.Meta):
        fields = OpportunitySerializer.Meta.fields + ["body"]
