"""Django settings for the rose project.

Every value that differs between environments is read from the environment
(or a local `.env` file) through django-environ.

DJANGO_ENV names the environment: development (the default), test, e2e,
staging or production. HTTPS-only cookies, HSTS and redirects are on for
staging and production, and apps.core.checks refuses to start those two with
anything unsafe (see docs/ops/security.md).
"""

import re
from pathlib import Path
from urllib.parse import urlsplit

import environ
from celery.schedules import crontab
from csp.constants import NONE, SELF
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BASE_DIR.parent

env = environ.Env(
    DJANGO_ENV=(str, "development"),
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, []),
    DJANGO_CSRF_TRUSTED_ORIGINS=(list, []),
    DJANGO_ADMIN_PATH=(str, "admin/"),
    DJANGO_SECURE_SSL_REDIRECT=(bool, True),
    DJANGO_TRUSTED_PROXY_COUNT=(int, 0),
    CONTACT_RATE_LIMIT=(str, "5/h"),
    LOGIN_RATE_LIMIT_IP=(str, "20/h"),
    LOGIN_RATE_LIMIT_EMAIL=(str, "10/h"),
    REGISTER_RATE_LIMIT_IP=(str, "5/h"),
    REGISTER_RATE_LIMIT_EMAIL=(str, "3/h"),
    PASSWORD_RESET_RATE_LIMIT_IP=(str, "5/h"),
    PASSWORD_RESET_RATE_LIMIT_EMAIL=(str, "3/h"),
    RSVP_RETENTION_DAYS=(int, 30),
    CONTACT_RETENTION_DAYS=(int, 365),
    FEED_ENABLED=(bool, True),
    FEED_WATERMARK=(bool, True),
    FEED_WATERMARK_OPACITY=(float, 0.06),
    FEED_WATERMARK_SPACING=(float, 0.34),
    FEED_PREMODERATION_POSTS=(int, 3),
    FEED_MAX_POSTS_PER_DAY=(int, 10),
    FEED_MAX_COMMENTS_PER_HOUR=(int, 60),
    MEMBERSHIP_GRACE_DAYS=(int, 7),
    MEMBERSHIP_PENDING_EXPIRY_DAYS=(int, 30),
    MERCHANT_DISPLAY_NAME=(str, "Rose"),
    RENTAL_RETENTION_DAYS=(int, 90),
    VOLUNTEER_RETENTION_DAYS=(int, 365),
    NEWSLETTER_SUPPRESS_AFTER_DAYS=(int, 30),
    CELERY_TASK_ALWAYS_EAGER=(bool, False),
    EMAIL_PROVIDER=(str, "console"),
    EMAIL_SENDER_NAME=(str, "Rose"),
    STORAGE_BACKEND=(str, "local"),
    S3_SIGNED_URL_SECONDS=(int, 60),
    PASSWORD_BREACH_CHECK=(bool, False),
    MEMBER_SESSION_DAYS=(int, 14),
    STAFF_SESSION_HOURS=(int, 12),
    BACKUP_ENABLED=(bool, False),
    BACKUP_RETENTION_DAYS=(int, 30),
    SITE_INDEXABLE=(bool, None),
)
environ.Env.read_env(BASE_DIR / ".env")

DJANGO_ENV = env("DJANGO_ENV")
DEPLOYED_ENVS = ("staging", "production")
IS_DEPLOYED = DJANGO_ENV in DEPLOYED_ENVS

# Whether search engines may index the public pages (robots.txt). Production
# only by default; staging is always closed whatever this says.
SITE_INDEXABLE = env("SITE_INDEXABLE")
if SITE_INDEXABLE is None:
    SITE_INDEXABLE = DJANGO_ENV == "production"

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    # The admin's look (Rose-themed in config/unfold.py); before the admin itself. The
    # basic config leaves the admin site to RoseAdminSite (the default one replaces it).
    "unfold.apps.BasicAppConfig",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "apps.core.apps.RoseAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    # Before staticfiles, so its development `runserver` (which migrates first) is the one used.
    "apps.core",
    "django.contrib.staticfiles",
    # Form widgets render through TEMPLATES (FORM_RENDERER below), so project overrides apply.
    "django.forms",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "anymail",
    "rest_framework",
    "django_filters",
    "csp",
    "django_ratelimit",
    "apps.accounts",
    "apps.pages",
    "apps.education",
    "apps.contact",
    "apps.events",
    "apps.journal",
    "apps.feed",
    "apps.memberships",
    "apps.rentals",
    "apps.volunteers",
    "apps.donations",
    "apps.newsletter",
    "apps.safety",
]

