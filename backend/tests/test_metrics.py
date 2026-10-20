"""One set of numbers: apps.core.metrics, and the admin dashboard as the only dashboard.

Every badge, card, table cell and export row for a metric shows the same value, small
numbers are withheld inside the service, and each role sees only its part.
"""

import csv
import io
import json
import re

import pytest
from django.test import Client, RequestFactory
from django.urls import reverse
from django.utils import timezone

from apps.contact.models import ContactMessage
from apps.core import admin_nav, metrics
from apps.core.dashboard import dashboard_callback
from apps.feed.models import FeedPost, Report
from apps.memberships.models import Payment
from apps.safety import roles
from tests.conftest import staff_login

pytestmark = pytest.mark.django_db


# The rules


def test_small_numbers_are_withheld_inside_the_service():
    """A figure's own keys never collide with its row's (a revenue row's tier label)."""
    rows = metrics.revenue_for(timezone.localdate())["rows"]
    assert [row["label"] for row in rows][-2:] == ["Guest passes", "Donations"]
    assert metrics.count(0) == {"value": 0, "display": "0", "spoken": "0"}
    for small in (1, 4):
        assert metrics.count(small) == {
            "value": None,
            "fewer_than": 5,
            "display": "<5",
            "spoken": "fewer than 5",
        }
    assert metrics.count(5) == {"value": 5, "display": "5", "spoken": "5"}
    assert metrics.count(1234)["display"] == "1,234"
    assert metrics.money(10_000, 4)["cents"] is None
    assert metrics.money(10_000, 4)["display"] == "<5"
    assert metrics.money(10_000, 5) == {"cents": 10_000, "display": "$100", "spoken": "$100"}


@pytest.fixture
def make_report(make_member, make_post):
    reporter = make_member(display_name="secret_reporter", email="reporter@private.example")
    author = make_member(display_name="secret_author")

    def make(status):
        post = make_post(author, caption="Reported")
        return Report.objects.create(
            reporter=reporter, target_type="post", post=post, reason="harassment", status=status
        )

    return make


def test_each_definition(make_report, make_member, make_membership, make_user):
    for status in ("open", "in_review", "resolved", "dismissed"):
        make_report(status)
    assert metrics.open_reports()["value"] is None  # 2: open and in review
    for _ in range(4):
        make_report("open")
    assert metrics.open_reports()["value"] == 6
    author = make_member()
    for n in range(5):
        FeedPost.objects.create(author=author, caption=f"First {n}", status=FeedPost.Status.PENDING)
    FeedPost.objects.create(
        author=author,
        caption="Still processing",
        status=FeedPost.Status.PENDING,
        is_processing=True,
    )
    assert metrics.posts_awaiting_approval()["value"] == 5
    for _ in range(5):
        make_membership(status="pending_payment", paid_awaiting_id_check=True)
    make_membership(status="pending_payment")  # unpaid: not waiting for a check
    inactive = make_user(is_active=False)
    make_membership(user=inactive, status="pending_payment", paid_awaiting_id_check=True)
    assert metrics.id_checks_needed()["value"] == 5
    for n in range(5):
        ContactMessage.objects.create(
            name="A", email="a@example.org", topic="general", message="x" * 20, handled=bool(n)
        )
    assert metrics.unanswered_messages() == metrics.count(1)


# The same number everywhere


@pytest.fixture
def busy(make_report, make_member, make_membership, make_tier):
    """Enough of everything for real numbers to show, not "<5"."""
    for _ in range(7):
        make_report("open")
    make_report("in_review")
    make_report("resolved")
    author = make_member()
    for n in range(6):
        FeedPost.objects.create(author=author, caption=f"First {n}", status=FeedPost.Status.PENDING)
    for _ in range(5):
        make_membership(status="pending_payment", paid_awaiting_id_check=True)
    tier = make_tier(name="Rose")
    for _ in range(6):
        membership = make_membership(tier=tier)
        Payment.objects.create(membership=membership, amount_cents=2500, method="cash")
    for n in range(5):
        ContactMessage.objects.create(
            name="A", email=f"m{n}@example.org", topic="general", message="x" * 20
        )


def badge_after(html, item):
    match = re.search(rf"{re.escape(item)}</span>\s*<span[^>]*>\s*([^<\s]+)\s*<", html)
    return match.group(1) if match else ""


def kpi(html, label):
    match = re.search(
        rf'<p class="rose-kpi-label">{re.escape(label)}</p>\s*'
        r'<p class="rose-kpi-value">([^<]+)</p>',
        html,
    )
    return match.group(1) if match else None


def table_row(html, label):
    match = re.search(
        rf'<th scope="row">{re.escape(label)}</th><td class="rose-num">([^<]+)</td>', html
    )
    return match.group(1) if match else None


