from django.apps import AppConfig


class SafetyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.safety"
    verbose_name = "Safety and the team"

    def ready(self):
        from . import owner  # noqa: F401  (connects the superuser's first-login setup)
