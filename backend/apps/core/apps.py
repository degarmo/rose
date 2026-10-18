from django.apps import AppConfig
from django.contrib.admin import apps as admin_apps


class CoreConfig(AppConfig):
    default = True
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        import pillow_heif
        from django.conf import settings
        from PIL import Image

        from . import checks  # noqa: F401  (registers the deployment safety checks)

        # HEIC photos from phones decode like any other format, then become WebP.
        pillow_heif.register_heif_opener()
        # Pillow warns above this many pixels and refuses at twice it; uploads
        # treat the warning as a refusal too (apps.core.images).
        Image.MAX_IMAGE_PIXELS = settings.UPLOAD_MAX_PIXELS


class RoseAdminConfig(admin_apps.AdminConfig):
    """Replaces django.contrib.admin so the site gains the Image review page."""

    default = False
    default_site = "apps.core.admin_site.RoseAdminSite"
