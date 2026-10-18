import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.education.models import Opportunity
from apps.pages.models import FAQItem, SiteSettings

pytestmark = pytest.mark.django_db


def test_seed_demo_loads_content_and_is_idempotent():
    call_command("seed_demo")
    call_command("seed_demo")
    assert Opportunity.objects.published().count() == 6
    assert FAQItem.objects.filter(is_published=True).count() == 8
    site = SiteSettings.load()
    assert site.tagline
    assert site.hours_text
    assert site.contact_email
    categories = set(Opportunity.objects.values_list("category", flat=True))
    levels = set(Opportunity.objects.values_list("level", flat=True))
    assert categories == {"class", "workshop", "mentorship", "volunteer"}
    assert levels == {"beginner", "intermediate", "advanced", "all"}


def test_seeded_dates_fall_on_thursday_evenings():
    call_command("seed_demo")
    for opportunity in Opportunity.objects.exclude(starts_at=None):
        local = timezone.localtime(opportunity.starts_at)
        assert local.weekday() == 3
        assert local.hour == 19


def test_seeded_cta_urls_are_valid():
    call_command("seed_demo")
    for opportunity in Opportunity.objects.all():
        opportunity.full_clean()
