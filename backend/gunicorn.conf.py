"""Gunicorn settings for staging and production (the web service in render.yaml).

The access log has no client address, no query string and no user agent, and
every line goes through the same privacy scrubber as the application logs.
"""

import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
timeout = 30
graceful_timeout = 20
forwarded_allow_ips = "*"
accesslog = "-"
errorlog = "-"
access_log_format = "%(m)s %(U)s %(s)s %(B)s %(M)sms"
logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"scrub": {"()": "apps.core.logging.ScrubFilter"}},
    "formatters": {"json": {"()": "apps.core.logging.JsonFormatter"}},
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["scrub"],
            "stream": "ext://sys.stdout",
        }
    },
    "loggers": {
        "gunicorn.error": {"handlers": ["stdout"], "level": "INFO", "propagate": False},
        "gunicorn.access": {"handlers": ["stdout"], "level": "INFO", "propagate": False},
    },
}
