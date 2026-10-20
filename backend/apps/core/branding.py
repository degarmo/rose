"""The club's name, and the neutral name used wherever discretion matters.

Where people read the site (the public pages, the member app, the admin) the name
comes from one setting: `SITE_DISPLAY_NAME`, with `SITE_SHORT_NAME` for tight spots,
both overridable in Admin > Site settings. Neither is ever written into the
repository; unset, both are "Rose".

Discreet places never use it, for members' privacy: email sender names and subjects,
calendar files, receipts and billing descriptors, the authenticator app, member-app
tab titles and notification text. Those read the neutral settings below
(`EMAIL_SENDER_NAME`, `MERCHANT_DISPLAY_NAME`, `OTP_TOTP_ISSUER`, all "Rose" by default).
"""

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError

CACHE_KEY = "site-names:v1"
CACHE_SECONDS = 300


def _names():
    names = cache.get(CACHE_KEY)
    if names is None:
        from apps.pages.models import SiteSettings

        try:
            stored = (
                SiteSettings.objects.filter(pk=1)
                .values("site_display_name", "site_short_name")
                .first()
            )
        except DatabaseError:
            # Before the first migration there is no table yet.
            stored = None
        stored = stored or {}
        stored_display = (stored.get("site_display_name") or "").strip()
        stored_short = (stored.get("site_short_name") or "").strip()
        display = stored_display or settings.SITE_DISPLAY_NAME
        # A short form set in the admin wins; a name set there without one is its own
        # short form; otherwise the environment's short form.
        short = stored_short or stored_display or settings.SITE_SHORT_NAME
        names = {"display": display, "short": short}
        cache.set(CACHE_KEY, names, CACHE_SECONDS)
    return names


def display_name():
    """The club's name where people read the site, the member app and the admin."""
    return _names()["display"]


def short_name():
    """The short form for tight spots: the phone header and the member sidebar."""
    return _names()["short"]


def forget_names():
    cache.delete(CACHE_KEY)


def neutral_name():
    """The plain "Rose" for every discreet place (EMAIL_SENDER_NAME's value)."""
    return settings.EMAIL_SENDER_NAME


def sender_name():
    """Neutral: the From name on every email. Never the club's name."""
    return settings.EMAIL_SENDER_NAME


def merchant_name():
    """Neutral: the merchant name on receipts and the billing descriptor."""
    return settings.MERCHANT_DISPLAY_NAME


def otp_issuer():
    """Neutral: the name authenticator apps show on a staff member's phone."""
    return settings.OTP_TOTP_ISSUER


def admin_site_name(request=None):
    """For django-unfold's SITE_TITLE and SITE_HEADER, which accept a callable."""
    return display_name()
