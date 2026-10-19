"""Development-only email list: subscribers in every state and one sent newsletter."""

from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from .models import Newsletter, Subscriber, Suppression, email_hash


def seed_newsletter():
    if not settings.DEBUG:
        raise ImproperlyConfigured("Email list demo data is for development only.")
    now = timezone.now()
    states = {
        "list.pending@example.org": {"status": Subscriber.Status.PENDING},
        "list.confirmed@example.org": {
            "status": Subscriber.Status.CONFIRMED,
            "confirmed_at": now - timedelta(days=20),
        },
        "list.left@example.org": {
            "status": Subscriber.Status.UNSUBSCRIBED,
            "confirmed_at": now - timedelta(days=40),
            "unsubscribed_at": now - timedelta(days=5),
        },
    }
    for email, values in states.items():
        Subscriber.objects.get_or_create(email=email, defaults=values)
    Suppression.objects.get_or_create(
        email_hash=email_hash("list.gone@example.org"),
        defaults={"unsubscribed_on": timezone.localdate() - timedelta(days=60)},
    )
    if not Newsletter.objects.filter(subject="A few dates for your calendar").exists():
        Newsletter.objects.create(
            subject="A few dates for your calendar",
            preheader="What is coming up this month",
            body="<p>Demo newsletter for development.</p><ul><li>Thursday classes</li></ul>",
            status=Newsletter.Status.SENT,
            sent_at=now - timedelta(days=14),
            send_started_at=now - timedelta(days=14),
            sent_count=1,
        )
