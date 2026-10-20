"""iCalendar files. Discreet by default: no title, no location."""

import uuid
from datetime import UTC

from django.conf import settings
from django.utils import timezone

from apps.pages.models import SiteSettings

UID_NAMESPACE = uuid.UUID("6f2b3d0a-4f6e-4bb0-9a43-1f0c2b7d5e11")


def default_title():
    return f"{settings.EMAIL_SENDER_NAME} - Evening"


def _escape(value):
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _stamp(moment):
    return moment.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _fold(line):
    """Fold lines longer than 75 octets, as RFC 5545 requires."""
    encoded = line.encode()
    if len(encoded) <= 75:
        return line
    parts, current = [], b""
    for char in line:
        piece = char.encode()
        if len(current) + len(piece) > (75 if not parts else 74):
            parts.append(current.decode())
            current = b""
        current += piece
    parts.append(current.decode())
    return "\r\n ".join(parts)


def build_ics(event, include_details=False):
    title = event.title if include_details else default_title()
    location = ""
    if include_details:
        address = SiteSettings.load().address_text.replace("\n", ", ")
        location = ", ".join(part for part in (event.location_label, address) if part)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{settings.EMAIL_SENDER_NAME}//Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uuid.uuid5(UID_NAMESPACE, str(event.pk))}",
        f"DTSTAMP:{_stamp(timezone.now())}",
        f"DTSTART:{_stamp(event.starts_at)}",
        # No end time given: calendars show the start only, rather than an invented end.
        *([f"DTEND:{_stamp(event.ends_at)}"] if event.ends_at else []),
        f"SUMMARY:{_escape(title)}",
        f"LOCATION:{_escape(location)}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
