"""Daily membership transitions and reminders. Run by Celery beat."""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from . import emails
from .models import Membership


def run(now=None):
    now = now or timezone.now()
    grace = timedelta(days=settings.MEMBERSHIP_GRACE_DAYS)
    counts = {
        "to_grace": 0,
        "to_expired": 0,
        "to_cancelled": 0,
        "pending_expired": 0,
        "guest_passes_ended": 0,
        "free_ended": 0,
        "free_continued": 0,
        "reminders": 0,
    }

    # Unused codes lapse: unpaid ones, and free ones whose ID was never checked.
    stale = now - timedelta(days=settings.MEMBERSHIP_PENDING_EXPIRY_DAYS)
    for membership in Membership.objects.filter(
        Q(paid_awaiting_id_check=False) | Q(tier__is_free=True),
        status=Membership.Status.PENDING_PAYMENT,
        created_at__lt=stale,
    ):
        membership.end(Membership.Status.EXPIRED, now)
        membership.save(update_fields=["status", "ended_at", "auto_renew", "updated_at"])
        counts["pending_expired"] += 1

    # A guest night simply ends: no grace period and no email.
    for membership in Membership.objects.filter(
        status=Membership.Status.ACTIVE, current_period_end__lte=now, tier__is_guest_pass=True
    ):
        membership.end(Membership.Status.EXPIRED, now)
        membership.save(update_fields=["status", "ended_at", "auto_renew", "updated_at"])
        counts["guest_passes_ended"] += 1

    # Free tiers have nothing to renew: one that renews stays open for another period,
    # and a time-limited one (a free week) simply ends, with no grace period and no email.
    for membership in Membership.objects.filter(
        status=Membership.Status.ACTIVE, current_period_end__lte=now, tier__is_free=True
    ).select_related("tier"):
        if membership.tier.renews and not membership.cancel_at_period_end:
            membership.start_new_period(now)
            membership.save()
            counts["free_continued"] += 1
            continue
        status = (
            Membership.Status.CANCELLED
            if membership.cancel_at_period_end
            else Membership.Status.EXPIRED
        )
        membership.end(status, now)
        membership.save(update_fields=["status", "ended_at", "auto_renew", "updated_at"])
        counts["free_ended"] += 1

    for membership in Membership.objects.filter(
        status=Membership.Status.ACTIVE, current_period_end__lte=now
    ).select_related("user"):
        with transaction.atomic():
            if membership.cancel_at_period_end:
                membership.end(Membership.Status.CANCELLED, now)
                membership.save(update_fields=["status", "ended_at", "auto_renew", "updated_at"])
                counts["to_cancelled"] += 1
                continue
            membership.status = Membership.Status.GRACE
            membership.grace_started_at = now
            membership.save(update_fields=["status", "grace_started_at", "updated_at"])
            transaction.on_commit(lambda m=membership: emails.send_account_note(m, "grace"))
            counts["to_grace"] += 1

    for membership in Membership.objects.filter(
        status=Membership.Status.GRACE, current_period_end__lte=now - grace
    ).select_related("user"):
        membership.end(Membership.Status.EXPIRED, now)
        membership.save(update_fields=["status", "ended_at", "auto_renew", "updated_at"])
        transaction.on_commit(lambda m=membership: emails.send_account_note(m, "expired"))
        counts["to_expired"] += 1

    first, second = settings.MEMBERSHIP_REMINDER_DAYS
    upcoming = Membership.objects.filter(
        status=Membership.Status.ACTIVE,
        cancel_at_period_end=False,
        auto_renew=False,
        current_period_end__gt=now,
        current_period_end__lte=now + timedelta(days=first),
        tier__is_guest_pass=False,
        tier__is_free=False,
    ).select_related("user__profile")
    for membership in upcoming:
        days_left = membership.current_period_end - now
        if days_left <= timedelta(days=second) and membership.reminded_3_at is None:
            membership.reminded_3_at = now
            membership.reminded_14_at = membership.reminded_14_at or now
        elif days_left > timedelta(days=second) and membership.reminded_14_at is None:
            membership.reminded_14_at = now
        else:
            continue
        membership.save(update_fields=["reminded_14_at", "reminded_3_at", "updated_at"])
        # Turned off in Settings > Notifications: the reminder is recorded but not sent.
        if membership.user is None or not membership.user.profile.email_membership_reminders:
            continue
        emails.send_account_note(membership, "upcoming")
        counts["reminders"] += 1
    return counts
