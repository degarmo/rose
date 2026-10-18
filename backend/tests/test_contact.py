import pytest
from django.contrib.admin.sites import site as admin_site
from django.core import mail
from rest_framework.test import APIClient

from apps.contact.models import ContactMessage
from apps.contact.notifications import PRIORITY_SUBJECT, SUBJECT
from apps.pages.models import SiteSettings

pytestmark = pytest.mark.django_db

VALID = {
    "name": "Sam",
    "email": "sam@example.org",
    "phone": "",
    "topic": "general",
    "message": "I would like to know more about orientation.",
}


def post(client, **overrides):
    return client.post("/api/contact/", {**VALID, **overrides}, format="json")


def test_model_flags_concerns_as_priority():
    concern = ContactMessage.objects.create(
        name="A", email="a@example.org", topic="concern", message="Something happened."
    )
    general = ContactMessage.objects.create(
        name="B", email="b@example.org", topic="general", message="Hello there."
    )
    assert concern.is_priority is True
    assert general.is_priority is False
    assert str(concern) == f"Report a concern message #{concern.pk}"
    assert list(ContactMessage.objects.all()) == [concern, general]


def test_valid_submission_is_stored_and_notifies(csrf_client):
    response = post(csrf_client)
    assert response.status_code == 201
    message = ContactMessage.objects.get()
    assert message.name == "Sam"
    assert message.handled is False

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.subject == SUBJECT
    assert email.from_email == "Rose <no-reply@localhost>"
    assert email.to == ["staff-inbox@example.org"]
    assert f"/contact/contactmessage/{message.pk}/change/" in email.body


def test_notification_contains_no_submission_content(csrf_client):
    post(csrf_client, name="Unique Name", email="unique@example.org", phone="312 555 0123")
    email = mail.outbox[0]
    for private in ("Unique Name", "unique@example.org", "312 555 0123", VALID["message"]):
        assert private not in email.body
        assert private not in email.subject


def test_concern_uses_priority_subject(csrf_client):
    post(csrf_client, topic="concern")
    assert mail.outbox[0].subject == PRIORITY_SUBJECT
    assert ContactMessage.objects.get().is_priority is True


def test_subjects_are_neutral():
    for subject in (SUBJECT, PRIORITY_SUBJECT):
        assert "club" not in subject.lower()
        assert "rose" not in subject.lower()


def test_falls_back_to_public_contact_email(csrf_client, settings):
    settings.CONTACT_NOTIFY_EMAIL = ""
    site = SiteSettings.load()
    site.contact_email = "public@example.org"
    site.save()
    post(csrf_client)
    assert mail.outbox[0].to == ["public@example.org"]


def test_no_recipient_means_no_email_but_message_saved(csrf_client, settings):
    settings.CONTACT_NOTIFY_EMAIL = ""
    assert post(csrf_client).status_code == 201
    assert ContactMessage.objects.count() == 1
    assert mail.outbox == []


def test_email_failure_does_not_lose_message(csrf_client, monkeypatch):
    def boom(*args, **kwargs):
        raise ConnectionError("smtp down")

    monkeypatch.setattr("apps.contact.views.notify_new_message", boom)
    assert post(csrf_client).status_code == 201
    assert ContactMessage.objects.count() == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", ""),
        ("name", "A"),
        ("email", "not-an-email"),
        ("topic", "something-else"),
        ("message", "short"),
        ("phone", "call me maybe"),
    ],
)
def test_validation_errors(csrf_client, field, value):
    response = post(csrf_client, **{field: value})
    assert response.status_code == 400
    assert field in response.json()
    assert ContactMessage.objects.count() == 0


def test_optional_phone_is_accepted(csrf_client):
    assert post(csrf_client, phone="+1 (312) 555-0100").status_code == 201
    assert ContactMessage.objects.get().phone == "+1 (312) 555-0100"


def test_honeypot_pretends_success_but_stores_nothing(csrf_client):
    response = post(csrf_client, website="http://spam.example")
    assert response.status_code == 201
    assert ContactMessage.objects.count() == 0
    assert mail.outbox == []


def test_csrf_token_is_required():
    client = APIClient(enforce_csrf_checks=True)
    response = post(client)
    assert response.status_code == 403
    assert ContactMessage.objects.count() == 0


def test_rate_limit_blocks_after_threshold(csrf_client, settings):
    settings.CONTACT_RATE_LIMIT = "3/h"
    statuses = [post(csrf_client).status_code for _ in range(4)]
    assert statuses == [201, 201, 201, 429]
    assert ContactMessage.objects.count() == 3


def test_rate_limit_is_per_client(settings):
    settings.CONTACT_RATE_LIMIT = "1/h"
    first = APIClient(REMOTE_ADDR="10.0.0.1")
    second = APIClient(REMOTE_ADDR="10.0.0.2")
    assert post(first).status_code == 201
    assert post(first).status_code == 429
    assert post(second).status_code == 201


def test_rate_limit_uses_trusted_proxy_hop(settings):
    settings.CONTACT_RATE_LIMIT = "1/h"
    settings.TRUSTED_PROXY_COUNT = 1
    client = APIClient(REMOTE_ADDR="10.9.9.9")
    first = client.post("/api/contact/", VALID, format="json", HTTP_X_FORWARDED_FOR="203.0.113.5")
    assert first.status_code == 201
    response = client.post(
        "/api/contact/", VALID, format="json", HTTP_X_FORWARDED_FOR="forged, 203.0.113.5"
    )
    assert response.status_code == 429


def test_get_is_not_allowed(api_client):
    assert api_client.get("/api/contact/").status_code == 405


def test_no_ip_or_agent_is_stored():
    field_names = {f.name for f in ContactMessage._meta.get_fields()}
    assert not field_names & {"ip", "ip_address", "user_agent", "remote_addr"}


def test_admin_flags_priority_and_filters(admin_client):
    ContactMessage.objects.create(
        name="A", email="a@example.org", topic="concern", message="x" * 20
    )
    ContactMessage.objects.create(name="B", email="b@example.org", topic="events", message="x" * 20)
    model_admin = admin_site._registry[ContactMessage]
    assert "priority_flag" in model_admin.list_display
    assert {"topic", "handled", "is_priority"} <= set(model_admin.list_filter)

    response = admin_client.get("/admin/contact/contactmessage/?topic__exact=concern")
    assert response.status_code == 200
    assert response.context["cl"].result_count == 1

    response = admin_client.get("/admin/contact/contactmessage/?handled__exact=0")
    assert response.context["cl"].result_count == 2


def test_admin_actions_mark_handled(admin_client):
    message = ContactMessage.objects.create(
        name="A", email="a@example.org", topic="general", message="x" * 20
    )
    admin_client.post(
        "/admin/contact/contactmessage/",
        {"action": "mark_handled", "_selected_action": [message.pk]},
    )
    message.refresh_from_db()
    assert message.handled is True
    admin_client.post(
        "/admin/contact/contactmessage/",
        {"action": "mark_unhandled", "_selected_action": [message.pk]},
    )
    message.refresh_from_db()
    assert message.handled is False
