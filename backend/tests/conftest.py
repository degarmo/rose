import json
import os
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
    # The club's names are configuration; tests see the repository's defaults whatever
    # .env says.
    settings.SITE_DISPLAY_NAME = settings.SITE_SHORT_NAME = "Rose"
    settings.EMAIL_SENDER_NAME = settings.MERCHANT_DISPLAY_NAME = "Rose"
    settings.OTP_TOTP_ISSUER = "Rose"
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
    """Private media, including watermarked copies, goes to a temp folder."""
    root = tmp_path / "private"
    settings.PRIVATE_MEDIA_ROOT = root
    return root


def verify_age(user, checked_by=None):
    """Record the in-person age check the member feed needs (apps.memberships.access)."""
    from apps.memberships.models import IdCheck

    return IdCheck.objects.create(user=user, checked_by=checked_by)


@pytest.fixture
def make_member(make_user, private_root):
    """A verified, entitled, age-checked member who has joined the feed and accepted the
    guidelines."""
    from apps.feed import services
    from apps.feed.models import Guidelines

    def make(**kwargs):
        user = make_user(**kwargs)
        user.profile.feed_access_granted = True
        user.profile.save()
        verify_age(user)
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
            IdCheck.objects.create(user=membership.user, membership=membership)
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


def staff_login(client, user):
    """Log a staff member in as if they had passed the two-step check."""
    from django_otp import DEVICE_ID_SESSION_KEY
    from django_otp.plugins.otp_totp.models import TOTPDevice

    device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
    if device is None:
        device = TOTPDevice.objects.create(user=user, name="Test app", confirmed=True)
    # Permission changes raise the session epoch; log in with the current one.
    user.refresh_from_db()
    client.force_login(user)
    session = client.session
    session[DEVICE_ID_SESSION_KEY] = device.persistent_id
    session.save()
    return client


def fresh_code(user):
    """The current code from this person's authenticator (staff_login made the device)."""
    import time

    from django_otp.oath import TOTP
    from django_otp.plugins.otp_totp.models import TOTPDevice

    device = TOTPDevice.objects.get(user=user, confirmed=True)
    totp = TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift)
    totp.time = time.time()
    return f"{totp.token():0{device.digits}d}"


def next_window(user):
    """As if the next 30-second code window had come: the last code used no longer blocks
    the current one (django-otp refuses a code it has already accepted)."""
    from django_otp.plugins.otp_totp.models import TOTPDevice

    TOTPDevice.objects.filter(user=user).update(last_t=-1)


@pytest.fixture
def admin_client(admin_user):
    """pytest-django's admin_client (its own Client), plus a verified second step."""
    from django.test import Client

    return staff_login(Client(), admin_user)


S3_TEST_ENDPOINT = os.environ.get("S3_TEST_ENDPOINT", "http://localhost:9000")
S3_TEST_KEY = os.environ.get("S3_TEST_ACCESS_KEY", "minio-local")
S3_TEST_SECRET = os.environ.get("S3_TEST_SECRET_KEY", "minio-local-secret")


@pytest.fixture
def s3(settings, tmp_path):
    """Real S3 storage on the local MinIO, with fresh public and private buckets.

    Start it with `docker compose up -d minio`. CI sets REQUIRE_S3_TESTS=1, which
    turns a missing MinIO into a failure instead of a skip.
    """
    import uuid

    import boto3
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError

    client = boto3.client(
        "s3",
        endpoint_url=S3_TEST_ENDPOINT,
        aws_access_key_id=S3_TEST_KEY,
        aws_secret_access_key=S3_TEST_SECRET,
        region_name="us-east-1",
        config=Config(
            connect_timeout=2, retries={"max_attempts": 1}, s3={"addressing_style": "path"}
        ),
    )
    try:
        client.list_buckets()
    except (BotoCoreError, ClientError) as exc:
        if os.environ.get("REQUIRE_S3_TESTS"):
            pytest.fail(f"MinIO is required here but unreachable: {exc}")
        pytest.skip("MinIO is not running (docker compose up -d minio)")

    run = uuid.uuid4().hex[:10]
    public, private = f"t{run}-public", f"t{run}-private"
    client.create_bucket(Bucket=public)
    client.create_bucket(Bucket=private)
    client.put_bucket_policy(
        Bucket=public,
        Policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": ["*"]},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{public}/*"],
                    }
                ],
            }
        ),
    )
    settings.STORAGE_BACKEND = "s3"
    settings.S3_ENDPOINT_URL = S3_TEST_ENDPOINT
    settings.S3_BROWSER_ENDPOINT_URL = S3_TEST_ENDPOINT
    settings.S3_REGION = "us-east-1"
    settings.S3_ACCESS_KEY_ID = S3_TEST_KEY
    settings.S3_SECRET_ACCESS_KEY = S3_TEST_SECRET
    settings.S3_PUBLIC_BUCKET = public
    settings.S3_PRIVATE_BUCKET = private
    settings.S3_PUBLIC_BASE_URL = f"{S3_TEST_ENDPOINT}/{public}"
    settings.S3_ADDRESSING_STYLE = "path"
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {"BACKEND": "apps.core.storage.PublicS3Storage"},
        "private": {"BACKEND": "apps.core.storage.PrivateS3Storage"},
    }
    settings.PRIVATE_MEDIA_ROOT = tmp_path / "unused-private"

    def keys(bucket, prefix=""):
        pages = client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix)
        return sorted(item["Key"] for page in pages for item in page.get("Contents", []))

    yield type("S3", (), {"client": client, "public": public, "private": private, "keys": keys})

    for bucket in (public, private):
        for key in keys(bucket):
            client.delete_object(Bucket=bucket, Key=key)
        client.delete_bucket(Bucket=bucket)
