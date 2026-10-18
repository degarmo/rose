from django.apps import AppConfig


class MembershipsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.memberships"

    def ready(self):
        # Fail at startup, not at checkout, if providers are misconfigured
        # (including the sandbox with DEBUG off).
        from .providers import registry

        registry.validate()
