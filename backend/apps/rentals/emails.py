"""Rental email. Subjects are neutral, and staff get no inquiry content by email."""

from django.conf import settings
from django.urls import reverse

from apps.contact.notifications import notification_recipient
from apps.core.email import send_neutral_mail

CONFIRMATION_SUBJECT = "We received your request"
STAFF_SUBJECT = "New request received"


def _day(date):
    return f"{date:%A, %B} {date.day}"


def send_confirmation(inquiry):
    body = (
        f"Hello {inquiry.contact_name},\n\n"
        f"Thank you for your request about {_day(inquiry.preferred_date)}. "
        "A volunteer will reply to this address, usually within a few days, to talk it "
        "through. Nothing is booked until we confirm with you.\n\n"
        "If you did not send this, you can ignore this email.\n"
    )
    send_neutral_mail(CONFIRMATION_SUBJECT, body, to=[inquiry.contact_email])


def notify_staff(inquiry):
    """A link to the admin, and nothing about who asked or what for."""
    recipient = notification_recipient()
    if not recipient:
        return 0
    path = reverse("admin:rentals_rentalinquiry_change", args=[inquiry.pk])
    body = (
        f"A new request is waiting in the admin.\n\n{settings.ADMIN_BASE_URL.rstrip('/')}{path}\n"
    )
    return send_neutral_mail(STAFF_SUBJECT, body, to=[recipient])
