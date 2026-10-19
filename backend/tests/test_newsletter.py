"""The email list: double opt-in, no enumeration, one-click leaving, no tracking."""

from datetime import timedelta

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.core.models import AuditLog
from apps.newsletter import services
from apps.newsletter.models import Newsletter, Subscriber, Suppression, email_hash
from apps.newsletter.tasks import purge_subscribers, send_scheduled_newsletters

pytestmark = pytest.mark.django_db
SUBSCRIBE = "/api/newsletter/subscribe/"


def subscribe(client, email="reader@private.example", **extra):
    return client.post(SUBSCRIBE, {"email": email, **extra}, format="json")


def confirmed(email):
    return Subscriber.objects.create(
        email=email, status=Subscriber.Status.CONFIRMED, confirmed_at=timezone.now()
    )


@pytest.fixture
def newsletter():
    return Newsletter.objects.create(
        subject="A few dates for your calendar",
        preheader="What is coming up",
        body='<p>Hello.</p><script>alert(1)</script><p><a href="https://example.org">More</a></p>',
    )


# Double opt-in and no enumeration


def test_subscribing_needs_confirmation(csrf_client):
    response = subscribe(csrf_client)
    assert response.status_code == 200
    subscriber = Subscriber.objects.get()
    assert subscriber.status == "pending"
    assert [m.subject for m in mail.outbox] == ["Please confirm your email"]
    body = mail.outbox[0].body
    assert f"/subscribe/confirm#token={subscriber.token}" in body
    assert services.recipients() and not list(services.recipients())

    assert (
        csrf_client.post(
            "/api/newsletter/confirm/", {"token": subscriber.token}, format="json"
        ).status_code
        == 200
    )
    subscriber.refresh_from_db()
    assert subscriber.status == "confirmed" and subscriber.confirmed_at


@pytest.mark.parametrize("state", ["new", "pending", "confirmed", "unsubscribed"])
def test_the_answer_is_the_same_whatever_the_address_state(csrf_client, state):
    email = "someone@private.example"
    if state != "new":
        Subscriber.objects.create(email=email, status=state)
    response = subscribe(csrf_client, email)
    assert (response.status_code, response.json()) == (
        200,
        {"detail": "Check your inbox for a link to confirm."},
    )


def test_confirmed_addresses_get_no_more_mail_from_signing_up(csrf_client):
    confirmed("reader@private.example")
    subscribe(csrf_client)
    assert mail.outbox == []


def test_honeypot_sends_nothing(csrf_client):
    response = subscribe(csrf_client, website="http://bot")
    assert response.status_code == 200
    assert not Subscriber.objects.exists() and mail.outbox == []


def test_subscribing_is_rate_limited_per_address(csrf_client, settings):
    settings.NEWSLETTER_RATE_LIMIT_EMAIL = "2/h"
    for _ in range(2):
        assert subscribe(csrf_client).status_code == 200
    assert subscribe(csrf_client).status_code == 429


def test_bad_tokens_are_refused(csrf_client):
    for path in ("/api/newsletter/confirm/", "/api/newsletter/unsubscribe/"):
        assert csrf_client.post(path, {"token": "nope"}, format="json").status_code == 400


# Leaving


def test_unsubscribe_page_works_in_one_click_without_login(csrf_client):
    subscriber = confirmed("reader@private.example")
    response = csrf_client.post(
        "/api/newsletter/unsubscribe/", {"token": subscriber.token}, format="json"
    )
    assert response.status_code == 200
    subscriber.refresh_from_db()
    assert subscriber.status == "unsubscribed" and subscriber.unsubscribed_at


def test_rfc8058_one_click_post_needs_no_cookie_or_csrf(client):
    subscriber = confirmed("reader@private.example")
    url = f"/api/newsletter/unsubscribe/{subscriber.token}/"
    # A link scanner or a person opening the link changes nothing.
    opened = client.get(url)
    assert opened.status_code == 302
    assert opened["Location"].endswith(f"/unsubscribe#token={subscriber.token}")
    subscriber.refresh_from_db()
    assert subscriber.status == "confirmed"
    response = client.post(url, {"List-Unsubscribe": "One-Click"})
    assert response.status_code == 200
    subscriber.refresh_from_db()
    assert subscriber.status == "unsubscribed"


def test_unsubscribed_addresses_become_suppression_records_after_30_days():
    subscriber = confirmed("leaver@private.example")
    services.unsubscribe(subscriber.token)
    assert purge_subscribers() == {"suppressed": 0, "unconfirmed_deleted": 0}
    Subscriber.objects.filter(pk=subscriber.pk).update(
        unsubscribed_at=timezone.now() - timedelta(days=31)
    )
    assert purge_subscribers()["suppressed"] == 1
    assert not Subscriber.objects.exists()
    record = Suppression.objects.get()
    assert record.email_hash == email_hash("Leaver@Private.example ")
    assert "leaver" not in record.email_hash


