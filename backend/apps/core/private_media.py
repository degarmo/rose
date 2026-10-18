"""Private media: files only ever reachable through an access-checked view.

Callers use `private_media()` and never touch storage URLs. The filesystem
backend refuses to produce a URL at all. Prompt 05 can add a backend for
S3-compatible storage that answers `deliver()` with a short-lived signed URL;
views and models do not change.
"""

from django.conf import settings
from django.core.files.storage import FileSystemStorage, storages
from django.http import FileResponse, HttpResponse
from django.utils.deconstruct import deconstructible
from django.utils.functional import cached_property

PRIVATE_HEADERS = {
    "Cache-Control": "private, no-store, max-age=0",
    "Content-Disposition": "inline",
    "X-Content-Type-Options": "nosniff",
    "Cross-Origin-Resource-Policy": "same-origin",
}


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


def private_storage():
    """Callable for model fields, so the backend can change in settings alone."""
    return storages["private"]


def with_private_headers(response):
    for header, value in PRIVATE_HEADERS.items():
        response[header] = value
    return response


class PrivateMedia:
    """The one interface callers use for private files."""

    def __init__(self, storage=None):
        self.storage = storage or private_storage()

    def read(self, name):
        with self.storage.open(name, "rb") as handle:
            return handle.read()

    def exists(self, name):
        return bool(name) and self.storage.exists(name)

    def delete(self, name):
        if self.exists(name):
            self.storage.delete(name)

    def deliver(self, request, name, content=None, content_type="image/webp"):
        """Response for an already-authorised request. `content` overrides the file."""
        if content is not None:
            response = HttpResponse(content, content_type=content_type)
        else:
            response = FileResponse(self.storage.open(name, "rb"), content_type=content_type)
        return with_private_headers(response)


def private_media():
    return PrivateMedia()
