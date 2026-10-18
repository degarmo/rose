from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.education.models import Opportunity

pytestmark = pytest.mark.django_db


def make(slug, **kwargs):
    defaults = {
        "title": slug.replace("-", " ").title(),
        "summary": "A summary.",
        "body": "A body.",
        "is_published": True,
    }
    defaults.update(kwargs)
    return Opportunity.objects.create(slug=slug, **defaults)


def test_published_queryset_and_ordering():
    make("b", sort_order=2)
    make("a", sort_order=1)
    make("hidden", is_published=False)
    assert [o.slug for o in Opportunity.objects.published()] == ["a", "b"]
    assert str(Opportunity.objects.get(slug="a")) == "A"


@pytest.mark.parametrize(
    "value,valid",
    [
        ("/contact", True),
        ("/", True),
        ("https://example.org/page", True),
        ("mailto:hello@example.org", True),
        ("", True),
        ("javascript:alert(1)", False),
        ("http://insecure.example", False),
        ("//evil.example", False),
    ],
)
def test_cta_url_validation(value, valid):
    opportunity = Opportunity(title="T", slug="t", summary="s", body="b", cta_url=value)
    if valid:
        opportunity.full_clean()
    else:
        with pytest.raises(ValidationError):
            opportunity.full_clean()


def test_hero_image_displayable_rules(gps_image_path):
    def upload():
        return SimpleUploadedFile("x.jpg", gps_image_path.read_bytes(), content_type="image/jpeg")

    assert make("none").image_is_displayable("hero_image") is False
    assert make("scenery", hero_image=upload()).image_is_displayable("hero_image") is True
    assert (
        make("faces", hero_image=upload(), hero_image_faces_visible=True).image_is_displayable(
            "hero_image"
        )
        is False
    )
    assert (
        make(
            "faces-ok",
            hero_image=upload(),
            hero_image_faces_visible=True,
            hero_image_consent_confirmed=True,
        ).image_is_displayable("hero_image")
        is True
    )


def test_list_endpoint_returns_published_only(api_client):
    make("visible", category="class", level="beginner")
    make("draft", is_published=False)
    response = api_client.get("/api/education/opportunities/")
    assert response.status_code == 200
    data = response.json()
    assert [item["slug"] for item in data] == ["visible"]
    assert data[0]["category_label"] == "Class"
    assert data[0]["level_label"] == "Beginner"
    assert "body" not in data[0]


def test_list_filters_by_category_and_level(api_client):
    make("class-beginner", category="class", level="beginner")
    make("workshop-advanced", category="workshop", level="advanced")
    make("workshop-all", category="workshop", level="all")

    def slugs(query):
        return sorted(
            i["slug"] for i in api_client.get(f"/api/education/opportunities/?{query}").json()
        )

    assert slugs("category=workshop") == ["workshop-advanced", "workshop-all"]
    assert slugs("level=beginner") == ["class-beginner"]
    assert slugs("category=workshop&level=all") == ["workshop-all"]


def test_list_rejects_unknown_filter_values(api_client):
    response = api_client.get("/api/education/opportunities/?category=nonsense")
    assert response.status_code == 400


def test_detail_endpoint_includes_body(api_client):
    starts = timezone.now() + timedelta(days=3)
    make("detail", body="Full text.", starts_at=starts, location_label="Library")
    data = api_client.get("/api/education/opportunities/detail/").json()
    assert data["body"] == "Full text."
    assert data["location_label"] == "Library"
    assert data["starts_at"] is not None
    assert data["hero_image"] is None


def test_detail_hides_unpublished(api_client):
    make("secret", is_published=False)
    assert api_client.get("/api/education/opportunities/secret/").status_code == 404


def test_hero_image_withheld_without_consent(api_client, gps_image_path):
    upload = SimpleUploadedFile("x.jpg", gps_image_path.read_bytes(), content_type="image/jpeg")
    make("faces", hero_image=upload, hero_image_faces_visible=True, hero_image_alt="Group")
    assert api_client.get("/api/education/opportunities/faces/").json()["hero_image"] is None

    Opportunity.objects.filter(slug="faces").update(hero_image_consent_confirmed=True)
    image = api_client.get("/api/education/opportunities/faces/").json()["hero_image"]
    assert image["alt"] == "Group"
    assert image["url"].startswith("http://testserver/media/education/")


def test_education_endpoints_are_read_only(api_client):
    make("x")
    assert api_client.post("/api/education/opportunities/", {}, format="json").status_code == 405
    assert api_client.delete("/api/education/opportunities/x/").status_code == 405
