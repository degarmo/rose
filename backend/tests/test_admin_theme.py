"""The admin in Rose's look (django-unfold): sidebar by role, dashboard, and its chrome."""

import re
from datetime import timedelta

import pytest
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.test import Client, RequestFactory
from django.urls import reverse
from django.utils import timezone

from apps.contact.models import ContactMessage
from apps.events.services import submit_rsvp
from tests.conftest import PASSWORD, staff_login

pytestmark = pytest.mark.django_db

SECTIONS = ["Today", "Members", "Events", "Content", "Community", "Money", "Outreach", "Settings"]

ROLE_PERMISSIONS = {
    "editor": [
        ("events", ["view_event", "add_event", "change_event", "view_eventtag", "view_rsvp"]),
        ("journal", ["view_post", "add_post", "change_post"]),
        ("pages", ["view_pagecontent", "change_pagecontent", "view_faqitem"]),
        ("education", ["view_opportunity", "change_opportunity"]),
    ],
    "moderator": [
        ("feed", ["view_feedpost", "change_feedpost", "view_report", "view_announcement"]),
        ("safety", ["view_memberaction", "view_appeal"]),
    ],
    "treasurer": [
        ("memberships", ["view_payment", "view_membership", "view_tier"]),
        ("donations", ["view_donation"]),
    ],
}


def make_staff(django_user_model, name, grants):
    user = django_user_model.objects.create_user(
        email=f"{name}@example.org", display_name=f"staff_{name}", password=PASSWORD, is_staff=True
    )
    for app, codenames in grants:
        user.user_permissions.add(
            *Permission.objects.filter(content_type__app_label=app, codename__in=codenames)
        )
    return django_user_model.objects.get(pk=user.pk)


@pytest.fixture
def role_user(django_user_model, admin_user, desk_staff):
    def get(role):
        if role == "owner":
            return admin_user
        if role == "door":
            return desk_staff
        return make_staff(django_user_model, role, ROLE_PERMISSIONS[role])

    return get


def visible(user, path="/admin/"):
    """{section: [item titles]} as the sidebar shows them to this person."""
    request = RequestFactory().get(path)
    request.user = user
    shown = {}
    for group in admin.site.get_sidebar_list(request):
        items = [item["title"] for item in group["items"] if item["has_permission"]]
        if items:
            shown[group["title"]] = items
    return shown


def links(user, admin_only=True):
    """The sidebar's links for this person; the door desk is the staff section's, on the
    site itself, so admin_only leaves it out."""
    request = RequestFactory().get("/admin/")
    request.user = user
    found = [
        str(item["link"])
        for group in admin.site.get_sidebar_list(request)
        for item in group["items"]
        if item["has_permission"]
    ]
    return [link for link in found if link.startswith("/")] if admin_only else found


def test_the_door_desk_item_opens_the_staff_door_desk(desk_staff, settings):
    assert f"{settings.SITE_URL}/members/staff/door" in links(desk_staff, admin_only=False)


# Sidebar sections by role


def test_owner_sees_every_section(admin_user):
    shown = visible(admin_user)
    assert list(shown) == SECTIONS
    assert shown["Today"] == ["Dashboard", "Door desk", "Reports"]
    assert shown["Members"] == ["Members", "Memberships", "ID checks", "Tiers"]
    assert shown["Events"] == ["Events", "Past events", "RSVPs (counts only)", "Event tags"]
    assert shown["Content"] == [
        "Journal",
        "Announcements",
        "Education",
        "Page copy",
        "FAQ",
        "Guidelines",
        "Agreement",
    ]
    assert shown["Community"] == ["Feed posts", "Moderation log", "Appeals"]
    assert shown["Money"] == ["Payments", "Donations", "Membership summary"]
    assert shown["Outreach"] == [
        "Newsletter",
        "Subscribers",
        "Rentals",
        "Volunteers",
        "Contact messages",
    ]
    assert shown["Settings"] == ["Site settings", "Team and roles", "Image review", "Audit log"]


def test_door_volunteer_sees_only_the_door_and_memberships(desk_staff):
    assert visible(desk_staff) == {
        "Today": ["Dashboard", "Door desk"],
        "Members": ["Memberships"],
        "Money": ["Payments", "Membership summary"],
    }


def test_editor_sees_content_and_image_review(role_user):
    shown = visible(role_user("editor"))
    assert list(shown) == ["Today", "Events", "Content", "Settings"]
    assert shown["Today"] == ["Dashboard"]
    assert shown["Content"] == ["Journal", "Education", "Page copy", "FAQ"]
    assert shown["Settings"] == ["Image review"]