MIDDLEWARE = [
    "apps.core.middleware.HealthCheckMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "apps.core.middleware.StagingGateMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "apps.pages.middleware.OldSiteRedirectMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "apps.accounts.middleware.SessionPolicyMiddleware",
    "apps.accounts.session_tracking.SessionSeenMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    "apps.core.middleware.PrivacyHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.age_check_banner",
            ],
        },
    },
]

# Widgets render through the project's templates, so the admin's widget overrides
# (templates/unfold/widgets) apply.
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = 60

CACHES = {"default": env.cache("CACHE_URL", default="locmemcache://")}
CACHES["default"]["KEY_PREFIX"] = "cache"

AUTH_USER_MODEL = "accounts.User"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        "OPTIONS": {"user_attributes": ("email", "display_name", "legal_name")},
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    # Off unless PASSWORD_BREACH_CHECK is true; see docs/ops/security.md.
    {"NAME": "apps.accounts.breach.BreachedPasswordValidator"},
]
PASSWORD_BREACH_CHECK = env("PASSWORD_BREACH_CHECK")
PASSWORD_BREACH_API = "https://api.pwnedpasswords.com/range/"
PASSWORD_BREACH_TIMEOUT_SECONDS = 3

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Chicago"
USE_I18N = True
USE_TZ = True

# --- Static files and the single-page app ---------------------------------
# Django serves the built React app itself (WhiteNoise), so the site, API,
# admin and media views share one origin. See apps.core.spa.
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
FRONTEND_DIST = Path(env.str("FRONTEND_DIST", default=str(REPO_DIR / "frontend" / "dist")))
WHITENOISE_ROOT = FRONTEND_DIST if FRONTEND_DIST.is_dir() else None
WHITENOISE_INDEX_FILE = False
WHITENOISE_KEEP_ONLY_HASHED_FILES = True


def whitenoise_immutable(path, url):
    """Vite's hashed /assets/ and Django's manifest-hashed static files never change."""
    return url.startswith("/assets/") or bool(re.search(r"\.[0-9a-f]{12}\.", url))


WHITENOISE_IMMUTABLE_FILE_TEST = whitenoise_immutable

# --- Media storage ----------------------------------------------------------
# "local" keeps files on disk (development and tests). "s3" uses two
# S3-compatible buckets (Cloudflare R2 by default; see docs/ops/storage.md):
# a public one for site, journal, education and event images, and a private
# one for member images, watermarked copies, exports and backups.
STORAGE_BACKEND = env("STORAGE_BACKEND")
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env.str("DJANGO_MEDIA_ROOT", default=str(BASE_DIR / "media")))
# Member uploads live here locally. Nothing under it is ever served by URL;
# only by access-checked views (apps.core.private_media).
PRIVATE_MEDIA_ROOT = Path(env.str("PRIVATE_MEDIA_ROOT", default=str(BASE_DIR / "private_media")))

S3_ENDPOINT_URL = env("S3_ENDPOINT_URL", default="")
S3_REGION = env("S3_REGION", default="auto")
S3_ACCESS_KEY_ID = env("S3_ACCESS_KEY_ID", default="")
S3_SECRET_ACCESS_KEY = env("S3_SECRET_ACCESS_KEY", default="")
S3_PUBLIC_BUCKET = env("S3_PUBLIC_BUCKET", default="")
S3_PRIVATE_BUCKET = env("S3_PRIVATE_BUCKET", default="")
# Where the public bucket is reachable by browsers: a custom domain or the
# provider's public bucket URL, without a trailing slash.
S3_PUBLIC_BASE_URL = env("S3_PUBLIC_BASE_URL", default="").rstrip("/")
# Signed URLs for private files must be fetchable by the browser; MinIO in
# Docker is reached on a different host name than the one the app uses.
S3_BROWSER_ENDPOINT_URL = env("S3_BROWSER_ENDPOINT_URL", default="") or S3_ENDPOINT_URL
S3_ADDRESSING_STYLE = env("S3_ADDRESSING_STYLE", default="virtual")
S3_SIGNED_URL_SECONDS = env("S3_SIGNED_URL_SECONDS")
# A signed URL outlives the access check that issued it (a revoked ID check, a ban), so it
# must expire quickly: every request to the media view checks access again.
if not 1 <= S3_SIGNED_URL_SECONDS <= 60:
    raise ImproperlyConfigured("S3_SIGNED_URL_SECONDS must be between 1 and 60.")

