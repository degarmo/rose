from pathlib import Path

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def isolated_settings(settings, tmp_path):
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.CONTACT_NOTIFY_EMAIL = "staff-inbox@example.org"
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def csrf_client():
    """A client that enforces CSRF exactly as a browser session would."""
    client = APIClient(enforce_csrf_checks=True)
    token = client.get("/api/csrf/").json()["csrfToken"]
    client.credentials(HTTP_X_CSRFTOKEN=token)
    return client


@pytest.fixture
def gps_image_path():
    return FIXTURES / "gps_tagged.jpg"


@pytest.fixture
def member(django_user_model):
    return django_user_model.objects.create_user(
        email="Private.Person@Example.org",
        display_name="velvet_fox",
        password="a-long-test-password-123",
        legal_name="Jordan Privatename",
        phone="312-555-0199",
    )


@pytest.fixture
def admin_user(django_user_model):
    return django_user_model.objects.create_superuser(
        email="admin@example.org", display_name="house_admin", password="admin-test-password-1"
    )
