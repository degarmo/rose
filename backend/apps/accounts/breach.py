"""Optional check against known breached passwords (PASSWORD_BREACH_CHECK, default off).

It uses the k-anonymity range API: only the first five characters of the
password's SHA-1 hash leave the server, and the reply is every hash suffix
sharing that prefix, padded so its size says nothing either. The password,
the full hash and the account are never sent.

The trade-off (docs/ops/security.md): it is an outbound call to a third party
on every new password, so it is off unless the club turns it on. If the
service cannot be reached, the password is accepted rather than blocking
sign-up, and only that fact is logged.
"""

import hashlib
import logging
import urllib.error
import urllib.request

from django.conf import settings
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

BREACHED = "This password has appeared in a data breach elsewhere. Please choose a different one."


def breach_count(password):
    digest = hashlib.sha1(password.encode(), usedforsecurity=False).hexdigest().upper()
    prefix, suffix = digest[:5], digest[5:]
    request = urllib.request.Request(
        f"{settings.PASSWORD_BREACH_API}{prefix}",
        headers={"Add-Padding": "true", "User-Agent": "password-check"},
    )
    with urllib.request.urlopen(request, timeout=settings.PASSWORD_BREACH_TIMEOUT_SECONDS) as reply:
        body = reply.read().decode()
    for line in body.splitlines():
        candidate, _, count = line.partition(":")
        if candidate.strip() == suffix:
            return int(count.strip() or 0)
    return 0


class BreachedPasswordValidator:
    def validate(self, password, user=None):
        if not settings.PASSWORD_BREACH_CHECK:
            return
        try:
            found = breach_count(password)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            logger.warning("Breached-password service unreachable; password accepted")
            return
        if found:
            raise ValidationError(BREACHED, code="password_breached")

    def get_help_text(self):
        return "Your password must not be one known from data breaches."
