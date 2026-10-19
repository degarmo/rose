from rest_framework import serializers

from apps.core.consent_images import consent_image_payload

from .access import (
    CLOSED,
    MEMBERS_ONLY,
    MONTHLY_LIMIT_REACHED,
    NOT_OPEN_YET,
    RESTRICTED,
    TIER_EVENT_NOT_INCLUDED,
    UNAVAILABLE,
    can_rsvp,
    plan_events_remaining,
    plan_party_limit,
)
from .models import MAX_PARTY_SIZE, RSVP, Event

UNAVAILABLE_STATES = {
    CLOSED,
    MEMBERS_ONLY,
    NOT_OPEN_YET,
    UNAVAILABLE,
    TIER_EVENT_NOT_INCLUDED,
    MONTHLY_LIMIT_REACHED,
    RESTRICTED,
}


def rsvp_state(user, event, mine=None):
    """What the RSVP panel should show this person. Never names anyone else.

    `plan_party_limit` and `events_remaining` are this person's own membership figures
    for members-only events (None when no plan applies or it is unlimited).
    """
    allowed, reason = can_rsvp(user, event, mine=mine)
    if mine and mine.status != RSVP.Status.CANCELLED:
        state = "going" if mine.status == RSVP.Status.GOING else "waitlisted"
    elif reason in UNAVAILABLE_STATES:
        state = reason
    elif event.is_full():
        state = "waitlist" if event.waitlist_enabled else "full"
    else:
        state = "open"
    return {
        "state": state,
        "can_rsvp": allowed,
        "reason": reason,
        "opens_at": event.rsvp_opens_at,
        "closes_at": event.rsvp_deadline,
        "max_party_size": event.max_party_size,
        "plan_party_limit": plan_party_limit(user, event),
        "events_remaining": plan_events_remaining(user, event),
        "mine": (
            {
                "status": mine.status,
                "party_size": mine.party_size,
                "note_to_hosts": mine.note_to_hosts,
            }
            if mine and mine.status != RSVP.Status.CANCELLED
            else None
        ),
    }


class EventSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    hero_image = serializers.SerializerMethodField()
    rsvp = serializers.SerializerMethodField()
    attendee_count = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id",
            "slug",
            "title",
            "summary",
            "category",
            "category_label",
            "audience",
            "starts_at",
            "ends_at",
            "location_label",
            "hero_image",
            "rsvp",
            "attendee_count",
        ]

    def get_hero_image(self, obj):
        return consent_image_payload(obj, "hero_image", self.context.get("request"))

    def get_rsvp(self, obj):
        request = self.context.get("request")
        user = request.user if request else None
        mine = self.context.get("my_rsvps", {}).get(obj.pk)
        return rsvp_state(user, obj, mine)

    def get_attendee_count(self, obj):
        """The only public signal about attendance, and only when staff turn it on."""
        return obj.going_count() if obj.show_attendee_count else None


class EventDetailSerializer(EventSerializer):
    opportunity = serializers.SerializerMethodField()

    class Meta(EventSerializer.Meta):
        fields = EventSerializer.Meta.fields + ["body", "opportunity"]

    def get_opportunity(self, obj):
        opportunity = obj.opportunity
        if opportunity is None or not opportunity.is_published:
            return None
        return {"slug": opportunity.slug, "title": opportunity.title}


class RSVPInputSerializer(serializers.Serializer):
    party_size = serializers.IntegerField(min_value=1, max_value=MAX_PARTY_SIZE, default=1)
    note_to_hosts = serializers.CharField(
        max_length=280, required=False, allow_blank=True, default=""
    )


class MyRSVPSerializer(serializers.ModelSerializer):
    """The signed-in person's own RSVPs. Never includes anyone else."""

    event = serializers.SerializerMethodField()

    class Meta:
        model = RSVP
        fields = ["status", "party_size", "note_to_hosts", "event"]

    def get_event(self, obj):
        return {
            "slug": obj.event.slug,
            "title": obj.event.title,
            "starts_at": obj.event.starts_at,
            "ends_at": obj.event.ends_at,
            "location_label": obj.event.location_label,
        }
