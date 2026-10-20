import base64
import binascii
import hmac

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError, connection
from django.http import HttpResponse

PRIVATE_PATH_PREFIXES = (
    "/api/",
    "/members",
    "/account",
    "/media/",
    "/join/confirming",
    "/dev/",
    "/subscribe",
    "/unsubscribe",
)
HEALTH_PATH = "/healthz"
PAYMENT_WEBHOOK_PREFIX = "/api/payments/webhook/"

DENY_ALL = (
    "accelerometer=(), autoplay=(), browsing-topics=(), camera=(), display-capture=(), "
    "fullscreen=(self), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), "
    "midi=(), payment=(), publickey-credentials-get=(), usb=(), xr-spatial-tracking=()"
)
CAMERA_SELF = DENY_ALL.replace("camera=()", "camera=(self)")


def admin_prefix():
    return f"/{settings.ADMIN_PATH.strip('/')}/"


# The door desk (the staff section's, in the member app). Links to it load the page
# afresh, so this document's policy (camera allowed) is the one in force while it is open.
# It is the only page that may use the camera.
STAFF_DOOR_PATH = "/members/staff/door"


class HealthCheckMiddleware:
    """`/healthz`: 200 "ok" when the database and Redis answer, 503 otherwise. No details.

    It runs first, before host validation and the staging gate, so the hosting
    platform's internal checks always reach it.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path != HEALTH_PATH:
            return self.get_response(request)
        healthy = True
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except DatabaseError:
            healthy = False
        try:
            cache.set("healthz", "1", timeout=10)
            healthy = healthy and cache.get("healthz") == "1"
        except Exception:  # any cache client error means unhealthy, nothing more to say
            healthy = False
        response = HttpResponse(
            "ok" if healthy else "unavailable",
            status=200 if healthy else 503,
            content_type="text/plain",
        )
        response["Cache-Control"] = "no-store"
        return response


class StagingGateMiddleware:
    """Staging only: HTTP basic auth on every path except /healthz and payment
    webhooks, and noindex on every response."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.active = settings.DJANGO_ENV == "staging"

    def __call__(self, request):
        if not self.active:
            return self.get_response(request)
        exempt = request.path == HEALTH_PATH or request.path.startswith(PAYMENT_WEBHOOK_PREFIX)
        if exempt or self._authorised(request):
            response = self.get_response(request)
        else:
            response = HttpResponse(
                "Authorisation required.", status=401, content_type="text/plain"
            )
            response["WWW-Authenticate"] = 'Basic realm="staging", charset="UTF-8"'
        response["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        return response

    def _authorised(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        scheme, _, encoded = header.partition(" ")
        if scheme.lower() != "basic" or not encoded:
            return False
        try:
            user, _, password = base64.b64decode(encoded).decode().partition(":")
        except (binascii.Error, UnicodeDecodeError):
            return False
        expected_user = settings.STAGING_BASIC_AUTH_USER
        expected_password = settings.STAGING_BASIC_AUTH_PASSWORD
        if not (expected_user and expected_password):
            return False
        return hmac.compare_digest(user, expected_user) & hmac.compare_digest(
            password, expected_password
        )


class PrivacyHeadersMiddleware:
    """The final header policy for every response.

    - X-Robots-Tag on every private or machine-facing path and the admin.
    - Cache-Control: no-store on the API unless a view set something stricter.
    - Permissions-Policy denies every device feature; only the door desk (the staff
      section's) may use the camera, to scan reference codes.
    - Referrer-Policy is no-referrer, except the admin (decision 174).
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.admin = admin_prefix()
        self.private = PRIVATE_PATH_PREFIXES + (self.admin,)

    def __call__(self, request):
        response = self.get_response(request)
        path = request.path
        if path.startswith(self.private):
            response["X-Robots-Tag"] = "noindex, nofollow"
        if path.startswith("/api/"):
            response["Cache-Control"] = response.get("Cache-Control", "no-store")
        door = path in (STAFF_DOOR_PATH, f"{STAFF_DOOR_PATH}/")
        response["Permissions-Policy"] = CAMERA_SELF if door else DENY_ALL
        if path.startswith(self.admin):
            response["Referrer-Policy"] = settings.ADMIN_REFERRER_POLICY
        response.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        return response