if STORAGE_BACKEND == "s3":
    STORAGES = {
        "default": {"BACKEND": "apps.core.storage.PublicS3Storage"},
        "private": {"BACKEND": "apps.core.storage.PrivateS3Storage"},
    }
    SITE_IMAGES_URL = f"{S3_PUBLIC_BASE_URL}/site/"
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "private": {"BACKEND": "apps.core.private_media.PrivateFileSystemStorage"},
    }
    SITE_IMAGES_URL = "/images/"
STORAGES["staticfiles"] = {
    "BACKEND": (
        "django.contrib.staticfiles.storage.StaticFilesStorage"
        if DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage"
    )
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Site imagery: fetched into the frontend's public folder, uploaded to the
# public bucket under site/ by migrate_media_to_storage.
IMAGE_MANIFEST_PATH = Path(
    env.str("IMAGE_MANIFEST_PATH", default=str(REPO_DIR / "docs" / "image-manifest.json"))
)
SITE_IMAGES_DIR = Path(
    env.str("SITE_IMAGES_DIR", default=str(REPO_DIR / "frontend" / "public" / "images"))
)

# Uploads: size and pixel caps, and the formats accepted (checked by magic bytes).
UPLOAD_MAX_BYTES = 15 * 1024 * 1024
UPLOAD_MAX_PIXELS = 40_000_000
UPLOAD_MAX_SIDE = 12_000
DATA_UPLOAD_MAX_MEMORY_SIZE = 2_621_440
FILE_UPLOAD_MAX_MEMORY_SIZE = 2_621_440

ADMIN_PATH = env("DJANGO_ADMIN_PATH")

# --- REST framework -------------------------------------------------------
# JSON only: the browsable API renders HTML forms and would need its own CSP
# exceptions, so it stays off everywhere.
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "UNAUTHENTICATED_USER": "django.contrib.auth.models.AnonymousUser",
}

# --- Email ----------------------------------------------------------------
# EMAIL_PROVIDER picks the backend: console (development), smtp (EMAIL_URL),
# or a transactional provider through django-anymail: postmark, amazon_ses,
# resend or mailgun. See docs/ops/email.md.
EMAIL_PROVIDER = env("EMAIL_PROVIDER")
EMAIL_PROVIDERS = {
    "console": "django.core.mail.backends.console.EmailBackend",
    "locmem": "django.core.mail.backends.locmem.EmailBackend",
    "smtp": "django.core.mail.backends.smtp.EmailBackend",
    "postmark": "anymail.backends.postmark.EmailBackend",
    "amazon_ses": "anymail.backends.amazon_ses.EmailBackend",
    "resend": "anymail.backends.resend.EmailBackend",
    "mailgun": "anymail.backends.mailgun.EmailBackend",
}
EMAIL_BACKEND = EMAIL_PROVIDERS[EMAIL_PROVIDER]
if EMAIL_PROVIDER == "smtp":
    _smtp = env.email("EMAIL_URL", default="smtp://localhost:25")
    _smtp.pop("EMAIL_BACKEND", None)
    vars().update(_smtp)
