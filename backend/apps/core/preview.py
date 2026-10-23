"""Staging preview mode (docs/ops/deploy.md, "Preview mode").

PREVIEW_MODE=true lets staging run before object storage and an email provider are set
up: uploads stay on the web container's disk (gone on every redeploy) and email is written
to the log instead of sent. Only those two deploy checks relax, to warnings (rose.W006 and
rose.W007). Production refuses the flag (rose.E013), and both stand-ins whatever it says.
"""

import logging

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger("rose.preview")

STARTUP_WARNING = "PREVIEW MODE: uploads are not persistent and emails are written to the log."
BANNER = "Preview mode: uploads are temporary, emails are not sent."


def preview_active():
    return bool(settings.PREVIEW_MODE) and settings.DJANGO_ENV == "staging"


class LogEmailBackend(BaseEmailBackend):
    """EMAIL_PROVIDER=console in a staging preview: one log line per message, through the
    log scrubber, never raw to stdout. Only the subject (neutral by design) and how many
    recipients: the address and the body, with names and the links that sign people in,
    stay out of the log. `manage.py show_email_link` gives staff a fresh link instead."""

    def send_messages(self, email_messages):
        for message in email_messages:
            logger.info(
                "Preview email not sent: %r to %d recipient(s)",
                message.subject,
                len(message.recipients()),
            )
        return len(email_messages)
