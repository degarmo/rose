"""Private fields must never appear in any public or member-facing output."""

import importlib
import inspect
import pkgutil

import pytest
from django.conf import settings
from rest_framework import serializers

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


@pytest.mark.parametrize("serializer_class", sorted(project_serializer_classes(), key=str))
def test_no_serializer_reads_private_user_fields(serializer_class):
    meta = getattr(serializer_class, "Meta", None)
    serializer = serializer_class()
    model = getattr(meta, "model", None)
    for path, source in field_sources(serializer):
        leaf = source.split(".")[-1]
        touches_user = model is User or "user" in source.split(".")
        assert not (touches_user and leaf in PRIVATE_USER_FIELDS), (
            f"{serializer_class.__name__}.{path} exposes private field {leaf!r}"
        )


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
        "/api/health/",
        "/api/csrf/",
    ]
    for url in endpoints:
        response = api_client.get(url)
        assert response.status_code == 200, url
        body = response.content.decode()
        for secret in secrets:
            assert secret not in body, f"{url} leaked {secret!r}"


def test_no_api_route_lists_users():
    from django.urls import get_resolver

    def walk(patterns, prefix=""):
        for pattern in patterns:
            route = prefix + str(pattern.pattern)
            if hasattr(pattern, "url_patterns"):
                yield from walk(pattern.url_patterns, route)
            else:
                yield route

    api_routes = [r for r in walk(get_resolver().url_patterns) if r.startswith("api/")]
    assert api_routes
    for route in api_routes:
        assert "user" not in route and "account" not in route, route
    assert settings.ADMIN_PATH not in api_routes