ANYMAIL = {
    key: value
    for key, value in {
        "POSTMARK_SERVER_TOKEN": env("POSTMARK_SERVER_TOKEN", default=""),
        "RESEND_API_KEY": env("RESEND_API_KEY", default=""),
        "MAILGUN_API_KEY": env("MAILGUN_API_KEY", default=""),
        "MAILGUN_SENDER_DOMAIN": env("MAILGUN_SENDER_DOMAIN", default=""),
        "MAILGUN_API_URL": env("MAILGUN_API_URL", default="https://api.mailgun.net/v3"),
        # No open or click tracking: it would tie a member's reading to their address.
        "SEND_DEFAULTS": {"track_clicks": False, "track_opens": False},
        "AMAZON_SES_CLIENT_PARAMS": {
            "region_name": env("SES_REGION", default="us-east-1"),
            "aws_access_key_id": env("SES_ACCESS_KEY_ID", default="") or None,
            "aws_secret_access_key": env("SES_SECRET_ACCESS_KEY", default="") or None,
        },
    }.items()
    if value != ""
}
EMAIL_TIMEOUT = 15
EMAIL_SENDER_NAME = env("EMAIL_SENDER_NAME")
EMAIL_SENDER_ADDRESS = env("EMAIL_SENDER_ADDRESS", default="no-reply@localhost")
DEFAULT_FROM_EMAIL = f"{EMAIL_SENDER_NAME} <{EMAIL_SENDER_ADDRESS}>"
SERVER_EMAIL = DEFAULT_FROM_EMAIL
# Django's error emails include request data, so they are never sent.
ADMINS = []
MANAGERS = []
CONTACT_NOTIFY_EMAIL = env("CONTACT_NOTIFY_EMAIL", default="")

# --- Accounts -------------------------------------------------------------
# Public origin of the site, used to build links in emails. The admin shares
# it (one origin), so staff links in notifications point there too.
SITE_URL = env("SITE_URL", default="http://localhost:5173").rstrip("/")
ADMIN_BASE_URL = env("ADMIN_BASE_URL", default=SITE_URL).rstrip("/")
EMAIL_VERIFICATION_MAX_AGE = 60 * 60 * 24 * 3
PASSWORD_RESET_TIMEOUT = 60 * 60 * 2
LOGIN_LOCKOUT_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 15 * 60

# Staff two-factor (TOTP plus single-use backup codes) for the whole admin.
OTP_TOTP_ISSUER = env("OTP_ISSUER", default="Rose")
OTP_BACKUP_CODE_COUNT = 10
# The device admin never shows an authenticator's secret key, QR code or backup codes.
OTP_ADMIN_HIDE_SENSITIVE_DATA = True

# --- Events ---------------------------------------------------------------
RSVP_RETENTION_DAYS = env("RSVP_RETENTION_DAYS")

# --- Contact --------------------------------------------------------------
CONTACT_RETENTION_DAYS = env("CONTACT_RETENTION_DAYS")

# --- Member feed ----------------------------------------------------------
# Kill switch: false makes every feed path answer 404 (docs/ops/incident.md).
FEED_ENABLED = env("FEED_ENABLED")
FEED_WATERMARK = env("FEED_WATERMARK")
# How strongly the viewer's name shows (0 to 1), and how far apart the marks are, as a
# share of the image width: 0.34 gives about three marks across.
FEED_WATERMARK_OPACITY = env("FEED_WATERMARK_OPACITY")
FEED_WATERMARK_SPACING = env("FEED_WATERMARK_SPACING")
if not 0 < FEED_WATERMARK_OPACITY <= 1:
    raise ImproperlyConfigured("FEED_WATERMARK_OPACITY must be above 0 and at most 1.")
if not 0.1 <= FEED_WATERMARK_SPACING <= 1:
    raise ImproperlyConfigured("FEED_WATERMARK_SPACING must be between 0.1 and 1.")
FEED_PREMODERATION_POSTS = env("FEED_PREMODERATION_POSTS")
FEED_MAX_POSTS_PER_DAY = env("FEED_MAX_POSTS_PER_DAY")
FEED_MAX_COMMENTS_PER_HOUR = env("FEED_MAX_COMMENTS_PER_HOUR")
FEED_WARNING_COOLDOWN_HOURS = 24

# seed_demo's one password for every demo account, so the README can list the logins.
# Used only with DEBUG on; seed_demo never runs in staging or production.
DEMO_PASSWORD = env.str("DEMO_PASSWORD", default="rose-demo-only")

