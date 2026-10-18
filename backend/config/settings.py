"""Django settings for the rose project.

Every value that differs between environments is read from the environment
(or a local `.env` file) through django-environ. Production hardening is on
whenever DJANGO_DEBUG is false.
"""

from pathlib import Path

import environ
from celery.schedules import crontab
from csp.constants import NONE, SELF

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
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
    FEED_WATERMARK=(bool, True),
    FEED_PREMODERATION_POSTS=(int, 3),
    FEED_MAX_POSTS_PER_DAY=(int, 10),
    FEED_MAX_COMMENTS_PER_HOUR=(int, 60),
    MEMBERSHIP_GRACE_DAYS=(int, 7),
    MEMBERSHIP_PENDING_EXPIRY_DAYS=(int, 30),
    MERCHANT_DISPLAY_NAME=(str, "Rose"),
    CELERY_TASK_ALWAYS_EAGER=(bool, False),
    EMAIL_SENDER_NAME=(str, "Rose"),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "apps.core.apps.RoseAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "csp",
    "django_ratelimit",
    "apps.core",
    "apps.accounts",
    "apps.pages",
    "apps.education",
    "apps.contact",
    "apps.events",
    "apps.journal",
    "apps.feed",
    "apps.memberships",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
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
            ],
        },
    },
]

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
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Chicago"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = env.path("DJANGO_MEDIA_ROOT", default=BASE_DIR / "media")
# Member uploads live here. Nothing under it is ever served by URL; only by
# access-checked views (apps.core.private_media).
PRIVATE_MEDIA_ROOT = Path(env.str("PRIVATE_MEDIA_ROOT", default=str(BASE_DIR / "private_media")))

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "private": {"BACKEND": "apps.core.private_media.PrivateFileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Watermarked image variants: short-lived, per viewer, on private disk, never in
# Redis (which also carries the task queue and must not fill up).
CACHES["watermarks"] = {
    "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
    "LOCATION": str(PRIVATE_MEDIA_ROOT / "watermark-cache"),
    "TIMEOUT": 600,
    "OPTIONS": {"MAX_ENTRIES": 2000},
}

# Site imagery lives in the repository, outside the backend folder.
IMAGE_MANIFEST_PATH = env.path(
    "IMAGE_MANIFEST_PATH", default=BASE_DIR.parent / "docs" / "image-manifest.json"
)
SITE_IMAGES_DIR = env.path(
    "SITE_IMAGES_DIR", default=BASE_DIR.parent / "frontend" / "public" / "images"
)

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
EMAIL_CONFIG = env.email("EMAIL_URL", default="consolemail://")
vars().update(EMAIL_CONFIG)
EMAIL_SENDER_NAME = env("EMAIL_SENDER_NAME")
EMAIL_SENDER_ADDRESS = env("EMAIL_SENDER_ADDRESS", default="no-reply@localhost")
DEFAULT_FROM_EMAIL = f"{EMAIL_SENDER_NAME} <{EMAIL_SENDER_ADDRESS}>"
SERVER_EMAIL = DEFAULT_FROM_EMAIL
CONTACT_NOTIFY_EMAIL = env("CONTACT_NOTIFY_EMAIL", default="")
ADMIN_BASE_URL = env("ADMIN_BASE_URL", default="http://localhost:8000")

# --- Accounts -------------------------------------------------------------
# Public origin of the site, used to build links in emails.
SITE_URL = env("SITE_URL", default="http://localhost:5173").rstrip("/")
EMAIL_VERIFICATION_MAX_AGE = 60 * 60 * 24 * 3
PASSWORD_RESET_TIMEOUT = 60 * 60 * 2
LOGIN_LOCKOUT_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 15 * 60

# --- Events ---------------------------------------------------------------
RSVP_RETENTION_DAYS = env("RSVP_RETENTION_DAYS")

# --- Member feed ----------------------------------------------------------
FEED_WATERMARK = env("FEED_WATERMARK")
FEED_PREMODERATION_POSTS = env("FEED_PREMODERATION_POSTS")
FEED_MAX_POSTS_PER_DAY = env("FEED_MAX_POSTS_PER_DAY")
FEED_MAX_COMMENTS_PER_HOUR = env("FEED_MAX_COMMENTS_PER_HOUR")
FEED_WARNING_COOLDOWN_HOURS = 24
FEED_EXPORT_TTL_HOURS = 24
FEED_MAX_IMAGES_PER_POST = 10
FEED_MAX_UPLOAD_BYTES = 15 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FILES = 12

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

# --- Celery ---------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6380/0")
CELERY_TASK_ALWAYS_EAGER = env("CELERY_TASK_ALWAYS_EAGER")
CELERY_TASK_IGNORE_RESULT = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
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
    "membership-lifecycle": {
        "task": "apps.memberships.tasks.run_lifecycle",
        "schedule": crontab(hour=6, minute=0),
    },
}

# --- Rate limiting --------------------------------------------------------
CONTACT_RATE_LIMIT = env("CONTACT_RATE_LIMIT")
LOGIN_RATE_LIMIT_IP = env("LOGIN_RATE_LIMIT_IP")
LOGIN_RATE_LIMIT_EMAIL = env("LOGIN_RATE_LIMIT_EMAIL")
REGISTER_RATE_LIMIT_IP = env("REGISTER_RATE_LIMIT_IP")
REGISTER_RATE_LIMIT_EMAIL = env("REGISTER_RATE_LIMIT_EMAIL")
PASSWORD_RESET_RATE_LIMIT_IP = env("PASSWORD_RESET_RATE_LIMIT_IP")
PASSWORD_RESET_RATE_LIMIT_EMAIL = env("PASSWORD_RESET_RATE_LIMIT_EMAIL")
TRUSTED_PROXY_COUNT = env("DJANGO_TRUSTED_PROXY_COUNT")
RATELIMIT_USE_CACHE = "default"

# --- Cookies and transport security ---------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"
CSRF_FAILURE_VIEW = "apps.core.views.csrf_failure"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

if DEBUG:
    # Local development may run without Redis; the ratelimit checks would
    # otherwise refuse to start. Production keeps these checks active.
    SILENCED_SYSTEM_CHECKS = ["django_ratelimit.E003", "django_ratelimit.W001"]
else:
    SILENCED_SYSTEM_CHECKS = ["django_ratelimit.W001"]
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env("DJANGO_SECURE_SSL_REDIRECT")
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# --- Content Security Policy ----------------------------------------------
# The API only ever returns JSON; the admin is the only HTML it serves.
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [SELF],
        "script-src": [SELF],
        "style-src": [SELF],
        "img-src": [SELF, "data:", "blob:"],
        "font-src": [SELF],
        "connect-src": [SELF],
        "object-src": [NONE],
        "base-uri": [SELF],
        "form-action": [SELF],
        "frame-ancestors": [NONE],
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
