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
    # Tests run with DEBUG off, where only the in-person provider may exist.
    settings.PAYMENT_PROVIDERS = ["manual"]
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


@pytest.fixture
def private_root(settings, tmp_path):
    """Private media goes to a temp folder; watermark cache stays in memory."""
    root = tmp_path / "private"
    settings.PRIVATE_MEDIA_ROOT = root
    settings.CACHES = {
        **settings.CACHES,
        "watermarks": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    }
    return root


@pytest.fixture
def make_member(make_user, private_root):
    """A verified, entitled member who has joined the feed and accepted the guidelines."""
    from apps.feed import services
    from apps.feed.models import Guidelines

    def make(**kwargs):
        user = make_user(**kwargs)
        user.profile.feed_access_granted = True
        user.profile.save()
        services.join_feed(user, Guidelines.current().version)
        user.refresh_from_db()
        return user

    return make


@pytest.fixture
def member_client(make_member):
    """Return (client, user) for a feed member, with CSRF enforced."""

    def build(user=None, **kwargs):
        user = user or make_member(**kwargs)
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(user)
        return csrf_client_for(client), user

    return build


@pytest.fixture
def image_upload(gps_image_path):
    from django.core.files.uploadedfile import SimpleUploadedFile

    def make(name="photo.jpg"):
        return SimpleUploadedFile(name, gps_image_path.read_bytes(), content_type="image/jpeg")

    return make


@pytest.fixture
def make_post(image_upload, settings):
    """Create a published post through the service (premoderation off unless asked)."""
    from apps.feed import services

    def make(author, caption="Hello", images=0, **kwargs):
        settings.FEED_PREMODERATION_POSTS = kwargs.pop("premoderation", 0)
        uploads = [image_upload() for _ in range(images)]
        return services.create_post(author, caption, uploads, attested=bool(uploads), **kwargs)

    return make


@pytest.fixture
def make_tier():
    from apps.memberships.models import Tier

    counter = {"n": 0}

    def make(**kwargs):
        counter["n"] += 1
        defaults = {
            "name": f"Tier {counter['n']}",
            "slug": f"tier-{counter['n']}",
            "price_cents": 2500,
            "interval": Tier.Interval.MONTH,
        }
        defaults.update(kwargs)
        return Tier.objects.create(**defaults)

    return make


@pytest.fixture
def agreement():
    from apps.memberships.models import MembershipAgreement

    return MembershipAgreement.objects.create(
        title="Membership agreement",
        body="<p>I agree to the community agreements.</p>",
        published_at=timezone.now(),
    )


@pytest.fixture
def make_membership(make_tier, make_user):
    """A membership in any status. Running statuses get a period and an ID check."""
    from apps.memberships.models import IdCheck, Membership

    def make(user=None, tier=None, status="active", id_check=None, **kwargs):
        user = user or make_user()
        tier = tier or make_tier()
        membership = Membership(user=user, tier=tier, status=status, **kwargs)
        if status != "pending_payment" and "current_period_end" not in kwargs:
            membership.start_new_period(timezone.now() - timedelta(days=5))
        if status in ("expired", "cancelled"):
            membership.ended_at = timezone.now()
        membership.save()
        if id_check is None:
            id_check = status != "pending_payment"
        if id_check:
            IdCheck.objects.create(membership=membership)
        return membership

    return make


@pytest.fixture
def sandbox(settings):
    """Development mode with the sandbox provider enabled."""
    settings.DEBUG = True
    settings.PAYMENT_PROVIDERS = ["manual", "sandbox"]
    return settings


@pytest.fixture
def desk_staff(django_user_model):
    """Staff with only the door desk permissions, like a volunteer at the door."""
    from django.contrib.auth.models import Permission

    user = django_user_model.objects.create_user(
        email="door@example.org", display_name="door_volunteer", password=PASSWORD, is_staff=True
    )
    user.user_permissions.set(
        Permission.objects.filter(
            content_type__app_label="memberships",
            codename__in=["view_membership", "change_membership", "view_payment"],
        )
    )
    return user
