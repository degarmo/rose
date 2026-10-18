from django.apps import AppConfig
from django.contrib.admin import apps as admin_apps


class CoreConfig(AppConfig):
    default = True
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"


class RoseAdminConfig(admin_apps.AdminConfig):
    """Replaces django.contrib.admin so the site gains the Image review page."""

    default = False
    default_site = "apps.core.admin_site.RoseAdminSite"
