"""Membership payloads. Never included: typed signature names, emails, provider
customer references or anything about an ID beyond whether a check exists."""

from django.conf import settings
from rest_framework import serializers

from .models import Membership, MembershipAgreement, Payment, Tier, has_id_check


class TierSerializer(serializers.ModelSerializer):
    interval_label = serializers.CharField(source="get_interval_display")

    class Meta:
        model = Tier
        fields = [
            "slug",
            "name",
            "description",
            "benefits",
            "price_cents",
            "currency",
            "interval",
            "interval_label",
            "duration_days",
            "grants_feed_access",
            "grants_members_events",
            "grants_members_education",
        ]


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
    status_label = serializers.CharField(source="get_status_display")
    online = serializers.SerializerMethodField()
    id_checked = serializers.SerializerMethodField()
    last_payment_failed = serializers.SerializerMethodField()
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
            "payments",
            "created_at",
        ]

    def get_online(self, obj):
        return obj.source == Membership.Source.PROVIDER and bool(obj.provider_subscription_ref)

    def get_id_checked(self, obj):
        return has_id_check(obj.user)

    def get_last_payment_failed(self, obj):
        latest = obj.payments.exclude(status=Payment.Status.REFUNDED).first()
        return latest is not None and latest.status == Payment.Status.FAILED

    def get_payments(self, obj):
        return PaymentSummarySerializer(obj.payments.all(), many=True).data


class JoinSerializer(serializers.Serializer):
    tier = serializers.SlugField()
    agreement_version = serializers.IntegerField()
    typed_name = serializers.CharField(max_length=200, write_only=True)
    method = serializers.CharField(max_length=40)


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