# Development only: treat team members as having passed the staff two-step login, to try
# the staff section without an authenticator. Honoured only with DEBUG on outside staging
# and production, and the deployment check refuses to start a deployed site with it set.
DEV_SKIP_STAFF_2FA = env.bool("DEV_SKIP_STAFF_2FA", default=False)
FEED_EXPORT_TTL_HOURS = 24
FEED_MAX_IMAGES_PER_POST = 10
DATA_UPLOAD_MAX_NUMBER_FILES = 12
WATERMARK_RETENTION_DAYS = 7

# --- Membership and payments ----------------------------------------------
# "manual" (pay at the door) is always on. "sandbox" is development only and
# refuses to start with DEBUG off. A real processor is one more key here.
PAYMENT_PROVIDERS = env.list(
    "PAYMENT_PROVIDERS", default=["manual", "sandbox"] if DEBUG else ["manual"]
)
MEMBERSHIP_GRACE_DAYS = env("MEMBERSHIP_GRACE_DAYS")
MEMBERSHIP_PENDING_EXPIRY_DAYS = env("MEMBERSHIP_PENDING_EXPIRY_DAYS")
MEMBERSHIP_REMINDER_DAYS = (14, 3)
# Shown on receipts and set as the billing descriptor with any processor. Keep it neutral.
MERCHANT_DISPLAY_NAME = env("MERCHANT_DISPLAY_NAME")
PAYMENT_WEBHOOK_RATE_LIMIT = "120/m"

# --- Rentals, volunteers, giving and the email list --------------------------
# Declined and cancelled rental inquiries keep only type, date and status after this.
RENTAL_RETENTION_DAYS = env("RENTAL_RETENTION_DAYS")
# Signups that went nowhere (new or inactive, untouched) are deleted after this.
VOLUNTEER_RETENTION_DAYS = env("VOLUNTEER_RETENTION_DAYS")
DONATION_MINIMUM_CENTS = 500
DONATION_MAXIMUM_CENTS = 1_000_000
DONATION_PRESETS_CENTS = [2500, 5000, 10000, 25000]
# Unfinished online gifts are forgotten after this; unsent acknowledgement emails after the next.
DONATION_CHECKOUT_RETENTION_DAYS = 7
DONATION_ACK_EMAIL_RETENTION_DAYS = 30
# Unsubscribed addresses become a hash-only suppression record after this.
NEWSLETTER_SUPPRESS_AFTER_DAYS = env("NEWSLETTER_SUPPRESS_AFTER_DAYS")
NEWSLETTER_PENDING_DAYS = 7
NEWSLETTER_BATCH_SIZE = 100

# --- Site content -------------------------------------------------------------
# Drafted copy (YAML) for load_site_content. Kept out of git; see docs/content.md.
SITE_CONTENT_DIR = Path(env.str("SITE_CONTENT_DIR", default=str(REPO_DIR / "content")))
STAFF_GUIDE_PATH = Path(
    env.str("STAFF_GUIDE_PATH", default=str(REPO_DIR / "docs" / "staff-guide.md"))
)

# --- Backups --------------------------------------------------------------
# Nightly pg_dump, encrypted on the server with an age public key (the private
# key is never here), uploaded to the private bucket under backups/.
BACKUP_ENABLED = env("BACKUP_ENABLED")
BACKUP_AGE_RECIPIENT = env("BACKUP_AGE_RECIPIENT", default="")
BACKUP_RETENTION_DAYS = env("BACKUP_RETENTION_DAYS")
PG_DUMP_PATH = env("PG_DUMP_PATH", default="pg_dump")

