"""Cached reads of page copy and redirects.

Both are read on most requests and change rarely, so each is cached in full and
the cache entry is dropped whenever a row is saved or deleted (signals below).
"""

import re

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.core.branding import forget_site_name

from .models import PageContent, Redirect, SiteSettings, normalise_path

PAGE_KEY = "page-content:v1:{}"
REDIRECTS_KEY = "redirects:v1"
TIMEOUT = 60 * 60 * 24

# Addresses that always move, whatever the loaded redirect table says.
BUILTIN_REDIRECTS = {
    # The old Gallery is a work in progress; the journal is where photos live now.
    "/gallery": "/journal",
}


def page_entries(page):
    """{key: {"value": str, "format": "plain" | "rich"}} for one page."""
    cache_key = PAGE_KEY.format(page)
    entries = cache.get(cache_key)
    if entries is None:
        entries = {
            row.key: {"value": row.value, "format": row.format}
            for row in PageContent.objects.filter(page=page)
        }
        cache.set(cache_key, entries, TIMEOUT)
    return entries


def redirect_map():
    table = cache.get(REDIRECTS_KEY)
    if table is None:
        table = dict(Redirect.objects.values_list("old_path", "new_path"))
        cache.set(REDIRECTS_KEY, table, TIMEOUT)
    return {**table, **BUILTIN_REDIRECTS}


# The account page moved into the member app's Settings. The sign-in pages
# (login, register, verify, forgot, reset) stay under /account.
ACCOUNT_MOVES = {
    "/account": "/members/settings",
    "/account/notices": "/members/settings/notices",
    "/account/export": "/members/settings/privacy/export",
}
RECEIPT_PATH = re.compile(r"^/account/receipts/(\d+)/?$")


def account_move(path):
    """Where an old /account address lives now, keeping receipt numbers."""
    trimmed = path.rstrip("/") or "/"
    if trimmed in ACCOUNT_MOVES:
        return ACCOUNT_MOVES[trimmed]
    match = RECEIPT_PATH.match(path)
    return f"/members/settings/membership/receipts/{match.group(1)}" if match else None


def redirect_for(path):
    """The new address for an old one. "/old/*" in the table matches everything under /old/."""
    moved = account_move(path)
    if moved:
        return moved
    path = normalise_path(path)
    table = redirect_map()
    if path in table:
        return table[path]
    best = None
    for old, new in table.items():
        if old.endswith("/*") and path.startswith(old[:-1]):
            if best is None or len(old) > len(best[0]):
                best = (old, new)
    return best[1] if best else None


@receiver([post_save, post_delete], sender=PageContent)
def _forget_page(sender, instance, **kwargs):
    cache.delete(PAGE_KEY.format(instance.page))


@receiver([post_save, post_delete], sender=Redirect)
def _forget_redirects(sender, instance, **kwargs):
    cache.delete(REDIRECTS_KEY)


@receiver(post_save, sender=SiteSettings)
def _forget_site_name(sender, instance, **kwargs):
    forget_site_name()
