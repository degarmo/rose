"""Neutral transactional email.

Subjects and sender names must never identify the organisation or its
purpose. Every outgoing message goes through `send_neutral_mail`, which
builds the From header from EMAIL_SENDER_NAME and prefixes nothing else.
"""

from django.conf import settings
from django.core.mail import EmailMessage


def neutral_sender():
    return f"{settings.EMAIL_SENDER_NAME} <{settings.EMAIL_SENDER_ADDRESS}>"


def send_neutral_mail(subject, body, to, reply_to=None):
    message = EmailMessage(
        subject=subject,
        body=body,
        from_email=neutral_sender(),
        to=list(to),
        reply_to=list(reply_to) if reply_to else None,
    )
    return message.send(fail_silently=False)
