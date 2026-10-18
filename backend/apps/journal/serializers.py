from rest_framework import serializers

from apps.core.consent_images import consent_image_payload

from .models import Post


class PostSerializer(serializers.ModelSerializer):
    caption_html = serializers.CharField(read_only=True)
    author = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    event = serializers.SerializerMethodField()
    cta = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ["slug", "caption_html", "published_at", "author", "images", "event", "cta"]

    def get_author(self, obj):
        return obj.author.display_name if obj.author else None

    def get_images(self, obj):
        request = self.context.get("request")
        payloads = (consent_image_payload(image, "image", request) for image in obj.images.all())
        return [payload for payload in payloads if payload]

    def _event(self, obj):
        event = obj.event
        if event is None or not event.is_published:
            return None
        request = self.context.get("request")
        user = request.user if request else None
        if event.audience == event.Audience.ACCOUNT and not (user and user.is_authenticated):
            return None
        return event

    def get_event(self, obj):
        event = self._event(obj)
        if event is None:
            return None
        return {"slug": event.slug, "title": event.title, "starts_at": event.starts_at}

    def get_cta(self, obj):
        if self._event(obj) is not None or not (obj.cta_label and obj.cta_url):
            return None
        return {"label": obj.cta_label, "url": obj.cta_url}
