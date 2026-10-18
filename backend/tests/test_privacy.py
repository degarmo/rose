"""Private fields must never appear in any public or member-facing output."""

import importlib
import inspect
import pkgutil
import re
from datetime import timedelta

import pytest
from django.conf import settings
from rest_framework import serializers
from rest_framework.test import APIClient

import apps
from apps.accounts.models import PRIVATE_USER_FIELDS, User
from apps.accounts.serializers import PublicUserSerializer
from apps.contact.models import ContactMessage
from apps.education.models import Opportunity
from apps.pages.models import FAQItem, SiteSettings

pytestmark = pytest.mark.django_db


def project_serializer_classes():
    classes = set()
    for module_info in pkgutil.walk_packages(apps.__path__, prefix="apps."):
        if not module_info.name.endswith(".serializers"):
            continue
        module = importlib.import_module(module_info.name)
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, serializers.BaseSerializer) and obj.__module__ == module.__name__:
                classes.add(obj)
    return classes


def field_sources(serializer, prefix=""):
    """Yield (path, source) for every field, following nested serializers."""
    for name, field in serializer.fields.items():
        if getattr(field, "write_only", False):
            continue
        path = f"{prefix}{name}"
        yield path, field.source
        child = getattr(field, "child", None)
        nested = child if isinstance(child, serializers.BaseSerializer) else field
        if isinstance(nested, serializers.Serializer):
            yield from field_sources(nested, prefix=f"{path}.")


def test_public_user_serializer_exposes_only_display_name(member):
    data = PublicUserSerializer(member).data
    assert set(data) == {"display_name"}
    assert data["display_name"] == "velvet_fox"


def test_user_private_fields_list_covers_identity_fields():
    assert {"email", "legal_name", "phone", "password"} <= PRIVATE_USER_FIELDS


def test_project_serializers_are_discovered():
    names = {cls.__name__ for cls in project_serializer_classes()}
    assert {"PublicUserSerializer", "OpportunitySerializer", "ContactMessageSerializer"} <= names


@pytest.mark.parametrize(
    "serializer_class",
    sorted(
        (cls for cls in project_serializer_classes() if not getattr(cls, "self_only", False)),
        key=str,
    ),
)
def test_no_serializer_reads_private_user_fields(serializer_class):
    """Self-only serializers are checked by test_self_only_serializers_are_scoped."""
    meta = getattr(serializer_class, "Meta", None)
    serializer = serializer_class()
    model = getattr(meta, "model", None)
    for path, source in field_sources(serializer):
        leaf = source.split(".")[-1]
        touches_user = model is User or "user" in source.split(".")
        assert not (touches_user and leaf in PRIVATE_USER_FIELDS), (
            f"{serializer_class.__name__}.{path} exposes private field {leaf!r}"
        )


def test_self_only_serializers_are_scoped():
    """Self-only serializers are used in one place each, always for request.user."""
    import inspect as _inspect

    from apps.accounts import views as account_views
    from apps.accounts.serializers import AccountSerializer
    from apps.memberships import views as membership_views
    from apps.memberships.serializers import MyMembershipSerializer

    self_only = {cls for cls in project_serializer_classes() if getattr(cls, "self_only", False)}
    assert self_only == {AccountSerializer, MyMembershipSerializer}
    membership_source = _inspect.getsource(membership_views)
    assert len(re.findall(r"\bMyMembershipSerializer\(", membership_source)) == 1
    assert "MyMembershipSerializer(" in _inspect.getsource(membership_views.membership_payload)
    payload_calls = re.findall(r"membership_payload\(([^)]*)\)", membership_source)
    assert payload_calls and set(payload_calls) == {"user", "request.user"}
    call_sites = 0
    for module_info in pkgutil.walk_packages(apps.__path__, prefix="apps."):
        if module_info.name.endswith(".views"):
            module = importlib.import_module(module_info.name)
            call_sites += len(re.findall(r"\bAccountSerializer\(", _inspect.getsource(module)))
    assert call_sites == 1
    assert "AccountSerializer(user)" in _inspect.getsource(account_views.session_payload)
    assert "request.user" in _inspect.getsource(account_views.session_payload)


