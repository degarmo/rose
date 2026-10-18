"""Django settings for the rose project.

Every value that differs between environments is read from the environment
(or a local `.env` file) through django-environ. Production hardening is on
whenever DJANGO_DEBUG is false.
"""

from pathlib import Path

import environ
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
    EMAIL_SENDER_NAME=(str, "Rose"),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
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
        "DIRS": [],
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

AUTH_USER_MODEL = "accounts.User"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
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

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

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

# --- Rate limiting --------------------------------------------------------
CONTACT_RATE_LIMIT = env("CONTACT_RATE_LIMIT")
TRUSTED_PROXY_COUNT = env("DJANGO_TRUSTED_PROXY_COUNT")
RATELIMIT_USE_CACHE = "default"

# --- Cookies and transport security ---------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "no-referrer"
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
        "img-src": [SELF, "data:"],
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
