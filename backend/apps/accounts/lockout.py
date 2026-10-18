"""Lock an email address out of login for a while after repeated failures."""

from django.conf import settings
from django.core.cache import cache

from apps.core.ratelimit import hashed_value


def _keys(email):
    digest = hashed_value(email.strip().lower())
    return f"login-failures:{digest}", f"login-locked:{digest}"


def is_locked(email):
    return cache.get(_keys(email)[1]) is not None


def register_failure(email):
    failures_key, locked_key = _keys(email)
    cache.add(failures_key, 0, timeout=settings.LOGIN_LOCKOUT_SECONDS)
    failures = cache.incr(failures_key)
    if failures >= settings.LOGIN_LOCKOUT_ATTEMPTS:
        cache.set(locked_key, True, timeout=settings.LOGIN_LOCKOUT_SECONDS)
        cache.delete(failures_key)
    return failures


def clear(email):
    cache.delete_many(list(_keys(email)))
