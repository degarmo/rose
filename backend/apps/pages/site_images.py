"""The page images (slots) the public site shows, as one cached map.

`/api/site-images/` serves it, and the server writes the same map into the page
(apps.core.spa) so a page's pictures start loading without waiting for a request.
Saving or deleting a slot drops the cache entry, so a change shows within seconds.
"""

from django.core.cache import cache
from django.db import DatabaseError
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.core.consent_images import consent_image_payload

from .models import SiteImage

CACHE_KEY = "site-images:v1"
TIMEOUT = 60 * 60 * 24


def site_images():
    """`{slot: {url, srcset, alt, width, height, focal: {x, y}}}`, public data only.

    An empty slot, or one withheld for consent, is left out: the page shows its
    texture there.
    """
    images = cache.get(CACHE_KEY)
    if images is None:
        images = {}
        try:
            slots = list(SiteImage.objects.exclude(image=""))
        except DatabaseError:
            # Before the first migration there is no table yet.
            slots = []
        for slot in slots:
            payload = consent_image_payload(slot, "image")
            if payload:
                images[slot.slot] = {**payload, "focal": {"x": slot.focal_x, "y": slot.focal_y}}
        cache.set(CACHE_KEY, images, TIMEOUT)
    return images


def forget_site_images():
    cache.delete(CACHE_KEY)


@receiver(post_save, sender=SiteImage)
@receiver(post_delete, sender=SiteImage)
def _site_image_changed(**kwargs):
    forget_site_images()