def test_moderator_sees_reports_and_community(role_user):
    shown = visible(role_user("moderator"))
    assert list(shown) == ["Today", "Content", "Community"]
    assert shown["Today"] == ["Dashboard", "Reports"]
    assert shown["Community"] == ["Feed posts", "Moderation log", "Appeals"]


def test_treasurer_sees_money_and_no_settings(role_user):
    shown = visible(role_user("treasurer"))
    assert shown["Money"] == ["Payments", "Donations", "Membership summary"]
    assert "Settings" not in shown and "Content" not in shown


def test_audit_log_is_for_superusers_only(role_user):
    for role in ("door", "editor", "moderator", "treasurer"):
        assert "Audit log" not in str(visible(role_user(role)))


@pytest.mark.parametrize("role", ["owner", "door", "editor", "moderator", "treasurer"])
def test_every_page_in_a_role_sidebar_opens(role, role_user):
    user = role_user(role)
    client = staff_login(Client(), user)
    for link in links(user):
        response = client.get(link, follow=True)
        assert response.status_code == 200, (role, link, response.status_code)
        assert b"core/rose-admin.css" in response.content


@pytest.mark.parametrize("role", ["door", "editor", "moderator", "treasurer"])
def test_pages_outside_a_role_stay_closed(role, role_user):
    user = role_user(role)
    client = staff_login(Client(), user)
    allowed = set(links(user))
    owner_links = links(role_user("owner"))
    for link in owner_links:
        if link in allowed:
            continue
        response = client.get(link)
        assert response.status_code in (302, 403, 404), (role, link, response.status_code)


def test_current_page_is_marked_active(admin_user):
    request = RequestFactory().get(reverse("admin:events_event_changelist"))
    request.user = admin_user
    active = [
        item["title"]
        for group in admin.site.get_sidebar_list(request)
        for item in group["items"]
        if item["active"]
    ]
    assert active == ["Events"]


def test_badges_count_what_is_waiting(admin_client, make_membership):
    ContactMessage.objects.create(
        name="A", email="a@example.org", topic="general", message="x" * 20
    )
    make_membership(status="pending_payment", paid_awaiting_id_check=True)
    html = admin_client.get(reverse("admin:index")).content.decode()
    assert "a@example.org" not in html
    # One of each: a small number, shown as "<5" like everywhere else (apps.core.metrics).
    assert re.search(r"Contact messages</span>\s*<span[^>]*>\s*&lt;5\s*<", html)
    assert re.search(r"Door desk</span>\s*<span[^>]*>\s*&lt;5\s*<", html)


def test_badge_callbacks_return_counts(admin_user, desk_staff, make_membership):
    from apps.core import admin_nav

    ContactMessage.objects.create(
        name="A", email="a@example.org", topic="general", message="x" * 20
    )
    make_membership(status="pending_payment", paid_awaiting_id_check=True)
    request = RequestFactory().get("/admin/")
    request.user = admin_user
    assert admin_nav.messages_badge(request) == "<5"
    assert admin_nav.desk_badge(request) == "<5"
    assert admin_nav.reports_badge(request) == ""  # none: no badge at all
    for _ in range(5):
        make_membership(status="pending_payment", paid_awaiting_id_check=True)
    assert admin_nav.desk_badge(request) == "6"


# Every registered admin page, in the new look


def test_every_registered_model_renders_for_the_owner(admin_client, small_world):
    for model in admin.site._registry:
        meta = model._meta
        changelist = reverse(f"admin:{meta.app_label}_{meta.model_name}_changelist")
        response = admin_client.get(changelist, follow=True)
        assert response.status_code == 200, (changelist, response.status_code)
        assert b"core/rose-admin.css" in response.content
        add = reverse(f"admin:{meta.app_label}_{meta.model_name}_add")
        response = admin_client.get(add)
        assert response.status_code in (200, 302, 403), (add, response.status_code)
        first = model._default_manager.first()
        if first is not None:
            change = reverse(f"admin:{meta.app_label}_{meta.model_name}_change", args=[first.pk])
            response = admin_client.get(change)
            assert response.status_code == 200, (change, response.status_code)


def test_custom_views_render_for_the_owner(admin_client):
    for name in (
        "admin:index",
        "admin:memberships_summary",
        "admin:feed_moderation",
        "admin:image_review",
        "admin:staff_guide",
        "admin:events_rsvp_counts",
    ):
        response = admin_client.get(reverse(name))
        assert response.status_code == 200, name
        html = response.content.decode()
        assert 'class="rose-' in html, name


# Chrome: own fonts and scripts, nothing from another site, CSP unchanged


EXTERNAL = re.compile(r"""(?:src|href|action)=["'](?:https?:)?//""", re.I)


