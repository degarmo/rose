"""Membership payloads. Never included: typed signature names, emails, provider
customer references or anything about an ID beyond whether a check exists."""

from datetime import timedelta

from django.conf import settings
from rest_framework import serializers

from .access import events_remaining, is_age_verified
from .models import Membership, MembershipAgreement, Payment, Tier


class TierSerializer(serializers.ModelSerializer):
    interval_label = serializers.CharField(source="get_interval_display")
    allowed_event_tags = serializers.SerializerMethodField()

    class Meta:
        model = Tier
        fields = [
            "slug",
            "name",
            "description",
            "perks",
            "price_cents",
            "currency",
            "is_free",
            "interval",
            "interval_label",
            "duration_days",
            "renews",
            "events_per_month",
            "guests_included_per_event",
            "guest_discount",
            "premium_discord",
            "event_access",
            "allowed_event_tags",
            "grants_feed_access",
            "grants_members_events",
            "grants_members_education",
            "is_featured",
            "is_guest_pass",
            "is_placeholder",
        ]

    def get_allowed_event_tags(self, obj):
        if obj.event_access != Tier.EventAccess.TAGGED:
            return []
        return [{"slug": tag.slug, "name": tag.name} for tag in obj.allowed_event_tags.all()]


class AgreementSerializer(serializers.ModelSerializer):
    class Meta:
        model = MembershipAgreement
        fields = ["version", "title", "body", "published_at", "is_placeholder"]


class PaymentSummarySerializer(serializers.ModelSerializer):
    method_label = serializers.CharField(source="get_method_display")
    status_label = serializers.CharField(source="get_status_display")

    class Meta:
        model = Payment
        fields = [
            "id",
            "created_at",
            "amount_cents",
            "method",
            "method_label",
            "status",
            "status_label",
        ]


class MyMembershipSerializer(serializers.ModelSerializer):
    """The signed-in person's own membership. Self only."""

    self_only = True
    tier = TierSerializer()
    status_label = serializers.SerializerMethodField()
    events_remaining_this_month = serializers.SerializerMethodField()
    online = serializers.SerializerMethodField()
    id_checked = serializers.SerializerMethodField()
    last_payment_failed = serializers.SerializerMethodField()
    code_expires_at = serializers.SerializerMethodField()
    payments = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = [
            "reference_code",
            "tier",
            "status",
            "status_label",
            "current_period_start",
            "current_period_end",
            "auto_renew",
            "cancel_at_period_end",
            "paid_awaiting_id_check",
            "source",
            "online",
            "id_checked",
            "last_payment_failed",
            "code_expires_at",
            "payments",
            "events_remaining_this_month",
            "created_at",
        ]

    def get_status_label(self, obj):
        if obj.status == Membership.Status.PENDING_PAYMENT and obj.paid_awaiting_id_check:
            return "Waiting for ID check"
        return obj.get_status_display()

    def get_events_remaining_this_month(self, obj):
        """The member's own figure: members-only events left this month. None is unlimited."""
        if not obj.is_entitled:
            return None
        return events_remaining(obj)

    def get_online(self, obj):
        return obj.source == Membership.Source.PROVIDER and bool(obj.provider_subscription_ref)

    def get_id_checked(self, obj):
        return is_age_verified(obj.user)

    def get_last_payment_failed(self, obj):
        latest = obj.payments.exclude(status=Payment.Status.REFUNDED).first()
        return latest is not None and latest.status == Payment.Status.FAILED

    def get_code_expires_at(self, obj):
        """When an unused reference code lapses (the daily lifecycle expires it): an unpaid
        one, or a free tier's still waiting for its ID check."""
        if obj.status != Membership.Status.PENDING_PAYMENT:
            return None
        if obj.paid_awaiting_id_check and not obj.tier.is_free:
            return None
        return obj.created_at + timedelta(days=settings.MEMBERSHIP_PENDING_EXPIRY_DAYS)

    def get_payments(self, obj):
        return PaymentSummarySerializer(obj.payments.all(), many=True).data


class JoinSerializer(serializers.Serializer):
    tier = serializers.SlugField()
    agreement_version = serializers.IntegerField()
    typed_name = serializers.CharField(max_length=200, write_only=True)
    # Not needed for a free tier.
    method = serializers.CharField(max_length=40, required=False, allow_blank=True)


def receipt_payload(payment):
    """Neutral by design: the merchant name, an amount and 'Membership'. Nothing else."""
    return {
        "title": "Receipt",
        "merchant": settings.MERCHANT_DISPLAY_NAME,
        "description": "Membership",
        "reference": f"{payment.membership.reference_code}-{payment.pk}",
        "date": payment.created_at,
        "amount_cents": payment.amount_cents,
        "currency": payment.membership.tier.currency,
        "method": payment.get_method_display(),
        "kind": "Refund" if payment.status == Payment.Status.REFUNDED else "Payment",
    }
