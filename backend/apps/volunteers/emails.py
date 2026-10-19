"""Volunteer email: neutral subjects, and no signup content in staff notices."""

from django.conf import settings
from django.urls import reverse

from apps.contact.notifications import notification_recipient
from apps.core.email import send_neutral_mail

CONFIRMATION_SUBJECT = "Thank you for your note"
STAFF_SUBJECT = "New note received"


def send_confirmation(signup):
    body = (
        f"Hello {signup.contact_name},\n\n"
        "Thank you for offering your time. A volunteer coordinator will reply to this "
        "address to talk about what might suit you.\n\n"
        "If you did not send this, you can ignore this email.\n"
    )
    send_neutral_mail(CONFIRMATION_SUBJECT, body, to=[signup.contact_email])


def notify_staff(signup):
    recipient = notification_recipient()
    if not recipient:
        return 0
    path = reverse("admin:volunteers_volunteersignup_change", args=[signup.pk])
    body = (
        "A new volunteer signup is waiting in the admin.\n\n"
        f"{settings.ADMIN_BASE_URL.rstrip('/')}{path}\n"
    )
    return send_neutral_mail(STAFF_SUBJECT, body, to=[recipient])
