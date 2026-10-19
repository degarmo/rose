"""Logs that cannot identify a member.

Every log record goes through ScrubFilter before it is written. It removes
email addresses, IP addresses, reference codes, session ids, cookies,
authorisation headers, typed signature names and any display name it can
attribute to the request, and it cuts query strings and member handles from
paths in the account, feed, membership and payment areas. Request bodies are
never logged at all. JsonFormatter writes one JSON object per line to stdout.

init_sentry() is used only if SENTRY_DSN is set; leaving it unset is the
recommended default (docs/ops/security.md).
"""

import json
import logging
import re
from datetime import UTC, datetime

REDACTED = "[redacted]"

EMAIL = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IPV6 = re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4}\b")
REFERENCE_CODE = re.compile(r"\b[2-9A-HJKMNP-Z]{3}-[2-9A-HJKMNP-Z]{3}\b")
SECRET_PAIRS = re.compile(
    r"(?i)\b(sessionid|csrftoken|csrfmiddlewaretoken|token|password|typed_name|"
    r"legal_name|display_name|email)(\"?\s*[:=]\s*\"?)([^\s\";&,]+)"
)
HEADERS = re.compile(r"(?i)\b(cookie|set-cookie|authorization|x-csrftoken)(\s*[:=]\s*)([^\n]+)")
BEARER = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]+")
SENSITIVE_PATHS = re.compile(
    r"(/(?:api/)?(?:account|members|membership|payments|join|dev)\b[^\s?\"']*)\?[^\s\"']*"
)
MEMBER_HANDLE = re.compile(r"(/(?:api/)?members/u/)[^/\s?\"']+")
TOKEN_PATH = re.compile(r"(/(?:api/)?(?:payments/sandbox|newsletter/unsubscribe)/)[^/\s?\"']+")


def scrub_text(text, extra_values=()):
    if not text:
        return text
    text = str(text)
    for value in extra_values:
        if value and len(value) >= 3:
            text = text.replace(value, REDACTED)
    text = HEADERS.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}", text)
    text = BEARER.sub(lambda m: f"{m.group(1)} {REDACTED}", text)
    text = SECRET_PAIRS.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}", text)
    text = SENSITIVE_PATHS.sub(lambda m: f"{m.group(1)}?{REDACTED}", text)
    text = MEMBER_HANDLE.sub(lambda m: f"{m.group(1)}{REDACTED}", text)
    text = TOKEN_PATH.sub(lambda m: f"{m.group(1)}{REDACTED}", text)
    text = EMAIL.sub(REDACTED, text)
    text = REFERENCE_CODE.sub(REDACTED, text)
    text = IPV6.sub(REDACTED, text)
    return IPV4.sub(REDACTED, text)


def _request_identities(request):
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return ()
    return (getattr(user, "display_name", ""), getattr(user, "email", ""))


class ScrubFilter(logging.Filter):
    """Rewrites each record in place; never drops one."""

    def filter(self, record):
        request = getattr(record, "request", None)
        identities = _request_identities(request) if request is not None else ()
        try:
            message = record.getMessage()
        except (TypeError, ValueError):
            message = str(record.msg)
        record.msg = scrub_text(message, identities)
        record.args = ()
        if record.exc_info and not record.exc_text:
            record.exc_text = logging.Formatter().formatException(record.exc_info)
        if record.exc_text:
            record.exc_text = scrub_text(record.exc_text, identities)
        record.exc_info = None
        # The request object, its body and headers never reach a log line.
        if request is not None:
            record.request = None
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record):
        entry = {
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        status = getattr(record, "status_code", None)
        if status is not None:
            entry["status"] = status
        if record.exc_text:
            entry["exception"] = record.exc_text
        return json.dumps(entry, ensure_ascii=False)


def scrub_event(event, hint=None):
    """Sentry before_send: drop request data and identities, scrub every text field."""
    request = event.get("request") or {}
    for key in ("data", "cookies", "headers", "query_string", "env"):
        request.pop(key, None)
    if "url" in request:
        request["url"] = scrub_text(request["url"])
    event.pop("user", None)
    event.pop("server_name", None)
    if event.get("message"):
        event["message"] = scrub_text(event["message"])
    log_entry = event.get("logentry") or {}
    if log_entry.get("message"):
        log_entry["message"] = scrub_text(log_entry["message"])
        log_entry["params"] = []
    for exception in (event.get("exception") or {}).get("values", []):
        exception["value"] = scrub_text(exception.get("value"))
        for frame in (exception.get("stacktrace") or {}).get("frames", []):
            frame.pop("vars", None)
    for crumb in (event.get("breadcrumbs") or {}).get("values", []):
        crumb["message"] = scrub_text(crumb.get("message"))
        crumb.pop("data", None)
    return event


def init_sentry(dsn, environment):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        integrations=[DjangoIntegration()],
        send_default_pii=False,
        max_request_body_size="never",
        include_local_variables=False,
        # No performance tracing: it would record every URL a member visits.
        traces_sample_rate=None,
        before_send=scrub_event,
        before_breadcrumb=lambda crumb, hint: {
            **crumb,
            "message": scrub_text(crumb.get("message")),
            "data": None,
        },
    )
