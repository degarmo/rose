"""Two-step login with an authenticator app, shared by the admin's staff login and the
website's login (where members may turn it on in Settings > Security).

Staff must have it; members choose. Either way the code comes from an authenticator
app (TOTP) or one of ten single-use backup codes.
"""

import secrets

from django.conf import settings
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.core.models import AuditLog, audit


def confirmed_totp(user):
    return TOTPDevice.objects.filter(user=user, confirmed=True).first()


def is_enabled(user):
    return confirmed_totp(user) is not None


def new_backup_codes(user):
    """Replace any backup codes with ten new ones; returns them, to be shown once."""
    StaticDevice.objects.filter(user=user).delete()
    backup = StaticDevice.objects.create(user=user, name="Backup codes", confirmed=True)
    codes = [secrets.token_hex(5) for _ in range(settings.OTP_BACKUP_CODE_COUNT)]
    StaticToken.objects.bulk_create(StaticToken(device=backup, token=code) for code in codes)
    return codes


def backup_codes_left(user):
    return StaticToken.objects.filter(device__user=user, device__confirmed=True).count()


def clean(token):
    return str(token).replace(" ", "").replace("-", "").strip()


def verify(user, token):
    """The device a code belongs to (authenticator first, then backup codes), or None."""
    token = clean(token)
    totp = confirmed_totp(user)
    if totp is not None and totp.verify_token(token):
        return totp
    backup = StaticDevice.objects.filter(user=user, confirmed=True).first()
    if backup is not None and backup.verify_token(token):
        audit(
            AuditLog.Category.SECURITY,
            "backup_code_used",
            user,
            f"Account ({user.display_name})",
            "user",
            target_user=user,
        )
        return backup
    return None


def fresh_code(user, code):
    """A code from the person's own authenticator app, never used before (django-otp keeps
    the last one it accepted, and throttles wrong guesses). For confirming a serious change
    on top of the session's two-step login; backup codes do not count."""
    code = clean(code or "")
    if not code.isdigit():
        return False
    return any(
        device.verify_token(code) for device in TOTPDevice.objects.filter(user=user, confirmed=True)
    )


def remove(user):
    TOTPDevice.objects.filter(user=user).delete()
    StaticDevice.objects.filter(user=user).delete()
