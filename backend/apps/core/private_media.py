"""Private media: files only ever reachable through an access-checked view.

Callers use `private_media()` and never touch storage URLs. Locally the
filesystem backend has no URL at all and the view streams the file. With the
private S3 bucket, the view answers with a 302 to a URL signed for 60 seconds;
either way the view's own response is `Cache-Control: private, no-store`.
"""

import hashlib
import hmac

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, storages
from django.core.signals import setting_changed
from django.dispatch import receiver
from django.http import FileResponse, HttpResponseRedirect
from django.utils.deconstruct import deconstructible
from django.utils.functional import LazyObject, cached_property, empty

PRIVATE_HEADERS = {
    "Cache-Control": "private, no-store, max-age=0",
    "Content-Disposition": "inline",
    "X-Content-Type-Options": "nosniff",
    "Cross-Origin-Resource-Policy": "same-origin",
}

WATERMARK_PREFIX = "watermarks/"
EXPORT_PREFIX = "exports/"
BACKUP_PREFIX = "backups/"


@deconstructible
class PrivateFileSystemStorage(FileSystemStorage):
    """Local private storage under PRIVATE_MEDIA_ROOT. There is deliberately no public URL."""

    @cached_property
    def base_location(self):
        return self._value_or_setting(self._location, settings.PRIVATE_MEDIA_ROOT)

    def _clear_cached_properties(self, setting, **kwargs):
        super()._clear_cached_properties(setting, **kwargs)
        if setting == "PRIVATE_MEDIA_ROOT":
            self.__dict__.pop("base_location", None)
            self.__dict__.pop("location", None)

    def url(self, name):
        raise RuntimeError("Private media has no public URL. Serve it through a view.")


class PrivateStorage(LazyObject):
    """storages["private"], looked up on first use (like Django's default_storage)."""

    def _setup(self):
        self._wrapped = storages["private"]


private_storage_proxy = PrivateStorage()


@receiver(setting_changed)
def _reset_private_storage(setting, **kwargs):
    if setting in ("STORAGES", "PRIVATE_MEDIA_ROOT"):
        private_storage_proxy._wrapped = empty


def private_storage():
    """Callable for model fields, so the backend can change in settings alone."""
    return private_storage_proxy


def with_private_headers(response):
    for header, value in PRIVATE_HEADERS.items():
        response[header] = value
    return response


def _digest(*parts):
    message = "|".join(str(part) for part in parts).encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def watermark_dir(source_name):
    """All viewers' copies of one image live under one folder, so deleting the image finds them."""
    return f"{WATERMARK_PREFIX}{_digest('source', source_name)[:32]}/"


def viewer_tag(viewer_id):
    return _digest("viewer", viewer_id)[:16]


def watermark_name(source_name, viewer_id, label):
    """An object key that reveals neither the viewer nor the image.

    It includes the watermark style, so changing the opacity or spacing renders new copies.
    """
    from .watermark import style_key

    label_part = _digest("label", source_name, viewer_id, label, style_key())[:32]
    return f"{watermark_dir(source_name)}{viewer_tag(viewer_id)}-{label_part}.webp"


class PrivateMedia:
    """The one interface callers use for private files."""

    def __init__(self, storage=None):
        self.storage = storage or storages["private"]

    def read(self, name):
        with self.storage.open(name, "rb") as handle:
            return handle.read()

    def exists(self, name):
        return bool(name) and self.storage.exists(name)

    def save(self, name, content):
        """Store bytes under exactly `name` (no renaming), replacing any old copy."""
        if self.storage.exists(name):
            self.storage.delete(name)
        return self.storage.save(name, ContentFile(content))

    def delete(self, name):
        """Delete a file and every watermarked copy made from it."""
        if not name:
            return
        if self.storage.exists(name):
            self.storage.delete(name)
        if not name.startswith(WATERMARK_PREFIX):
            for copy in self.iter_prefix(watermark_dir(name)):
                self.storage.delete(copy)

    def delete_viewer_copies(self, viewer_id):
        """Remove every copy watermarked with this person's name (account deletion)."""
        tag = viewer_tag(viewer_id)
        for folder in self.list_dirs(WATERMARK_PREFIX):
            for copy in self.iter_prefix(folder):
                if copy.rsplit("/", 1)[-1].startswith(f"{tag}-"):
                    self.storage.delete(copy)

    def open(self, name):
        return self.storage.open(name, "rb")

    def deliver(self, request, name, content_type="image/webp"):
        """Response for an already-authorised request."""
        if getattr(self.storage, "signed_urls", False):
            response = HttpResponseRedirect(self.storage.signed_url(name, content_type))
        else:
            response = FileResponse(self.storage.open(name, "rb"), content_type=content_type)
        return with_private_headers(response)

    def deliver_watermarked(self, request, name, viewer_id, label):
        """Render the viewer's copy once, keep it under watermarks/, then deliver it.

        Copies are removed after WATERMARK_RETENTION_DAYS by the bucket's lifecycle
        rule, and by apps.feed.tasks.purge_old_watermarks wherever there is none.
        """
        from .watermark import watermark_bytes

        marked = watermark_name(name, viewer_id, label)
        if not self.exists(marked):
            self.save(marked, watermark_bytes(self.read(name), label))
        return self.deliver(request, marked)

    def iter_prefix(self, prefix):
        """Names of files directly under a folder prefix such as "exports/"."""
        try:
            _dirs, files = self.storage.listdir(prefix.rstrip("/"))
        except FileNotFoundError:
            return []
        return [f"{prefix}{name}" for name in files]

    def list_dirs(self, prefix):
        try:
            dirs, _files = self.storage.listdir(prefix.rstrip("/"))
        except FileNotFoundError:
            return []
        return [f"{prefix}{name}/" for name in dirs]

    def modified(self, name):
        return self.storage.get_modified_time(name)


def private_media():
    return PrivateMedia()