def test_every_screen_shows_the_same_numbers(admin_client, admin_user, busy):
    reports = metrics.open_reports()["display"]
    pending = metrics.posts_awaiting_approval()["display"]
    checks = metrics.id_checks_needed()["display"]
    messages = metrics.unanswered_messages()["display"]
    assert (reports, pending, checks, messages) == ("8", "6", "5", "5")

    html = admin_client.get(reverse("admin:index")).content.decode()
    # Cards
    assert kpi(html, "Open reports") == reports
    assert kpi(html, "Posts awaiting approval") == pending
    assert kpi(html, "ID checks needed") == checks
    # Badges
    assert badge_after(html, "Reports") == reports
    assert badge_after(html, "Feed posts") == pending
    assert badge_after(html, "Door desk") == checks
    assert badge_after(html, "Contact messages") == messages
    # Table cells
    assert table_row(html, "Open reports") == reports
    assert table_row(html, "Posts awaiting approval") == pending
    # The badge callbacks themselves
    request = RequestFactory().get("/admin/")
    request.user = admin_user
    assert admin_nav.reports_badge(request) == reports
    assert admin_nav.pending_posts_badge(request) == pending
    assert admin_nav.desk_badge(request) == checks

    # Members and money: the card, the table's total row and the export agree.
    active = metrics.membership_section(timezone.localdate())
    assert kpi(html, "Active members") == active["total_active"]["display"] == "6"
    assert re.search(r'<th scope="row">All tiers</th><td class="rose-num">6</td>', html), (
        "tier table total"
    )
    assert kpi(html, "Revenue this month") == "$150"
    assert re.search(r'<th scope="row">Total</th><td class="rose-num">\$150</td>', html)

    export = admin_client.post(reverse("admin:metrics_export"), {"range": "30d"})
    rows = list(csv.reader(io.StringIO(export.content.decode())))
    assert ["Feed", "", "Open reports", "8"] in rows
    assert ["Feed", "", "Posts awaiting approval", "6"] in rows
    assert ["Door desk", "", "ID checks needed", "5"] in rows
    assert ["Members", "All tiers", "Active", "6"] in rows


def test_small_numbers_show_the_same_way_everywhere(admin_client, make_report, make_membership):
    make_report("open")
    make_membership(status="pending_payment", paid_awaiting_id_check=True)
    html = admin_client.get(reverse("admin:index")).content.decode()
    assert badge_after(html, "Reports") == "&lt;5"
    assert badge_after(html, "Door desk") == "&lt;5"
    withheld = (
        '<span class="rose-metric-withheld" title="fewer than 5"><span aria-hidden="true">'
        '&lt;5</span><span class="sr-only">fewer than 5</span></span>'
    )
    card = re.search(
        r'<p class="rose-kpi-label">Open reports</p>\s*<p class="rose-kpi-value">(.*?)</p>', html
    )
    assert card.group(1) == withheld
    assert "secret_reporter" not in html and "reporter@private.example" not in html


# Who sees what


def as_role(make_user, role):
    user = make_user(display_name=f"dash_{role}")
    roles.set_role(user, role)
    return staff_login(Client(), user)


FULL = ("Active members", "New this month", "Revenue this month", "Email list", "By tier")


@pytest.mark.parametrize("role", [roles.ADMIN, roles.STAFF])
def test_admin_and_staff_see_everything(role, make_user, busy):
    html = as_role(make_user, role).get(reverse("admin:index")).content.decode()
    for text in (*FULL, "Open reports", "Posts awaiting approval", "ID checks needed"):
        assert text in html, (role, text)
    assert 'action="/admin/metrics/export/"' in html and "30 days" in html
    assert "Age verification for the member feed" in html
    change = reverse("admin:pages_sitesettings_age_verification")
    assert (f'href="{change}">Change</a>' in html) is (role == roles.ADMIN)


def test_moderators_see_only_what_is_waiting(make_user, busy):
    html = as_role(make_user, roles.MODERATOR).get(reverse("admin:index")).content.decode()
    cards = re.findall(r'<p class="rose-kpi-label">([^<]+)</p>', html)
    assert cards == ["Open reports", "Posts awaiting approval", "ID checks needed"]
    for text in (*FULL, "$150", "metrics/export", "Age verification for the member feed:"):
        assert text not in html, text


def test_a_door_volunteer_sees_only_id_checks(desk_staff, busy):
    html = staff_login(Client(), desk_staff).get(reverse("admin:index")).content.decode()
    assert re.findall(r'<p class="rose-kpi-label">([^<]+)</p>', html) == ["ID checks needed"]
    assert "/members/staff/door?needs_id=1" in html


def test_the_range_switch_changes_the_charts(admin_user):
    for key, label, points in (
        ("30d", "30 days", 5),
        ("90d", "90 days", 13),
        ("12m", "12 months", 12),
    ):
        request = RequestFactory().get("/admin/", {"range": key})
        request.user = admin_user
        context = dashboard_callback(request, {})
        assert context["range"] == key and context["range_label"] == label
        titles = [title for title, _chart in context["series_charts"]]
        assert titles == ["Revenue ($)", "Payments", "RSVPs", "Feed posts"]
        assert len(json.loads(context["series_charts"][0][1])["labels"]) == points


def test_the_export_is_for_admin_and_staff_and_logged(make_user):
    from apps.core.models import AuditLog

    moderator = as_role(make_user, roles.MODERATOR)
    assert moderator.post(reverse("admin:metrics_export"), {"range": "30d"}).status_code == 403
    staff = as_role(make_user, roles.STAFF)
    assert staff.get(reverse("admin:metrics_export")).status_code == 403
    response = staff.post(reverse("admin:metrics_export"), {"range": "12m"})
    assert response.status_code == 200 and response["Content-Type"].startswith("text/csv")
    assert "no-store" in response["Cache-Control"]
    assert AuditLog.objects.get(action="metrics_export").actor.display_name == "dash_staff"


def test_the_dashboard_needs_the_two_step_login(client, admin_user):
    client.force_login(admin_user)
    assert client.get(reverse("admin:index")).status_code == 302
