"""Staff actions on an account, from the admin's Members page: the staff feed grant,
confirming an email, a password reset, signing out everywhere, deactivating and
reactivating, the CSV export and erasure.

Every one is written to the audit log. Those that change the account tell the member with
the neutral notice and email ("An update about your account", apps.safety.services); a
password reset's own email is its notice, and erasure sends the closing email.
"""

from django.db import transaction
from django.utils import timezone

from apps.core.models import AuditLog, audit

from . import tasks


class AccountActionError(Exception):
    """An action that does not apply to this account; the message says why."""


def _log(actor, action, user, reason="", category=AuditLog.Category.OPERATIONS):
    audit(
        category,
        action,
        actor,
        f"Member {user.display_name}",
        "user",
        target_user=user,
        reason=reason,
    )


def _tell(user, message):
    from apps.safety.services import tell_member

    tell_member(user, message)


def _reason(reason):
    reason = reason.strip()
    if not reason:
        raise AccountActionError("Give a reason.")
    return reason


def record_grant(profile, actor):
    """Stamp who granted feed access, and when. Revoking clears the stamp."""
    if profile.feed_access_granted and profile.feed_access_granted_at is None:
        profile.feed_access_granted_by = actor
        profile.feed_access_granted_at = timezone.now()
    elif not profile.feed_access_granted:
        profile.feed_access_granted_by = None
        profile.feed_access_granted_at = None


@transaction.atomic
def set_feed_grant(actor, user, granted, reason):
    """Give or take back the staff grant of the member feed (for comped members and
    volunteers). It is an entitlement only: the feed still waits for the person's own ID
    check while the club has the age check on (apps.feed.access). Returns a note when it
    does."""
    from apps.memberships.access import age_gate_passes

    reason = _reason(reason)
    profile = user.profile
    if profile.feed_access_granted == granted:
        raise AccountActionError("Already has the grant." if granted else "Has no grant.")
    profile.feed_access_granted = granted
    record_grant(profile, actor)
    profile.save()
    _log(actor, "feed_grant" if granted else "feed_grant_revoked", user, reason)
    _tell(user, "Your access to the member community changed.")
    if granted and not age_gate_passes(user):
        return "the feed opens after their ID check at the door"
    return ""


def confirm_email(actor, user, reason):
    reason = _reason(reason)
    if user.email_verified:
        raise AccountActionError("The email is already confirmed.")
    user.mark_email_verified()
    _log(actor, "email_confirmed_by_staff", user, reason)
    _tell(user, "Our team confirmed your email address.")
    return ""


def send_password_reset(actor, user):
    """The member's own reset email, as if they had asked; it is the notice."""
    if not user.is_active:
        raise AccountActionError("The account is deactivated.")
    _log(actor, "password_reset_sent", user)
    transaction.on_commit(lambda: tasks.send_password_reset_email.delay(user.pk))
    return ""


def sign_out_everywhere(actor, user, reason):
    reason = _reason(reason)
    user.sign_out_everywhere()
    _log(actor, "signed_out_everywhere", user, reason, AuditLog.Category.SECURITY)
    _tell(user, "Our team signed your account out on every device.")
    return ""


@transaction.atomic
def set_active(actor, user, active, reason):
    """Deactivate (no login, every session ended, nothing deleted) or reactivate."""
    reason = _reason(reason)
    if user.is_active == active:
        raise AccountActionError("Already active." if active else "Already deactivated.")
    user.is_active = active
    user.save(update_fields=["is_active"])
    if not active:
        user.sign_out_everywhere()
    _log(actor, "reactivated" if active else "deactivated", user, reason)
    _tell(
        user,
        "Our team reactivated your account." if active else "Our team deactivated your account.",
    )
    return ""


EXPORT_HEADER = ["Display name", "Tier", "Membership status", "Joined"]


def export_rows(actor, users, include_email):
    """Rows for the CSV export of these accounts: display name, tier, membership status and
    the month they joined; the email only when asked for, which is logged as such."""
    from apps.memberships.models import Membership

    users = list(users)
    audit(
        AuditLog.Category.EXPORT,
        "member_csv_with_email" if include_email else "member_csv",
        actor,
        f"Member export ({len(users)} accounts)",
        "export",
        reason="Included email addresses" if include_email else "",
    )
    rows = [[*EXPORT_HEADER, *(["Email"] if include_email else [])]]
    for user in users:
        membership = (
            Membership.objects.filter(user=user).select_related("tier").order_by("-created_at")
        ).first()
        name = user.display_name
        row = [
            f"'{name}" if name[:1] in "=+-@" else name,
            membership.tier.name if membership else "",
            membership.get_status_display() if membership else "No membership",
            timezone.localtime(user.date_joined).strftime("%Y-%m"),
        ]
        if include_email:
            row.append(user.email)
        rows.append(row)
    return rows


def request_erasure(actor, user, reason):
    """Erase the account, in the background (apps.accounts.erasure). Cannot be undone."""
    reason = _reason(reason)
    _log(actor, "erase_account", user, reason)
    transaction.on_commit(lambda: tasks.erase_account.delay(user.pk))
    return "erasing now"
