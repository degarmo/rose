from datetime import timedelta
from pathlib import Path

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

FIXTURES = Path(__file__).parent / "fixtures"
PASSWORD = "a-long-test-password-123"


@pytest.fixture(autouse=True)
def isolated_settings(settings, tmp_path):
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.CONTACT_NOTIFY_EMAIL = "staff-inbox@example.org"
    settings.SITE_URL = "https://site.example"
    settings.IMAGE_MANIFEST_PATH = tmp_path / "image-manifest.json"
    settings.SITE_IMAGES_DIR = tmp_path / "images"
    # Celery reads CELERY_* from Django settings on every lookup.
    settings.CELERY_TASK_ALWAYS_EAGER = True
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def run_on_commit_immediately(request, monkeypatch):
    """Inside the per-test transaction nothing commits, so run hooks straight away."""
    marker = request.node.get_closest_marker("django_db")
    if marker and marker.kwargs.get("transaction"):
        return
    monkeypatch.setattr("django.db.transaction.on_commit", lambda func, *a, **kw: func())


@pytest.fixture
def api_client():
    return APIClient()


def csrf_client_for(client=None):
    client = client or APIClient(enforce_csrf_checks=True)
    token = client.get("/api/csrf/").json()["csrfToken"]
    client.credentials(HTTP_X_CSRFTOKEN=token)
    return client


@pytest.fixture
def csrf_client():
    """A client that enforces CSRF exactly as a browser session would."""
    return csrf_client_for()


@pytest.fixture
def gps_image_path():
    return FIXTURES / "gps_tagged.jpg"


@pytest.fixture
def member(django_user_model):
    return django_user_model.objects.create_user(
        email="Private.Person@Example.org",
        display_name="velvet_fox",
        password=PASSWORD,
        legal_name="Jordan Privatename",
        phone="312-555-0199",
    )


@pytest.fixture
def make_user(django_user_model):
    counter = {"n": 0}

    def make(verified=True, **kwargs):
        counter["n"] += 1
        n = counter["n"]
        user = django_user_model.objects.create_user(
            email=kwargs.pop("email", f"person{n}@example.org"),
            display_name=kwargs.pop("display_name", f"guest_{n}"),
            password=kwargs.pop("password", PASSWORD),
            **kwargs,
        )
        if verified:
            user.mark_email_verified()
        return user

    return make


@pytest.fixture
def signed_in(make_user):
    """Return (client, user): a CSRF-enforcing client logged in as a verified user."""

    def sign_in(user=None, **kwargs):
        user = user or make_user(**kwargs)
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(user)
        return csrf_client_for(client), user

    return sign_in


@pytest.fixture
def make_event():
    from apps.events.models import Event

    counter = {"n": 0}

    def make(**kwargs):
        counter["n"] += 1
        starts = kwargs.pop("starts_at", timezone.now() + timedelta(days=3))
        defaults = {
            "title": f"Evening {counter['n']}",
            "slug": f"evening-{counter['n']}",
            "summary": "A summary.",
            "body": "<p>Body.</p>",
            "category": "social",
            "starts_at": starts,
            "ends_at": starts + timedelta(hours=3),
            "is_published": True,
        }
        defaults.update(kwargs)
        return Event.objects.create(**defaults)

    return make


@pytest.fixture
def admin_user(django_user_model):
    return django_user_model.objects.create_superuser(
        email="admin@example.org", display_name="house_admin", password="admin-test-password-1"
    )
