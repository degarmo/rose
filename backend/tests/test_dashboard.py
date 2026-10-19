"""The admin home page dashboard: totals only, shown by permission."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.contact.models import ContactMessage
from apps.core.dashboard import build_dashboard
from apps.core.models import AuditLog
from apps.events.services import submit_rsvp
from apps.memberships.models import Payment
from tests.conftest import staff_login

pytestmark = pytest.mark.django_db


def stats(dashboard, title):
    section = next(s for s in dashboard["sections"] if s.title == title)
    return {stat.label: stat.value for stat in section.stats}


@pytest.fixture
def world(make_user, make_membership, make_event):
    active = make_membership(
        user=make_user(display_name="secret_member", email="secret@private.example")
    )
    make_membership(status="grace")
    make_membership(status="pending_payment")
    make_membership(status="pending_payment", paid_awaiting_id_check=True)
    Payment.objects.create(membership=active, amount_cents=2500, method="cash")
    paid = Payment.objects.create(
        membership=active, amount_cents=4000, method="online", provider_payment_ref="p1"
    )
    Payment.objects.create(
        membership=active, amount_cents=1000, method="online", status="refunded", refund_of=paid
    )
    Payment.objects.create(membership=active, amount_cents=0, method="comp")
    event = make_event(capacity=10, starts_at=timezone.now() + timedelta(days=3))
    submit_rsvp(make_user(), event, 2)
    ContactMessage.objects.create(
        name="A", email="a@example.org", topic="concern", message="x" * 20
    )
    ContactMessage.objects.create(
        name="B", email="b@example.org", topic="general", message="x" * 20
    )
    return {"event": event}


def test_numbers_are_right(admin_user, world):
    dashboard = build_dashboard(admin_user)
    members = stats(dashboard, "Membership")
    assert members["Current members"] == "2"
    assert members["In grace"] == "1"
    assert members["Waiting to pay at the door"] == "1"
    assert stats(dashboard, "Income")["This month"] == "$55.00"  # 25 + 40 - 10, comps excluded
    events = stats(dashboard, "Events")
    assert events["Events in the next 30 days"] == "1" and events["People going"] == "2"
    assert stats(dashboard, "Messages") == {"Waiting for a reply": "2", "Of which concerns": "1"}
    events_section = next(s for s in dashboard["sections"] if s.title == "Events")
    assert events_section.rows[0]["going"] == 2 and events_section.rows[0]["capacity"] == 10


def test_attention_lists_only_what_needs_action(admin_user, world):
    labels = {item.label: item.count for item in build_dashboard(admin_user)["attention"]}
    assert labels["paid online, waiting for an ID check at the door"] == 1
    assert labels["unhandled concerns from the contact form"] == 1
    assert "open feed reports" not in labels  # zero is left out


def test_page_shows_totals_and_never_names(admin_client, world):
    page = admin_client.get(reverse("admin:index")).content.decode()
    assert "Needs attention" in page and "Current members" in page and "$55.00" in page
    assert '<meter min="0" max="10" value="2"' in page
    for private in ("secret_member", "secret@private.example", "a@example.org"):
        assert private not in page


def test_sections_follow_permissions(client, desk_staff, world):
    staff_login(client, desk_staff)
    dashboard = build_dashboard(desk_staff)
    titles = [section.title for section in dashboard["sections"]]
    assert titles == ["Membership", "Income", "Images"]
    page = client.get(reverse("admin:index"))
    assert page.status_code == 200
    assert "Waiting for a reply" not in page.content.decode()


def test_system_section_is_for_superusers(admin_user, desk_staff, settings):
    settings.BACKUP_ENABLED = True
    assert "System" not in [s.title for s in build_dashboard(desk_staff)["sections"]]
    system = stats(build_dashboard(admin_user), "System")
    assert system["Last backup"] == "None yet"
    AuditLog.objects.create(
        category="operations",
        action="backup_created",
        actor=None,
        actor_label="system",
        target_label="Nightly database backup",
        target_type="backup",
    )
    # The entry is from now; look at the dashboard two days later.
    later = build_dashboard(admin_user, now=timezone.now() + timedelta(days=2))
    assert any(item.label == "nightly backup is overdue" for item in later["attention"])


def test_feed_switched_off_is_shown(admin_user, settings):
    settings.FEED_ENABLED = False
    assert stats(build_dashboard(admin_user), "Member feed")["Feed"] == "Switched off"


def test_dashboard_needs_the_two_step_login(client, admin_user):
    client.force_login(admin_user)
    assert client.get(reverse("admin:index")).status_code == 302
