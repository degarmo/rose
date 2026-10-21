"""S3-compatible storage for production: one public bucket, one private bucket.

Configured entirely by settings (S3_*), so Cloudflare R2, Backblaze B2, AWS S3
and MinIO all work. See docs/ops/storage.md.
"""

from django.conf import settings
from django.utils.deconstruct import deconstructible
from storages.backends.s3 import S3Storage

PUBLIC_CACHE_CONTROL = "public, max-age=31536000, immutable"
PRIVATE_CACHE_CONTROL = "private, no-store, max-age=0"


def _common():
    return {
        "endpoint_url": settings.S3_ENDPOINT_URL or None,
        "region_name": settings.S3_REGION,
        "access_key": settings.S3_ACCESS_KEY_ID,
        "secret_key": settings.S3_SECRET_ACCESS_KEY,
        "addressing_style": settings.S3_ADDRESSING_STYLE,
        "signature_version": "s3v4",
        # R2 and B2 have no ACLs; access comes from the bucket's own settings.
        "default_acl": None,
        "file_overwrite": False,
    }


@deconstructible
class PublicS3Storage(S3Storage):
    """Page, journal, education and event images. Served from S3_PUBLIC_BASE_URL with a long cache.

    Uploaded names are random, so a changed image is always a new URL.
    """

    def __init__(self, **overrides):
        base = settings.S3_PUBLIC_BASE_URL.split("://", 1)
        options = {
            **_common(),
            "bucket_name": settings.S3_PUBLIC_BUCKET,
            "querystring_auth": False,
            "custom_domain": base[1] if len(base) == 2 else None,
            "url_protocol": f"{base[0]}:" if len(base) == 2 else "https:",
            "object_parameters": {"CacheControl": PUBLIC_CACHE_CONTROL},
        }
        options.update(overrides)
        super().__init__(**options)


@deconstructible
class PrivateS3Storage(S3Storage):
    """Member images, watermarked copies, exports and backups. Never public.

    url() is only ever called by apps.core.private_media after every access
    check, and returns a URL signed for S3_SIGNED_URL_SECONDS (60 by default)
    that also tells the browser not to store the file.
    """

    signed_urls = True

    def __init__(self, **overrides):
        options = {
            **_common(),
            "bucket_name": settings.S3_PRIVATE_BUCKET,
            "querystring_auth": True,
            "querystring_expire": settings.S3_SIGNED_URL_SECONDS,
            "object_parameters": {"CacheControl": PRIVATE_CACHE_CONTROL},
        }
        options.update(overrides)
        super().__init__(**options)

    def signed_url(self, name, content_type):
        """A short-lived URL for the browser, signed against the browser-facing endpoint."""
        browser = self._browser_storage()
        return browser.url(
            name,
            parameters={
                "ResponseCacheControl": PRIVATE_CACHE_CONTROL,
                "ResponseContentType": content_type,
                "ResponseContentDisposition": "inline",
            },
            expire=settings.S3_SIGNED_URL_SECONDS,
        )

    def _browser_storage(self):
        if settings.S3_BROWSER_ENDPOINT_URL == settings.S3_ENDPOINT_URL:
            return self
        if not hasattr(self, "_browser"):
            # Signing happens offline: nothing is ever sent to this endpoint.
            self._browser = S3Storage(
                **{**_common(), "endpoint_url": settings.S3_BROWSER_ENDPOINT_URL},
                bucket_name=settings.S3_PRIVATE_BUCKET,
                querystring_auth=True,
                querystring_expire=settings.S3_SIGNED_URL_SECONDS,
            )
        return self._browser
