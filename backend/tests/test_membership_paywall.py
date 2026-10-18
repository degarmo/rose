"""Members-only education: the locked body never leaves the server."""

import pytest
from rest_framework.test import APIClient

from apps.education.models import Opportunity

pytestmark = pytest.mark.django_db

SECRET_BODY = "The members-only lesson plan, word for word."


@pytest.fixture
def locked_class(make_tier):
    make_tier(name="Monthly", slug="monthly")
    make_tier(name="Pass", slug="pass", grants_members_education=False)
    return Opportunity.objects.create(
        title="Advanced lab",
        slug="advanced-lab",
        summary="A short public summary.",
        body=SECRET_BODY,
        cta_label="Reserve",
        cta_url="/events/secret-night",
        members_only=True,
        is_published=True,
    )


def detail(client):
    return client.get("/api/education/opportunities/advanced-lab/")


@pytest.mark.parametrize("who", ["anonymous", "account", "expired", "pass_only"])
def test_locked_for_everyone_without_education(
    who, locked_class, signed_in, make_membership, make_tier
):
    if who == "anonymous":
        client = APIClient()
    else:
        client, user = signed_in()
        if who == "expired":
            make_membership(user=user, status="expired")
        if who == "pass_only":
            make_membership(user=user, tier=make_tier(grants_members_education=False))
    response = detail(client)
    assert response.status_code == 200
    data = response.json()
    assert data["locked"] is True
    assert data["body"] is None
    assert data["cta_url"] == "" and data["cta_label"] == ""
    assert data["summary"] == "A short public summary."
    assert data["paywall"]["benefit"] == "Members-only classes come with membership."
    assert "Monthly" in data["paywall"]["tiers"] and "Pass" not in data["paywall"]["tiers"]
    raw = response.content.decode()
    assert SECRET_BODY not in raw and "secret-night" not in raw
    listing = client.get("/api/education/opportunities/").content.decode()
    assert SECRET_BODY not in listing and "secret-night" not in listing


@pytest.mark.parametrize("status", ["active", "grace"])
def test_unlocked_for_members(status, locked_class, signed_in, make_membership):
    client, user = signed_in()
    make_membership(user=user, status=status)
    data = detail(client).json()
    assert data["locked"] is False
    assert data["paywall"] is None
    assert data["body"] == SECRET_BODY
    assert data["cta_url"] == "/events/secret-night"


def test_public_classes_are_never_locked(signed_in):
    Opportunity.objects.create(title="Open", slug="open", summary="s", body="b", is_published=True)
    data = APIClient().get("/api/education/opportunities/open/").json()
    assert data["locked"] is False and data["body"] == "b" and data["paywall"] is None
