"""Subscribing, confirming, leaving, and sending the newsletter.

- Double opt-in: nothing is ever sent to an address until its owner confirms.
- No enumeration: subscribing answers the same way whatever the address's state.
- One click to leave, from the footer link or the List-Unsubscribe header.
- Confirmed subscribers only, never anyone suppressed, no tracking.
"""

import html
import re
from datetime import timedelta

from django.conf import settings
from django.core.mail import get_connection
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from apps.core.email import neutral_message, send_neutral_mail, site_link
from apps.core.models import AuditLog, audit

from .models import Newsletter, Subscriber, Suppression, email_hash, new_token

CONFIRM_SUBJECT = "Please confirm your email"


class NewsletterError(Exception):
    """A send was refused; the message is shown to staff."""


def confirm_link(subscriber):
    # The token sits in the fragment, which browsers never send to the server.
    return site_link(f"/subscribe/confirm#token={subscriber.token}")


def unsubscribe_page_link(subscriber):
    return site_link(f"/unsubscribe#token={subscriber.token}")


def one_click_link(subscriber):
    """RFC 8058: mail apps POST here, without cookies, to unsubscribe in one click."""
    return site_link(f"/api/newsletter/unsubscribe/{subscriber.token}/")


def send_confirmation(subscriber):
    body = (
        "Someone, hopefully you, asked to receive occasional updates at this address.\n\n"
        f"To confirm, open this link:\n{confirm_link(subscriber)}\n\n"
        "If this was not you, ignore this email and nothing more will be sent.\n"
    )
    send_neutral_mail(CONFIRM_SUBJECT, body, to=[subscriber.email])


@transaction.atomic
def subscribe(email):
    """Start (or restart) a subscription. Returns nothing the caller may reveal."""
    email = email.strip().lower()
    subscriber = Subscriber.objects.select_for_update().filter(email=email).first()
    if subscriber is not None and subscriber.status == Subscriber.Status.CONFIRMED:
        return
    if subscriber is None:
        subscriber = Subscriber.objects.create(email=email)
    else:
        subscriber.status = Subscriber.Status.PENDING
        subscriber.token = new_token()
        subscriber.created_at = timezone.now()
        subscriber.unsubscribed_at = None
        subscriber.save()
    transaction.on_commit(lambda: send_confirmation(subscriber))


def _by_token(token):
    if not token or len(token) > 64:
        return None
    return Subscriber.objects.select_for_update().filter(token=token).first()


@transaction.atomic
def confirm(token):
    subscriber = _by_token(token)
    if subscriber is None or subscriber.status == Subscriber.Status.UNSUBSCRIBED:
        return False
    if subscriber.status == Subscriber.Status.PENDING:
        subscriber.status = Subscriber.Status.CONFIRMED
        subscriber.confirmed_at = timezone.now()
        subscriber.save(update_fields=["status", "confirmed_at"])
        # Asking again is a fresh opt-in, so an old suppression no longer applies.
        Suppression.objects.filter(email_hash=email_hash(subscriber.email)).delete()
    return True


@transaction.atomic
def unsubscribe(token):
    subscriber = _by_token(token)
    if subscriber is None:
        return False
    if subscriber.status != Subscriber.Status.UNSUBSCRIBED:
        subscriber.status = Subscriber.Status.UNSUBSCRIBED
        subscriber.unsubscribed_at = timezone.now()
        subscriber.save(update_fields=["status", "unsubscribed_at"])
    return True


