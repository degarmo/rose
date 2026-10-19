"""Neutral transactional email.

Subjects and sender names must never identify the organisation or its
purpose. Every outgoing message goes through `send_neutral_mail` (or
`neutral_message` for the email list), which builds the From header from
EMAIL_SENDER_NAME and prefixes nothing else.
"""

from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.core.mail.message import make_msgid


def neutral_sender():
    return f"{settings.EMAIL_SENDER_NAME} <{settings.EMAIL_SENDER_ADDRESS}>"


def neutral_message_id():
    """Message-ID on the sender's domain, so the server hostname never appears."""
    domain = settings.EMAIL_SENDER_ADDRESS.rpartition("@")[2] or "localhost"
    return make_msgid(domain=domain)


def send_neutral_mail(subject, body, to, reply_to=None):
    message = EmailMessage(
        subject=subject,
        body=body,
        from_email=neutral_sender(),
        to=list(to),
        reply_to=list(reply_to) if reply_to else None,
        headers={"Message-ID": neutral_message_id()},
    )
    return message.send(fail_silently=False)


def neutral_message(subject, body, to, html=None, headers=None):
    """A neutral message with an optional HTML part and extra headers, not yet sent.

    Open and click tracking are switched off on the message itself as well as in
    ANYMAIL's defaults, so no provider setting can turn them back on.
    """
    message = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=neutral_sender(),
        to=list(to),
        headers={"Message-ID": neutral_message_id(), **(headers or {})},
    )
    if html:
        message.attach_alternative(html, "text/html")
    message.track_opens = False
    message.track_clicks = False
    return message


def site_link(path):
    """Absolute link to a page on the public site."""
    return f"{settings.SITE_URL}{path}"
