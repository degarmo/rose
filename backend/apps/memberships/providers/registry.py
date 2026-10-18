"""Providers enabled by settings.PAYMENT_PROVIDERS. Unknown keys fail at startup."""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .manual import ManualProvider
from .sandbox import SandboxProvider

AVAILABLE = {
    ManualProvider.key: ManualProvider,
    SandboxProvider.key: SandboxProvider,
}


def build(key):
    if key not in AVAILABLE:
        raise ImproperlyConfigured(f"Unknown payment provider {key!r}.")
    return AVAILABLE[key]()


def enabled():
    """Instantiate every enabled provider. Raises for sandbox when DEBUG is off."""
    return {key: build(key) for key in settings.PAYMENT_PROVIDERS}


def get(key):
    if key not in settings.PAYMENT_PROVIDERS:
        return None
    return build(key)


def online():
    return [provider for provider in enabled().values() if provider.online]


def validate():
    if "manual" not in settings.PAYMENT_PROVIDERS:
        raise ImproperlyConfigured("The manual (in-person) provider must always be enabled.")
    enabled()
