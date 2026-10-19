"""Membership email. Subjects and bodies never name the club or its activities."""

from django.conf import settings
from django.utils import timezone

from apps.core.email import send_neutral_mail, site_link

REFERENCE_SUBJECT = "Your reference code"
INVITE_SUBJECT = "Your account is ready"
NOTE_SUBJECT = "A note about your account"


def _date(moment):
    local = timezone.localtime(moment)
    return f"{local:%B} {local.day}, {local.year}"


def send_reference_code(membership):
    days = settings.MEMBERSHIP_PENDING_EXPIRY_DAYS
    bring = "a valid photo ID" if membership.tier.is_free else "your payment and a valid photo ID"
    body = (
        f"Hello {membership.user.display_name},\n\n"
        f"Your reference code is {membership.reference_code}.\n\n"
        f"Please bring it on your first visit, along with {bring} "
        "showing you are 18 or older. Staff will finish setting up your account there.\n\n"
        f"The code stays open for {days} days. You can see it any time at {site_link('/account')}\n"
    )
    send_neutral_mail(REFERENCE_SUBJECT, body, to=[membership.user.email])


REMINDER_BODIES = {
    "upcoming": "Your account renews on {date}. To keep things uninterrupted, renew before then.",
    "grace": "Your account reached its renewal date on {date}. It stays open for a few more days "
    "while you renew.",
    "expired": "Your account has now lapsed. You can renew any time.",
}


def send_account_note(membership, kind):
    if membership.user is None:
        return
    body = (
        f"Hello {membership.user.display_name},\n\n"
        + REMINDER_BODIES[kind].format(date=_date(membership.current_period_end))
        + f"\n\nRenew or check your account: {site_link('/account')}\n"
        f"Reference: {membership.reference_code}\n"
    )
    send_neutral_mail(NOTE_SUBJECT, body, to=[membership.user.email])


def send_import_invite(membership, new_account):
    """Sent after import_members. No password link: the person asks for one themselves."""
    if new_account:
        intro = (
            "An account has been set up for you on our new website, with your existing "
            "membership already on it.\n\n"
            f"To sign in for the first time, choose a password at {site_link('/account/forgot')} "
            "using this email address."
        )
    else:
        intro = "Your existing membership has been added to your account."
    body = (
        f"Hello {membership.user.display_name},\n\n{intro}\n\n"
        f"Your reference code is {membership.reference_code}. You can see it any time at "
        f"{site_link('/account')}\n\nIf you were not expecting this, you can ignore this email.\n"
    )
    send_neutral_mail(INVITE_SUBJECT, body, to=[membership.user.email])
