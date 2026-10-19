"""Volunteer signups: the form, the staff list and the logged CSV export."""

import csv
import io
from datetime import timedelta

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.core.models import AuditLog
from apps.volunteers.models import VolunteerSignup
from apps.volunteers.tasks import purge_old_signups
from tests.conftest import PASSWORD, staff_login

pytestmark = pytest.mark.django_db
URL = "/api/volunteer/signup/"


def payload(**overrides):
    data = {
        "contact_name": "Sam Helper",
        "contact_email": "sam@private.example",
        "interests": ["door", "teaching"],
        "availability": ["weekends"],
        "experience_note": "Ran a door team for two years.",
        "website": "",
    }
    data.update(overrides)
    return data


def test_options_list_the_roles_and_times(api_client):
    data = api_client.get("/api/volunteer/options/").json()
    assert {c["value"] for c in data["interests"]} >= {"door", "teaching", "outreach", "admin_web"}
    assert {c["value"] for c in data["availability"]} == {
        "weeknights",
        "weekends",
        "daytime",
        "one_off",
    }


def test_signup_is_stored_and_never_echoed(csrf_client):
    response = csrf_client.post(URL, payload(), format="json")
    assert response.status_code == 201
    assert "sam@private.example" not in response.content.decode()
    signup = VolunteerSignup.objects.get()
    assert signup.status == "new" and signup.interests == ["door", "teaching"]
    assert sorted(m.subject for m in mail.outbox) == [
        "New note received",
        "Thank you for your note",
    ]
    staff = next(m for m in mail.outbox if m.subject == "New note received")
    assert "Sam" not in staff.body and "door" not in staff.body


def test_signed_in_signups_are_linked(signed_in):
    client, user = signed_in()
    client.post(
        URL, payload(contact_name=user.display_name, contact_email=user.email), format="json"
    )
    assert VolunteerSignup.objects.get().user == user


@pytest.mark.parametrize(
    "overrides",
    [{"interests": []}, {"interests": ["juggling"]}, {"availability": []}, {"contact_name": "x"}],
)
def test_incomplete_signups_are_refused(csrf_client, overrides):
    assert csrf_client.post(URL, payload(**overrides), format="json").status_code == 400


def test_honeypot_and_rate_limit(csrf_client, settings):
    assert csrf_client.post(URL, payload(website="x"), format="json").status_code == 201
    assert not VolunteerSignup.objects.exists()
    settings.VOLUNTEER_RATE_LIMIT = "1/h"
    csrf_client.post(URL, payload(), format="json")
    assert csrf_client.post(URL, payload(), format="json").status_code == 429


def test_admin_filters_by_interest_and_status(admin_client):
    VolunteerSignup.objects.create(
        contact_name="Teacher Tam", contact_email="t@x.example", interests=["teaching"]
    )
    VolunteerSignup.objects.create(
        contact_name="Door Dee", contact_email="d@x.example", interests=["door"], status="active"
    )
    url = reverse("admin:volunteers_volunteersignup_changelist")
    by_interest = admin_client.get(url, {"interest": "teaching"}).content.decode()
    assert "Teacher Tam" in by_interest and "Door Dee" not in by_interest
    by_status = admin_client.get(url, {"status__exact": "active"}).content.decode()
    assert "Door Dee" in by_status and "Teacher Tam" not in by_status


def export(client, **data):
    response = client.post(reverse("admin:volunteers_export"), data)
    rows = list(csv.reader(io.StringIO(response.content.decode())))
    return response, rows


def test_export_is_logged_and_has_no_email_by_default(admin_client, admin_user):
    VolunteerSignup.objects.create(
        contact_name="=cmd()", contact_email="hidden@x.example", interests=["door"]
    )
    response, rows = export(admin_client)
    assert "no-store" in response["Cache-Control"] and "private" in response["Cache-Control"]
    assert rows[0] == ["Name", "Interests", "Availability", "Status", "Signed up"]
    assert rows[1][0] == "'=cmd()"  # never a live spreadsheet formula
    assert "hidden@x.example" not in response.content.decode()
    entry = AuditLog.objects.get(category=AuditLog.Category.EXPORT)
    assert entry.action == "volunteer_csv" and entry.actor == admin_user
    assert "1 rows" in entry.target_label


def test_superuser_may_include_emails_and_that_is_logged_separately(admin_client):
    VolunteerSignup.objects.create(
        contact_name="A", contact_email="a@x.example", interests=["door"]
    )
    response, rows = export(admin_client, include_email="on")
    assert rows[0][-1] == "Email" and rows[1][-1] == "a@x.example"
    entry = AuditLog.objects.get(category=AuditLog.Category.EXPORT)
    assert entry.action == "volunteer_csv_with_email"
    assert entry.reason == "Included contact email"


def test_staff_who_are_not_superusers_cannot_include_emails(client, django_user_model):
    from django.contrib.auth.models import Permission

    staff = django_user_model.objects.create_user(
        email="coord@x.example", display_name="coordinator", password=PASSWORD, is_staff=True
    )
    staff.user_permissions.set(Permission.objects.filter(codename="view_volunteersignup"))
    staff_login(client, staff)
    VolunteerSignup.objects.create(
        contact_name="A", contact_email="a@x.example", interests=["door"]
    )
    page = client.get(reverse("admin:volunteers_export")).content.decode()
    assert "include_email" not in page
    response, rows = export(client, include_email="on")
    assert "a@x.example" not in response.content.decode()
    assert AuditLog.objects.get().action == "volunteer_csv"


def test_signups_that_went_nowhere_are_deleted(settings):
    settings.VOLUNTEER_RETENTION_DAYS = 365
    old_new = VolunteerSignup.objects.create(contact_name="A", contact_email="a@x.example")
    old_active = VolunteerSignup.objects.create(
        contact_name="B", contact_email="b@x.example", status="active"
    )
    VolunteerSignup.objects.filter(pk__in=[old_new.pk, old_active.pk]).update(
        updated_at=timezone.now() - timedelta(days=400)
    )
    assert purge_old_signups() == 1
    assert list(VolunteerSignup.objects.values_list("pk", flat=True)) == [old_active.pk]


def test_deleting_an_account_deletes_its_signups(signed_in):
    client, user = signed_in()
    client.post(URL, payload(), format="json")
    client.post("/api/account/delete/", {"password": PASSWORD}, format="json")
    assert not VolunteerSignup.objects.exists()
