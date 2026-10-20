"""The in-person age check: recording it, revoking it, and the club's switch for it.

Staff look at a valid photo ID showing 18+ and hand it back. The IdCheck row says only that
they saw one, who did, and when. No ID number, date of birth, photo or scan is taken, here
or anywhere else (decision 455). One check opens the member feed for good; it can be revoked
with a reason, which closes the feed at once. Every check and revocation is in the audit log.
"""

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.core.models import AuditLog, audit

from .access import AGE_CHECK_CACHE_KEY, FEED, entitlements, is_age_verified
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


# The club's switch (SiteSettings.require_age_verification_for_feed)

SETTING_LABEL = "Age verification for the member feed"


def can_change_setting(user):
    """The Admin role (superusers count as admins). Moderators and Staff can only see it."""
    from apps.safety import roles

    return roles.has_role(user, roles.ADMIN)


def _fresh_code(user, code):
    """A code from the person's own authenticator app, never used before (django-otp keeps
    the last one it accepted, and throttles wrong guesses)."""
    from django_otp.plugins.otp_totp.models import TOTPDevice

    code = (code or "").strip().replace(" ", "")
    if not code.isdigit():
        return False
    return any(
        device.verify_token(code) for device in TOTPDevice.objects.filter(user=user, confirmed=True)
    )


def _on_off(value):
    return "On" if value else "Off"


@transaction.atomic
def set_age_check_required(actor, required, reason, code):
    """Switch the member feed's age check on or off. Admins only, with a reason and a fresh
    two-step code; the change is in the audit log (who, when, old and new value, reason) and
    reaches every request within moments (the cache is cleared). Switching it on tells each
    person it closes the feed to, once (apps.memberships.tasks)."""
    from apps.pages.models import SiteSettings

    if not can_change_setting(actor):
        raise AgeCheckError("Only an admin can change this setting.")
    reason = (reason or "").strip()
    if not reason:
        raise AgeCheckError("Give a reason for the change.")
    if not _fresh_code(actor, code):
        raise AgeCheckError("That code did not work. Use a new code from your authenticator app.")
    site = SiteSettings.objects.select_for_update().get(pk=SiteSettings.load().pk)
    old = site.require_age_verification_for_feed
    required = bool(required)
    if old == required:
        raise AgeCheckError(f"Age verification is already {_on_off(required).lower()}.")
    site.require_age_verification_for_feed = required
    fields = ["require_age_verification_for_feed", "updated_at"]
    if required:
        site.age_verification_switched_on_at = timezone.now()
        fields.append("age_verification_switched_on_at")
    site.save(update_fields=fields)
    audit(
        AuditLog.Category.SETTINGS,
        "age_verification_on" if required else "age_verification_off",
        actor,
        SETTING_LABEL,
        "setting",
        reason=f"Changed from {_on_off(old)} to {_on_off(required)}. Reason: {reason}",
    )
    cache.delete(AGE_CHECK_CACHE_KEY)
    transaction.on_commit(lambda: cache.delete(AGE_CHECK_CACHE_KEY))
    if required:
        switched_on_at = site.age_verification_switched_on_at.isoformat()

        def tell():
            from .tasks import notify_age_check_switched_on

            notify_age_check_switched_on.delay(switched_on_at)

        transaction.on_commit(tell)
    return site


def notify_switched_on(switched_on_at):
    """Tell each person the switch-on closed the feed to: a neutral email, and the notice on
    their verify card. At most once per person per switch-on."""
    from apps.pages.models import SiteSettings

    from .access import feed_entitled_accounts
    from .emails import send_age_check_notice

    site = SiteSettings.load()
    if not site.require_age_verification_for_feed:
        return 0
    if site.age_verification_switched_on_at != switched_on_at:
        return 0  # switched again since: that switch-on sends its own
    verified = IdCheck.valid().values("user_id")
    due = (
        feed_entitled_accounts()
        .exclude(pk__in=verified)
        .exclude(profile__age_check_notice_at__gte=switched_on_at)
        .select_related("profile")
    )
    told = 0
    for user in due:
        send_age_check_notice(user)
        user.profile.age_check_notice_at = switched_on_at
        user.profile.save(update_fields=["age_check_notice_at", "updated_at"])
        told += 1
    return told


def setting_summary(user):
    """The switch's state for the admin's page and dashboard card."""
    from apps.core import metrics
    from apps.pages.models import SiteSettings

    from .access import age_check_required

    return {
        "required": age_check_required(),
        "can_change": can_change_setting(user),
        "switched_on_at": SiteSettings.load().age_verification_switched_on_at,
        "unchecked_with_feed": metrics.feed_access_without_id_check(),
    }
