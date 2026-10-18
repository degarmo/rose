from django.conf import settings
from django.urls import reverse

from apps.core.email import send_neutral_mail
from apps.pages.models import SiteSettings

SUBJECT = "New message received"
PRIORITY_SUBJECT = "Priority message received"


def notification_recipient():
    return settings.CONTACT_NOTIFY_EMAIL or SiteSettings.load().contact_email


def notify_new_message(message):
    """Tell staff a message is waiting, without copying its contents into email.

    The submitter's name, address and words stay in the database and are
    read in the admin, so they never sit in a mailbox or a provider's logs.
    """
    recipient = notification_recipient()
    if not recipient:
        return 0
    path = reverse("admin:contact_contactmessage_change", args=[message.pk])
    body = (
        f"A new message is waiting in the admin.\n\n"
        f"Topic: {message.get_topic_display()}\n"
        f"Priority: {'Yes' if message.is_priority else 'No'}\n\n"
        f"{settings.ADMIN_BASE_URL.rstrip('/')}{path}\n"
    )
    subject = PRIORITY_SUBJECT if message.is_priority else SUBJECT
    return send_neutral_mail(subject, body, to=[recipient])
