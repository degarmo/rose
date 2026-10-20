"""The in-person age check: recording it, and revoking it.

Staff look at a valid photo ID showing 18+ and hand it back. The IdCheck row says only that
they saw one, who did, and when. No ID number, date of birth, photo or scan is taken, here
or anywhere else (decision 455). One check opens the member feed for good; it can be revoked
with a reason, which closes the feed at once. Every check and revocation is in the audit log.
"""

from django.db import transaction
from django.utils import timezone

from apps.core.models import AuditLog, audit

from .access import FEED, entitlements, is_age_verified
from .models import IdCheck


class AgeCheckError(Exception):
    """A check or revocation was refused; the message is shown to staff."""


def is_team_account(user):
    return bool(user.is_staff or user.is_superuser)


def _label(user, membership):
    if membership is not None:
        return f"Membership {membership.reference_code} ({user.display_name})"
    return f"Account {user.display_name}"


def _ref(user, membership):
    return membership.reference_code if membership is not None else user.display_name


def _witness_for(staff, user, witness):
    """A team account's check needs two people: the one recording it and the one checked
    must differ, or a second team member must witness it."""
    if not is_team_account(user) or staff.pk != user.pk:
        return None
    if witness is None:
        raise AgeCheckError("A second team member must witness your own ID check.")
    if witness.pk == user.pk or not (witness.is_active and is_team_account(witness)):
        raise AgeCheckError("The witness must be another member of the team.")
    return witness


@transaction.atomic
def record_id_check(staff, user, membership=None, witness=None):
    """Staff saw a valid photo ID showing 18+ for `user`. Nothing else is stored."""
    if user is None:
        raise AgeCheckError("This belongs to a deleted account.")
    if is_age_verified(user):
        raise AgeCheckError("An ID check is already on file.")
    witness = _witness_for(staff, user, witness)
    check = IdCheck.objects.create(
        user=user,
        membership=membership,
        checked_by=staff,
        witnessed_by=witness,
        verified_18_plus=True,
    )
    audit(
        AuditLog.Category.DOOR_DESK,
        "id_check",
        staff,
        _label(user, membership),
        "membership" if membership is not None else "account",
        target_user=user,
        target_ref=_ref(user, membership),
        reason=f"Witnessed by {witness.display_name}" if witness else "",
    )
    if witness is not None:
        audit(
            AuditLog.Category.DOOR_DESK,
            "id_check_witnessed",
            witness,
            _label(user, membership),
            "account",
            target_user=user,
            target_ref=_ref(user, membership),
            reason=f"Recorded by {staff.display_name}",
        )
    profile = getattr(user, "profile", None)
    if profile is not None and profile.age_check_notice_at is not None:
        profile.age_check_notice_at = None
        profile.save(update_fields=["age_check_notice_at", "updated_at"])
    transaction.on_commit(lambda: _tell(user.pk))
    return check


def _tell(user_pk):
    """An in-app note (when the feed is now theirs) and a neutral "You're all set" email."""
    from apps.accounts.models import User
    from apps.feed.models import Notification
    from apps.feed.services import notify

    from .emails import send_age_verified

    user = User.objects.filter(pk=user_pk, is_active=True).first()
    if user is None:
        return
    if FEED in entitlements(user):
        notify(
            user,
            Notification.Kind.AGE_VERIFIED,
            "Your age check is recorded. Thank you. The member feed is open to you.",
        )
    send_age_verified(user)


@transaction.atomic
def revoke_id_checks(staff, user, reason, membership=None):
    """Revoke every valid check for this person, with a reason. The feed closes at once."""
    reason = (reason or "").strip()
    if not reason:
        raise AgeCheckError("Give a reason for revoking the ID check.")
    if user is None:
        raise AgeCheckError("This belongs to a deleted account.")
    revoked = (
        IdCheck.valid()
        .filter(user=user)
        .update(revoked_at=timezone.now(), revoked_by=staff, revoke_reason=reason[:300])
    )
    if not revoked:
        raise AgeCheckError("There is no ID check on file to revoke.")
    audit(
        AuditLog.Category.DOOR_DESK,
        "id_check_revoked",
        staff,
        _label(user, membership),
        "membership" if membership is not None else "account",
        target_user=user,
        target_ref=_ref(user, membership),
        reason=reason,
    )
    return revoked


def seed_check(user):
    """Demo and test data only (seed_demo, e2e_fixtures): a check with nobody behind it,
    without the email or notification a real one sends."""
    if not IdCheck.valid().filter(user=user).exists():
        IdCheck.objects.create(user=user)
