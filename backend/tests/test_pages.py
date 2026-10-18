import pytest
from django.core.exceptions import ValidationError

from apps.pages.models import FAQItem, SiteSettings, SocialLink

pytestmark = pytest.mark.django_db


def test_site_settings_is_a_singleton():
    first = SiteSettings.load()
    second = SiteSettings(tagline="Another", hours_text="", address_text="", contact_email="")
    second.save()
    assert first.pk == second.pk == 1
    assert SiteSettings.objects.count() == 1
    assert SiteSettings.load().tagline == "Another"
    assert str(first) == "Site settings"


def test_site_settings_cannot_be_deleted():
    with pytest.raises(ValidationError):
        SiteSettings.load().delete()


def test_social_links_ordered_and_named():
    site = SiteSettings.load()
    SocialLink.objects.create(settings=site, label="Second", url="https://b.example", sort_order=2)
    SocialLink.objects.create(settings=site, label="First", url="https://a.example", sort_order=1)
    assert [str(link) for link in site.social_links.all()] == ["First", "Second"]


def test_faq_ordering_and_str():
    FAQItem.objects.create(question="Later?", answer="a", sort_order=20)
    FAQItem.objects.create(question="Sooner?", answer="a", sort_order=10)
    assert [str(f) for f in FAQItem.objects.all()] == ["Sooner?", "Later?"]


def test_site_settings_endpoint(api_client):
    site = SiteSettings.load()
    site.tagline = "Welcome"
    site.hours_text = "Thursdays"
    site.address_text = "Chicago"
    site.contact_email = "hello@example.org"
    site.quick_exit_url = "https://weather.example"
    site.save()
    SocialLink.objects.create(settings=site, label="Newsletter", url="https://news.example")

    response = api_client.get("/api/site-settings/")
    assert response.status_code == 200
    assert response.json() == {
        "tagline": "Welcome",
        "hours_text": "Thursdays",
        "address_text": "Chicago",
        "contact_email": "hello@example.org",
        "quick_exit_url": "https://weather.example",
        "social_links": [{"label": "Newsletter", "url": "https://news.example"}],
    }


def test_site_settings_endpoint_creates_empty_singleton(api_client):
    response = api_client.get("/api/site-settings/")
    assert response.status_code == 200
    assert response.json()["social_links"] == []


def test_faq_endpoint_lists_only_published_in_order(api_client):
    FAQItem.objects.create(question="Second?", answer="b", sort_order=2)
    FAQItem.objects.create(question="First?", answer="a", sort_order=1)
    FAQItem.objects.create(question="Hidden?", answer="c", is_published=False)
    data = api_client.get("/api/faqs/").json()
    assert [item["question"] for item in data] == ["First?", "Second?"]
    assert set(data[0]) == {"id", "question", "answer"}


@pytest.mark.parametrize("url", ["/api/site-settings/", "/api/faqs/"])
def test_pages_endpoints_are_read_only(api_client, url):
    assert api_client.post(url, {}, format="json").status_code == 405