@pytest.mark.parametrize(
    "name",
    ["admin:index", "admin:memberships_summary", "admin:events_event_add", "admin:login"],
)
def test_admin_pages_load_nothing_from_other_sites(name, admin_client, client, settings):
    response = (client if name == "admin:login" else admin_client).get(reverse(name))
    # Links back to the member app on the site's own address are not requests.
    html = response.content.decode().replace(f'href="{settings.SITE_URL}', 'href="')
    assert not EXTERNAL.findall(html), EXTERNAL.findall(html)
    assert "fonts.googleapis" not in html and "cdn." not in html
    assert "core/rose-admin.css" in html
    assert "core/vendor/alpine-csp-3.16.1.js" in html
    assert "unfold/js/alpine/alpine.js" not in html
    inline = re.findall(r"<script(?![^>]*\bsrc=)([^>]*)>", html)
    assert all('type="application/json"' in attrs for attrs in inline), inline
    assert " style=" not in html


def test_csp_has_no_unsafe_inline(admin_client):
    policy = admin_client.get(reverse("admin:index"))["Content-Security-Policy"]
    directives = dict(
        (part.split()[0], part.split()[1:]) for part in policy.split(";") if part.strip()
    )
    assert directives["script-src"] == ["'self'"]
    assert "'unsafe-inline'" not in policy and "'unsafe-eval'" not in policy
    styles = directives["style-src"]
    assert styles[0] == "'self'"
    assert all(value.startswith("'sha256-") for value in styles[1:])


def test_login_pages_are_plain_and_discreet(client):
    html = client.get(reverse("admin:login")).content.decode()
    assert 'id="nav-sidebar"' not in html
    assert "core/brand/emblem-240.webp" in html and "core/rose-admin.css" in html
    assert "Email" in html and "Password" in html


def test_dashboard_needs_the_two_step_login(client, admin_user):
    client.force_login(admin_user)
    assert client.get(reverse("admin:index")).status_code == 302


@pytest.fixture
def small_world(make_user, make_membership, make_event):
    """A little of everything, for the pages and forms above (the dashboard's own tests
    are in tests/test_metrics.py)."""
    make_membership(user=make_user(display_name="secret_member", email="secret@private.example"))
    make_membership(status="pending_payment", paid_awaiting_id_check=True)
    event = make_event(capacity=10, starts_at=timezone.now() + timedelta(days=3))
    submit_rsvp(make_user(), event, 2)
    return event


# Pages added with the new sidebar


def test_rsvp_counts_page_shows_numbers_and_no_names(admin_client, make_user, make_event):
    event = make_event(capacity=10)
    submit_rsvp(make_user(display_name="secret_guest"), event, 2)
    html = admin_client.get(reverse("admin:events_rsvp_counts")).content.decode()
    # Two going: a small number, withheld like every other figure (apps.core.metrics).
    assert event.title in html and "fewer than 5</span></span> / 10</td>" in html
    assert "secret_guest" not in html
    for n in range(2):
        submit_rsvp(make_user(display_name=f"guest_more_{n}"), event, 2)
    html = admin_client.get(reverse("admin:events_rsvp_counts")).content.decode()
    assert '<td class="rose-num">6 / 10</td>' in html


def test_rsvp_counts_need_the_rsvp_permission(role_user):
    door = staff_login(Client(), role_user("door"))
    assert door.get(reverse("admin:events_rsvp_counts")).status_code == 403
    editor = staff_login(Client(), role_user("editor"))
    assert editor.get(reverse("admin:events_rsvp_counts")).status_code == 200


def test_image_review_is_for_staff_who_edit_pages_with_images(role_user):
    door = staff_login(Client(), role_user("door"))
    assert door.get(reverse("admin:image_review")).status_code == 403
    editor = staff_login(Client(), role_user("editor"))
    assert editor.get(reverse("admin:image_review")).status_code == 200


def test_form_tabs_are_buttons_that_say_which_is_showing(admin_client):
    html = admin_client.get(reverse("admin:events_event_add")).content.decode()
    nav = re.search(r'<nav aria-label="Sections of this form".*?</nav>', html, re.S).group(0)
    assert "<a " not in nav
    assert nav.count('<button type="button"') >= 2 and "x-bind:aria-pressed=" in nav


def unstyled_widgets(form_class):
    """Fields whose widget is Django's own (unstyled in Unfold's forms), by name."""
    from django.contrib.admin.widgets import (
        AutocompleteSelect,
        FilteredSelectMultiple,
        RelatedFieldWidgetWrapper,
    )
    from django.forms import HiddenInput, MultipleHiddenInput

    found = []
    for name, field in form_class().fields.items():
        widget = field.widget
        if isinstance(widget, RelatedFieldWidgetWrapper):
            widget = widget.widget
        # Django's own widgets that Unfold's stylesheet styles (filter_horizontal, autocomplete).
        if isinstance(widget, HiddenInput | MultipleHiddenInput | FilteredSelectMultiple):
            continue
        if isinstance(widget, AutocompleteSelect):
            continue
        if not any(cls.__module__.startswith("unfold.") for cls in type(widget).__mro__):
            found.append(f"{name}: {type(widget).__name__}")
    return found


