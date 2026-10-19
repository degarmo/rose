"""The staff admin's left sidebar and its Settings menu."""

import re

import pytest
from django.urls import reverse

from apps.contact.models import ContactMessage
from tests.conftest import staff_login

pytestmark = pytest.mark.django_db


def sidebar(html):
    match = re.search(r'<nav class="ig-sidebar".*?</nav>', html, re.S)
    assert match, "sidebar missing"
    return match.group(0)


def labels(nav_html):
    return re.findall(r'<span class="ig-label">([^<]+)</span>', nav_html)


def test_superuser_sees_every_item_and_settings_last(admin_client):
    html = admin_client.get(reverse("admin:index")).content.decode()
    nav = sidebar(html)
    assert labels(nav) == [
        "Home",
        "Door desk",
        "Messages",
        "Notifications",
        "Create",
        "Events",
        "Moderation",
        "Images",
        "Dashboard",
        "All sections",
        "Settings",
    ]
    settings_menu = nav[nav.index('class="ig-settings"') :]
    assert "#settings" in settings_menu  # the gear icon
    for entry in (
        "Site settings",
        "Change password",
        "Audit log",
        "View site",
        "Appearance",
        "Log out",
    ):
        assert entry in settings_menu
    assert 'action="/admin/logout/"' in settings_menu and "csrfmiddlewaretoken" in settings_menu


def test_door_volunteer_sees_only_their_pages(client, desk_staff):
    staff_login(client, desk_staff)
    nav = sidebar(client.get(reverse("admin:memberships_door_desk")).content.decode())
    assert labels(nav) == [
        "Home",
        "Door desk",
        "Notifications",
        "Images",
        "Dashboard",
        "All sections",
        "Settings",
    ]
    assert "Audit log" not in nav and "Site settings" not in nav
    active = re.findall(
        r'class="ig-item is-active"[^>]*aria-current="page">.*?<span class="ig-label">([^<]+)',
        nav,
        re.S,
    )
    assert active == ["Door desk"]


def test_badges_count_what_is_waiting(admin_client):
    ContactMessage.objects.create(
        name="A", email="a@example.org", topic="general", message="x" * 20
    )
    ContactMessage.objects.create(
        name="B", email="b@example.org", topic="concern", message="x" * 20
    )
    nav = sidebar(admin_client.get(reverse("admin:index")).content.decode())
    assert re.search(
        r'ig-badge-count" aria-hidden="true">2</span>\s*</span>\s*<span class="ig-label">Messages',
        nav,
    )
    assert "ig-badge-dot" in nav  # Notifications shows a dot, not a number
    assert ", 2 waiting" in nav  # read out to screen readers
    assert "a@example.org" not in nav


def test_current_page_is_marked(admin_client):
    nav = sidebar(admin_client.get(reverse("admin:events_event_changelist")).content.decode())
    active = re.findall(
        r'class="ig-item is-active"[^>]*>.*?<span class="ig-label">([^<]+)', nav, re.S
    )
    assert active == ["Events"]


def test_login_pages_have_no_sidebar(client):
    html = client.get(reverse("admin:login")).content.decode()
    assert "ig-sidebar" not in html
    assert "core/ig-admin.css" in html  # still styled


def test_no_inline_styles_or_scripts(admin_client):
    """The CSP has no 'unsafe-inline'; the new chrome must not need it."""
    html = admin_client.get(reverse("admin:index")).content.decode()
    nav = sidebar(html)
    assert " style=" not in nav
    assert "<script>" not in html and "<script >" not in html
    assert 'src="/static/core/ig-admin.js"' in html


def test_django_sidebar_is_replaced(admin_client):
    html = admin_client.get(reverse("admin:events_event_changelist")).content.decode()
    assert 'id="nav-sidebar"' not in html
