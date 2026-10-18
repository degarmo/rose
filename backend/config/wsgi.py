"""WSGI entry point. Staging and production refuse to start if a safety check fails."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()

from apps.core.checks import assert_deploy_safe  # noqa: E402  (needs Django set up)

assert_deploy_safe()
