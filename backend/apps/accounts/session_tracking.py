"""Where you are signed in: one AccountSession row per session, for Settings > Security.

Only a coarse device label ("Safari on iPhone") and times are kept, never an IP
address, and the session key only as a hash. Rows go when the session ends (log out,
"log out everywhere", a password change elsewhere) or once it would have expired.
"""

import hashlib
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone

from .models import AccountSession

SEEN_EVERY = timedelta(minutes=10)
BROWSERS = (("Edg/", "Edge"), ("Firefox/", "Firefox"), ("Chrome/", "Chrome"), ("Safari/", "Safari"))
SYSTEMS = (
    ("iPhone", "iPhone"),
    ("iPad", "iPad"),
    ("Android", "Android"),
    ("Mac OS X", "Mac"),
    ("Windows", "Windows"),
    ("Linux", "Linux"),
)


def device_label(user_agent):
    browser = next((name for marker, name in BROWSERS if marker in user_agent), "A browser")
    system = next((name for marker, name in SYSTEMS if marker in user_agent), "another device")
    return f"{browser} on {system}"


def key_hash(session_key):
    return hashlib.sha256(session_key.encode()).hexdigest()


def current_hash(request):
    key = request.session.session_key
    return key_hash(key) if key else None


def live_sessions(user):
    """This person's sessions that could still be in use; older rows are removed."""
    cutoff = timezone.now() - timedelta(seconds=settings.SESSION_COOKIE_AGE)
    AccountSession.objects.filter(user=user, last_seen_at__lt=cutoff).delete()
    return AccountSession.objects.filter(user=user)


@receiver(user_logged_in)
def _record(sender, request, user, **kwargs):
    if request is None or not hasattr(request, "session"):
        return
    if request.session.session_key is None:
        request.session.save()
    AccountSession.objects.update_or_create(
        key_hash=key_hash(request.session.session_key),
        defaults={
            "user": user,
            "device": device_label(request.headers.get("User-Agent", "")),
            "last_seen_at": timezone.now(),
        },
    )


@receiver(user_logged_out)
def _forget(sender, request, user, **kwargs):
    if request is not None and hasattr(request, "session") and request.session.session_key:
        AccountSession.objects.filter(key_hash=key_hash(request.session.session_key)).delete()


class SessionSeenMiddleware:
    """Keeps "last active" roughly current: at most one small update per ten minutes."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and request.session.session_key:
            now = timezone.now()
            AccountSession.objects.filter(
                key_hash=key_hash(request.session.session_key), last_seen_at__lt=now - SEEN_EVERY
            ).update(last_seen_at=now)
        return self.get_response(request)
