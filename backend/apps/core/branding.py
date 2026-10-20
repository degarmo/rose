"""The club's name, from one setting.

`SITE_NAME` in the environment is the default ("Rose" when unset, so the real name
never has to be written into the repository), and Admin > Site settings can override
it. Everything that shows the name reads it here: the site's wordmark and page titles
(through a meta tag the server adds to the page), the admin, email senders, receipts,
calendar files and the authenticator app. `EMAIL_SENDER_NAME`, `MERCHANT_DISPLAY_NAME`
and `OTP_ISSUER` can still give those three their own name when set.
"""

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError

CACHE_KEY = "site-name:v1"
CACHE_SECONDS = 300


def site_name():
    name = cache.get(CACHE_KEY)
    if name is None:
        from apps.pages.models import SiteSettings

        try:
            stored = SiteSettings.objects.filter(pk=1).values_list("site_name", flat=True).first()
        except DatabaseError:
            # Before the first migration there is no table yet.
            stored = None
        name = (stored or "").strip() or settings.SITE_NAME
        cache.set(CACHE_KEY, name, CACHE_SECONDS)
    return name


def forget_site_name():
    cache.delete(CACHE_KEY)


def sender_name():
    """The From name on every email."""
    return settings.EMAIL_SENDER_NAME or site_name()


def merchant_name():
    """The merchant name on receipts; set the processor's billing descriptor to match."""
    return settings.MERCHANT_DISPLAY_NAME or site_name()


def otp_issuer():
    """The name authenticator apps show for the staff login."""
    return settings.OTP_TOTP_ISSUER or site_name()


def admin_site_name(request=None):
    """For django-unfold's SITE_TITLE and SITE_HEADER, which accept a callable."""
    return site_name()