# --- Celery ---------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6380/0")
CELERY_TASK_ALWAYS_EAGER = env("CELERY_TASK_ALWAYS_EAGER")
CELERY_TASK_IGNORE_RESULT = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
CELERY_BEAT_SCHEDULE = {
    "send-event-reminders": {
        "task": "apps.events.tasks.send_due_reminders",
        "schedule": 15 * 60,
    },
    "purge-old-rsvps": {
        "task": "apps.events.tasks.purge_expired_rsvps",
        "schedule": 60 * 60 * 6,
    },
    "purge-expired-exports": {
        "task": "apps.feed.tasks.purge_expired_exports",
        "schedule": 60 * 60,
    },
    "purge-old-watermarks": {
        "task": "apps.feed.tasks.purge_old_watermarks",
        "schedule": crontab(hour=4, minute=30),
    },
    "purge-old-contact-messages": {
        "task": "apps.contact.tasks.purge_old_messages",
        "schedule": crontab(hour=5, minute=0),
    },
    "membership-lifecycle": {
        "task": "apps.memberships.tasks.run_lifecycle",
        "schedule": crontab(hour=6, minute=0),
    },
    "purge-membership-usage": {
        "task": "apps.memberships.tasks.purge_old_usage",
        "schedule": crontab(hour=6, minute=30),
    },
    "send-scheduled-newsletters": {
        "task": "apps.newsletter.tasks.send_scheduled_newsletters",
        "schedule": 5 * 60,
    },
    "purge-email-list": {
        "task": "apps.newsletter.tasks.purge_subscribers",
        "schedule": crontab(hour=5, minute=15),
    },
    "purge-rental-contacts": {
        "task": "apps.rentals.tasks.purge_closed_inquiries",
        "schedule": crontab(hour=5, minute=30),
    },
    "purge-volunteer-signups": {
        "task": "apps.volunteers.tasks.purge_old_signups",
        "schedule": crontab(hour=5, minute=45),
    },
    "purge-donation-contacts": {
        "task": "apps.donations.tasks.purge_donation_contacts",
        "schedule": crontab(hour=6, minute=15),
    },
    "purge-stale-sessions": {
        "task": "apps.accounts.tasks.purge_stale_sessions",
        "schedule": crontab(hour=4, minute=45),
    },
    "nightly-backup": {
        "task": "apps.core.tasks.nightly_backup",
        "schedule": crontab(hour=3, minute=15),
    },
}

# --- Rate limiting --------------------------------------------------------
# Every limit is listed in docs/ops/security.md.
CONTACT_RATE_LIMIT = env("CONTACT_RATE_LIMIT")
LOGIN_RATE_LIMIT_IP = env("LOGIN_RATE_LIMIT_IP")
LOGIN_RATE_LIMIT_EMAIL = env("LOGIN_RATE_LIMIT_EMAIL")
REGISTER_RATE_LIMIT_IP = env("REGISTER_RATE_LIMIT_IP")
REGISTER_RATE_LIMIT_EMAIL = env("REGISTER_RATE_LIMIT_EMAIL")
PASSWORD_RESET_RATE_LIMIT_IP = env("PASSWORD_RESET_RATE_LIMIT_IP")
PASSWORD_RESET_RATE_LIMIT_EMAIL = env("PASSWORD_RESET_RATE_LIMIT_EMAIL")
# Default for every other write endpoint, per endpoint and per account (or IP).
WRITE_RATE_LIMIT = "120/h"
ACCOUNT_WRITE_RATE_LIMIT = "30/h"
TOKEN_RATE_LIMIT = "30/h"
ADMIN_LOGIN_RATE_LIMIT_IP = "20/h"
RENTAL_INQUIRY_RATE_LIMIT = "5/h"
VOLUNTEER_RATE_LIMIT = "5/h"
DONATION_RATE_LIMIT = "10/h"
NEWSLETTER_RATE_LIMIT_IP = "10/h"
NEWSLETTER_RATE_LIMIT_EMAIL = "3/h"
TRUSTED_PROXY_COUNT = env("DJANGO_TRUSTED_PROXY_COUNT")
RATELIMIT_USE_CACHE = "default"

# --- Sessions -------------------------------------------------------------
# Members: idle sessions end after MEMBER_SESSION_DAYS. Staff: at most
# STAFF_SESSION_HOURS, and when the browser closes (apps.accounts.middleware).
SESSION_COOKIE_AGE = 60 * 60 * 24 * env("MEMBER_SESSION_DAYS")
SESSION_SAVE_EVERY_REQUEST = True
STAFF_SESSION_SECONDS = 60 * 60 * env("STAFF_SESSION_HOURS")