def test_every_admin_form_uses_the_themed_widgets(admin_user, small_world):
    request = RequestFactory().get("/admin/")
    request.user = admin_user
    problems = {}
    for model, model_admin in admin.site._registry.items():
        obj = model._default_manager.first()
        forms = [model_admin.get_form(request, obj)]
        forms += [
            formset.form for formset, _inline in model_admin.get_formsets_with_inlines(request, obj)
        ]
        for form_class in forms:
            if bad := unstyled_widgets(form_class):
                problems[f"{model._meta.label}/{form_class.__name__}"] = bad
    assert problems == {}, "\n".join(f"{k}: {v}" for k, v in problems.items())


# The rich-text editor


def test_editor_paragraphs_are_kept_as_paragraphs(make_event):
    """Trix writes <div> blocks and blank-line spacers; the site keeps <p>s."""
    from apps.core.text import sanitize_rich_text

    trix = (
        '<div>First <strong>one</strong>.</div><div><br></div><div class="x">Second<br>line.</div>'
    )
    assert sanitize_rich_text(trix) == "<p>First <strong>one</strong>.</p><p>Second<br>line.</p>"
    event = make_event(body=trix + "<div><script>alert(1)</script></div>")
    event.refresh_from_db()
    assert event.body == "<p>First <strong>one</strong>.</p><p>Second<br>line.</p>"
    assert sanitize_rich_text("<p>Kept.</p><ul><li>As is</li></ul>") == (
        "<p>Kept.</p><ul><li>As is</li></ul>"
    )


def test_editor_keeps_paragraphs_apart_after_unfold_settings(admin_client, make_event):
    html = admin_client.get(
        reverse("admin:events_event_change", args=[make_event().pk])
    ).content.decode()
    assert "<trix-editor" in html
    order = [
        html.index(script)
        for script in ("forms/js/trix/trix.js", "forms/js/trix.config.js", "core/rose-trix.js")
    ]
    assert order == sorted(order)


def test_device_admin_never_shows_an_authenticator_secret(admin_client, admin_user):
    from django_otp.plugins.otp_static.models import StaticDevice
    from django_otp.plugins.otp_totp.models import TOTPDevice

    device = TOTPDevice.objects.get(user=admin_user)
    html = admin_client.get(
        reverse("admin:otp_totp_totpdevice_change", args=[device.pk])
    ).content.decode()
    assert device.key not in html and "qrcode" not in html.lower()
    backup = StaticDevice.objects.create(user=admin_user, name="Backup codes")
    backup.token_set.create(token="secret-backup-1")
    html = admin_client.get(
        reverse("admin:otp_static_staticdevice_change", args=[backup.pk])
    ).content.decode()
    assert "secret-backup-1" not in html
    listing = admin_client.get(reverse("admin:otp_totp_totpdevice_changelist")).content
    assert b"core/rose-admin.css" in listing and device.key.encode() not in listing


def test_breadcrumb_keeps_a_display_name_as_written(admin_client, make_user):
    user = make_user(display_name="quiet_lamp")
    html = admin_client.get(reverse("admin:accounts_user_change", args=[user.pk])).content.decode()
    assert re.search(r">\s*quiet_lamp\s*</a", html)
    assert "Quiet_lamp" not in html
    assert re.search(r">\s*Accounts\s*</a", html)


def test_button_fields_are_in_plain_words(admin_client):
    for name in ("admin:journal_post_add", "admin:education_opportunity_add"):
        html = admin_client.get(reverse(name)).content.decode()
        assert "Button label" in html and "Button link" in html, name
        assert "Cta" not in html, name


@pytest.mark.parametrize(
    ("name", "item"),
    [
        ("admin:events_rsvp_counts", "RSVPs (counts only)"),
        ("admin:memberships_summary", "Membership summary"),
        ("admin:feed_moderation", "Reports"),
        ("admin:memberships_membership_changelist", "Memberships"),
        ("admin:index", "Dashboard"),
    ],
)
def test_one_sidebar_item_is_active_on_pages_under_a_list(name, item, admin_user):
    request = RequestFactory().get(reverse(name))
    request.user = admin_user
    active = [
        entry["title"]
        for group in admin.site.get_sidebar_list(request)
        for entry in group["items"]
        if entry["active"]
    ]
    assert active == [item]