def test_unconfirmed_signups_are_deleted_after_a_week():
    pending = Subscriber.objects.create(email="never@private.example")
    Subscriber.objects.filter(pk=pending.pk).update(created_at=timezone.now() - timedelta(days=8))
    assert purge_subscribers()["unconfirmed_deleted"] == 1


def test_resubscribing_after_suppression_is_a_fresh_opt_in(csrf_client):
    Suppression.objects.create(
        email_hash=email_hash("back@private.example"), unsubscribed_on=timezone.localdate()
    )
    subscribe(csrf_client, "back@private.example")
    subscriber = Subscriber.objects.get()
    assert not list(services.recipients())
    services.confirm(subscriber.token)
    assert not Suppression.objects.exists()
    assert [s.email for s in services.recipients()] == ["back@private.example"]


# Sending


def test_body_is_sanitised(newsletter):
    assert "<script>" not in newsletter.body and "alert" not in newsletter.body


def test_sends_only_to_confirmed_unsuppressed_subscribers(newsletter, admin_user, settings):
    settings.NEWSLETTER_BATCH_SIZE = 2
    for n in range(3):
        confirmed(f"reader{n}@private.example")
    Subscriber.objects.create(email="pending@private.example")
    Subscriber.objects.create(email="left@private.example", status="unsubscribed")
    suppressed = confirmed("suppressed@private.example")
    Suppression.objects.create(
        email_hash=email_hash(suppressed.email), unsubscribed_on=timezone.localdate()
    )

    services.queue_send(newsletter, admin_user)
    newsletter.refresh_from_db()
    assert newsletter.status == "sent" and newsletter.sent_count == 3
    assert sorted(m.to[0] for m in mail.outbox) == [f"reader{n}@private.example" for n in range(3)]
    assert AuditLog.objects.filter(category="newsletter", action="send").exists()
    # Sending again does nothing.
    with pytest.raises(services.NewsletterError):
        services.queue_send(newsletter, admin_user)
    assert services.deliver(newsletter.pk) == 0


def test_every_message_has_one_click_unsubscribe_headers_and_a_footer_link(newsletter, admin_user):
    subscriber = confirmed("reader@private.example")
    services.queue_send(newsletter, admin_user)
    message = mail.outbox[0]
    assert message.subject == "A few dates for your calendar"
    assert message.extra_headers["List-Unsubscribe"] == (
        f"<https://site.example/api/newsletter/unsubscribe/{subscriber.token}/>"
    )
    assert message.extra_headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    footer = f"https://site.example/unsubscribe#token={subscriber.token}"
    assert footer in message.body
    html = message.alternatives[0][0]
    assert footer in html and "What is coming up" in html


def test_tracking_is_off_at_the_provider(newsletter, admin_user, settings):
    settings.EMAIL_BACKEND = "anymail.backends.test.EmailBackend"
    confirmed("reader@private.example")
    services.queue_send(newsletter, admin_user)
    params = mail.outbox[0].anymail_test_params
    assert params["track_opens"] is False and params["track_clicks"] is False
    assert settings.ANYMAIL["SEND_DEFAULTS"] == {"track_clicks": False, "track_opens": False}


def test_send_test_goes_only_to_the_staff_member(admin_client, admin_user, newsletter):
    confirmed("reader@private.example")
    admin_client.post(reverse("admin:newsletter_send_test", args=[newsletter.pk]))
    assert [m.to for m in mail.outbox] == [[admin_user.email]]
    newsletter.refresh_from_db()
    assert newsletter.status == "draft"


def test_admin_send_needs_the_confirm_tick(admin_client, newsletter):
    confirmed("reader@private.example")
    url = reverse("admin:newsletter_send", args=[newsletter.pk])
    admin_client.post(url)
    assert mail.outbox == []
    admin_client.post(url, {"confirm": "on"})
    newsletter.refresh_from_db()
    assert newsletter.status == "sent" and len(mail.outbox) == 1


def test_scheduled_newsletters_go_out_when_due(newsletter):
    confirmed("reader@private.example")
    Newsletter.objects.filter(pk=newsletter.pk).update(
        status="scheduled", scheduled_at=timezone.now() + timedelta(hours=1)
    )
    assert send_scheduled_newsletters() == []
    Newsletter.objects.filter(pk=newsletter.pk).update(
        scheduled_at=timezone.now() - timedelta(minutes=1)
    )
    assert send_scheduled_newsletters() == [1]


def test_change_form_shows_the_inbox_preview(admin_client, newsletter):
    page = admin_client.get(
        reverse("admin:newsletter_newsletter_change", args=[newsletter.pk])
    ).content.decode()
    assert "data-inbox-preview" in page and "inbox-preview.js" in page
    assert "A few dates for your calendar" in page


def test_subscribe_endpoints_never_list_people(api_client):
    from tests.test_privacy import api_routes

    confirmed("reader@private.example")
    for route, _ in api_routes():
        if route.startswith("api/newsletter") and "<" not in route:
            assert "reader@private.example" not in api_client.get("/" + route).content.decode()