def test_contact_endpoint_response_does_not_echo_submission(csrf_client):
    response = csrf_client.post(
        "/api/contact/",
        {
            "name": "Echo Check",
            "email": "echo@example.org",
            "phone": "312 555 0100",
            "topic": "general",
            "message": "Please do not echo this back to me.",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json() == {"ok": True}


def test_no_public_endpoint_leaks_private_values(member, api_client):
    SiteSettings.load()
    FAQItem.objects.create(question="Q?", answer="A.")
    Opportunity.objects.create(
        title="Class", slug="class", summary="s", body="b", is_published=True
    )
    ContactMessage.objects.create(
        name="Someone Private", email="someone@private.example", topic="general", message="hi"
    )
    secrets = [
        member.email,
        member.legal_name,
        member.phone,
        member.password,
        "Someone Private",
        "someone@private.example",
    ]
    endpoints = [
        "/api/site-settings/",
        "/api/faqs/",
        "/api/education/opportunities/",
        "/api/education/opportunities/class/",
        "/api/csrf/",
    ]
    for url in endpoints:
        response = api_client.get(url)
        assert response.status_code == 200, url
        body = response.content.decode()
        for secret in secrets:
            assert secret not in body, f"{url} leaked {secret!r}"


def api_routes():
    from django.urls import get_resolver

    def walk(patterns, prefix=""):
        for pattern in patterns:
            route = prefix + str(pattern.pattern)
            if hasattr(pattern, "url_patterns"):
                yield from walk(pattern.url_patterns, route)
            else:
                yield route, pattern.name

    return [
        (route, name)
        for route, name in walk(get_resolver().url_patterns)
        if route.startswith("api/")
    ]


def test_no_api_route_lists_people():
    routes = api_routes()
    assert routes
    for route, _ in routes:
        for word in ("user", "attendee", "people", "member-list", "guest"):
            assert word not in route, route
    assert settings.ADMIN_PATH not in [route for route, _ in routes]


@pytest.fixture
def attendance(make_user, make_event):
    """Two attendees with distinctive identities on a public and an account event."""
    from datetime import timedelta

    from django.utils import timezone

    from apps.events.services import submit_rsvp
    from apps.journal.models import Post

    first = make_user(
        display_name="secret_attendee_a",
        email="attendee.a@private.example",
        legal_name="Alex Hiddenname",
        phone="312-555-0111",
    )
    second = make_user(display_name="secret_attendee_b", email="attendee.b@private.example")
    public = make_event(slug="public-night", capacity=1, show_attendee_count=True)
    account = make_event(slug="account-night", audience="account")
    for event in (public, account):
        submit_rsvp(first, event, 2 if event == account else 1, "please keep this private")
        submit_rsvp(second, event, 1, "note from b")
    Opportunity.objects.create(
        title="Class", slug="class", summary="s", body="b", is_published=True
    )
    Post.objects.create(
        slug="post",
        caption="Caption",
        is_published=True,
        published_at=timezone.now() - timedelta(minutes=1),
        event=public,
    )
    return {"first": first, "second": second, "public": public, "account": account}


def fill_route(route, name, attendance):
    slug = {
        "opportunity-detail": "class",
        "journal-detail": "post",
    }.get(name, attendance["public"].slug)
    path = "/" + re.sub(r"<(?:\w+:)?(\w+)>", slug, route)
    if name == "event-calendar":
        from django.utils import timezone

        today = timezone.localdate()
        path += f"?start={today.isoformat()}&end={(today + timedelta(days=30)).isoformat()}"
    return path


def identity_strings(user):
    return [user.display_name, user.email, user.legal_name, user.phone]


@pytest.mark.parametrize("viewer", ["anonymous", "other_verified", "attendee_b"])
def test_no_endpoint_reveals_who_is_attending(viewer, attendance, signed_in):
    """Every API route, every viewer: nobody else's attendance is ever disclosed."""
    if viewer == "anonymous":
        client = APIClient()
        hidden_people = [attendance["first"], attendance["second"]]
    elif viewer == "other_verified":
        client, _ = signed_in(display_name="nosy_neighbour")
        hidden_people = [attendance["first"], attendance["second"]]
    else:
        client, _ = signed_in(user=attendance["second"])
        hidden_people = [attendance["first"]]

    secrets = [s for person in hidden_people for s in identity_strings(person) if s]
    secrets.append("please keep this private")
    checked = 0
    for route, name in api_routes():
        for slug_event in ("public", "account"):
            if slug_event == "account" and not name.startswith("event-"):
                continue
            path = fill_route(route, name, attendance)
            path = path.replace(attendance["public"].slug, attendance[slug_event].slug)
            response = client.get(path)
            body = response.content.decode()
            for secret in secrets:
                assert secret not in body, f"{viewer} saw {secret!r} at {path}"
            checked += 1
    assert checked >= len(api_routes())


def test_public_signal_is_only_a_count(attendance, api_client):
    data = api_client.get("/api/events/public-night/").json()
    assert data["attendee_count"] == 1
    assert data["rsvp"]["mine"] is None