def html_to_text(markup):
    """A readable plain-text version of the sanitised body."""
    text = re.sub(r'<a href="([^"]+)"[^>]*>(.*?)</a>', r"\2 (\1)", markup)
    text = re.sub(r"<li[^>]*>", "- ", text)
    text = re.sub(r"</(p|h3|h4|blockquote|li|ul|ol)>|<br\s*/?>", "\n", text)
    text = html.unescape(strip_tags(text))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def build_message(newsletter, to, unsubscribe_url=None, one_click_url=None):
    footer_link = unsubscribe_url or site_link("/unsubscribe")
    context = {
        "newsletter": newsletter,
        "unsubscribe_url": footer_link,
    }
    html_body = render_to_string("newsletter/email.html", context)
    text_body = (
        f"{html_to_text(newsletter.body)}\n\n--\n"
        "You are receiving this because you confirmed this address for occasional updates.\n"
        f"Unsubscribe in one click: {footer_link}\n"
    )
    headers = {}
    if one_click_url:
        headers = {
            "List-Unsubscribe": f"<{one_click_url}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        }
    return neutral_message(newsletter.subject, text_body, [to], html=html_body, headers=headers)


def send_test(newsletter, staff):
    """To the staff member alone. Never to anyone on the list."""
    if not staff.email:
        raise NewsletterError("Your account has no email address.")
    message = build_message(newsletter, staff.email)
    message.send(fail_silently=False)
    audit(
        AuditLog.Category.NEWSLETTER,
        "send_test",
        staff,
        f"Newsletter #{newsletter.pk}",
        "newsletter",
        target_ref=str(newsletter.pk),
    )


def recipients():
    """Confirmed subscribers who are not suppressed, oldest first."""
    suppressed = set(Suppression.objects.values_list("email_hash", flat=True))
    for subscriber in Subscriber.objects.filter(status=Subscriber.Status.CONFIRMED).order_by("pk"):
        if email_hash(subscriber.email) not in suppressed:
            yield subscriber


def queue_send(newsletter, staff):
    """Mark it for sending now and hand it to the worker."""
    from .tasks import send_newsletter

    if newsletter.status == Newsletter.Status.SENT or newsletter.send_started_at:
        raise NewsletterError("This newsletter has already been sent.")
    newsletter.status = Newsletter.Status.SCHEDULED
    newsletter.scheduled_at = timezone.now()
    newsletter.save(update_fields=["status", "scheduled_at", "updated_at"])
    audit(
        AuditLog.Category.NEWSLETTER,
        "send",
        staff,
        f"Newsletter #{newsletter.pk}",
        "newsletter",
        target_ref=str(newsletter.pk),
    )
    transaction.on_commit(lambda: send_newsletter.delay(newsletter.pk))


def deliver(newsletter_pk):
    """Send to every confirmed subscriber in batches. Runs once per newsletter."""
    with transaction.atomic():
        newsletter = Newsletter.objects.select_for_update().filter(pk=newsletter_pk).first()
        if (
            newsletter is None
            or newsletter.send_started_at
            or (newsletter.status != Newsletter.Status.SCHEDULED)
        ):
            return 0
        newsletter.send_started_at = timezone.now()
        newsletter.save(update_fields=["send_started_at"])

    sent = 0
    batch = []
    size = settings.NEWSLETTER_BATCH_SIZE

    def flush():
        nonlocal sent
        if batch:
            with get_connection() as connection:
                sent += connection.send_messages(batch) or 0
            batch.clear()

    for subscriber in recipients():
        batch.append(
            build_message(
                newsletter,
                subscriber.email,
                unsubscribe_url=unsubscribe_page_link(subscriber),
                one_click_url=one_click_link(subscriber),
            )
        )
        if len(batch) >= size:
            flush()
    flush()

    Newsletter.objects.filter(pk=newsletter.pk).update(
        status=Newsletter.Status.SENT, sent_at=timezone.now(), sent_count=sent
    )
    audit(
        AuditLog.Category.NEWSLETTER,
        "delivered",
        None,
        f"Newsletter #{newsletter.pk}",
        "newsletter",
        target_ref=str(newsletter.pk),
        reason=f"{sent} sent",
    )
    return sent


def purge(now=None):
    """Unsubscribed for 30 days: keep only a suppression hash. Never confirmed: delete."""
    now = now or timezone.now()
    suppressed = 0
    cutoff = now - timedelta(days=settings.NEWSLETTER_SUPPRESS_AFTER_DAYS)
    for subscriber in Subscriber.objects.filter(
        status=Subscriber.Status.UNSUBSCRIBED, unsubscribed_at__lt=cutoff
    ):
        with transaction.atomic():
            Suppression.objects.get_or_create(
                email_hash=email_hash(subscriber.email),
                defaults={"unsubscribed_on": timezone.localdate(subscriber.unsubscribed_at)},
            )
            subscriber.delete()
        suppressed += 1
    stale, _ = Subscriber.objects.filter(
        status=Subscriber.Status.PENDING,
        created_at__lt=now - timedelta(days=settings.NEWSLETTER_PENDING_DAYS),
    ).delete()
    return {"suppressed": suppressed, "unconfirmed_deleted": stale}