# --- Cookies and transport security ---------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"
CSRF_FAILURE_VIEW = "apps.core.views.csrf_failure"
SECURE_CONTENT_TYPE_NOSNIFF = True
# no-referrer everywhere except the admin, where Django's own forms post with
# an Origin header that no-referrer would turn into "null" (decision 174).
SECURE_REFERRER_POLICY = "no-referrer"
ADMIN_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

if DEBUG:
    # Local development may run without Redis; the ratelimit checks would
    # otherwise refuse to start. Deployed environments keep these checks.
    SILENCED_SYSTEM_CHECKS = ["django_ratelimit.E003", "django_ratelimit.W001"]
else:
    SILENCED_SYSTEM_CHECKS = ["django_ratelimit.W001"]

if IS_DEPLOYED:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env("DJANGO_SECURE_SSL_REDIRECT")
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # Render's health checks call /healthz over plain HTTP inside its network.
    SECURE_REDIRECT_EXEMPT = [r"^healthz$"]

# --- Staging gate -----------------------------------------------------------
STAGING_BASIC_AUTH_USER = env("STAGING_BASIC_AUTH_USER", default="")
STAGING_BASIC_AUTH_PASSWORD = env("STAGING_BASIC_AUTH_PASSWORD", default="")

# --- Admin appearance ------------------------------------------------------
from config.unfold import UNFOLD  # noqa: E402, F401  (read by django-unfold)

# --- Content Security Policy ----------------------------------------------
# One policy for the app, API and admin. No inline scripts or styles anywhere,
# so neither nonces nor 'unsafe-inline' are needed. The one exception is by hash:
# the admin's rich-text editor (Trix 2.1.1, served by Unfold) adds two fixed <style>
# elements for its own layout (one created empty, then filled). Nothing else can match.
TRIX_STYLE_HASHES = [
    "'sha256-47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU='",
    "'sha256-JDgngvYGBXjCEm5edwNK0gSIH1v4MowQ29dRjjv54IY='",
    "'sha256-jAP18ioNeNaQBBU5RJvT96kjJnVxHvZs+s8WUNiLnvA='",
]


def _origin(url):
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}" if parts.scheme and parts.netloc else None


MEDIA_ORIGINS = sorted(
    {origin for origin in (_origin(S3_PUBLIC_BASE_URL), _origin(S3_BROWSER_ENDPOINT_URL)) if origin}
    if STORAGE_BACKEND == "s3"
    else set()
)
# The admin's two-step login redirects back to the site after its form is sent; in
# development the site runs on another origin (Vite), so it is allowed here. In
# production the site and the admin share one origin and this adds nothing.
FORM_ORIGINS = [origin for origin in {_origin(SITE_URL)} if origin]
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [SELF],
        "script-src": [SELF],
        "style-src": [SELF, *TRIX_STYLE_HASHES],
        "img-src": [SELF, "data:", "blob:", *MEDIA_ORIGINS],
        "font-src": [SELF],
        "connect-src": [SELF],
        "media-src": [SELF],
        "object-src": [NONE],
        "base-uri": [SELF],
        "form-action": [SELF, *FORM_ORIGINS],
        "frame-ancestors": [NONE],
        "manifest-src": [SELF],
        "worker-src": [NONE],
    }
}

# --- Logging --------------------------------------------------------------
# JSON lines on stdout. Every record passes through the privacy scrubber
# (apps.core.logging), and nothing is ever emailed.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"scrub": {"()": "apps.core.logging.ScrubFilter"}},
    "formatters": {"json": {"()": "apps.core.logging.JsonFormatter"}},
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["scrub"],
        }
    },
    "root": {"handlers": ["stdout"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["stdout"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["stdout"], "level": "WARNING", "propagate": False},
        "django.server": {"handlers": ["stdout"], "level": "INFO", "propagate": False},
        "celery": {"handlers": ["stdout"], "level": "INFO", "propagate": False},
    },
}

# --- Error tracking (off by default) --------------------------------------
# Leaving SENTRY_DSN unset is the recommended default; see docs/ops/security.md.
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    from apps.core.logging import init_sentry

    init_sentry(SENTRY_DSN, environment=DJANGO_ENV)
