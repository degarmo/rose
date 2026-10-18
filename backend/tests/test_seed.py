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
    assert site.directions_text
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


def test_seed_events_journal_and_demo_users(capsys, settings):
    from apps.accounts.models import User
    from apps.events.models import RSVP, Event
    from apps.journal.models import Post

    settings.DEBUG = True
    call_command("seed_demo")
    out = capsys.readouterr().out
    assert "demo.verified@example.org" in out

    education = Event.objects.filter(category="education")
    assert education.count() == 4
    assert all(event.opportunity_id for event in education)
    assert all(timezone.localtime(e.starts_at).weekday() == 3 for e in education)
    socials = Event.objects.filter(category="social")
    assert sorted({timezone.localtime(e.starts_at).weekday() for e in socials}) == [4, 5]
    assert socials.count() == 8
    assert Event.objects.filter(audience="members").count() == 1

    full = Event.objects.get(slug="intimate-salon")
    assert full.waitlist_enabled and full.is_full()

    assert Post.objects.live().count() == 9
    assert all(1 <= post.images.count() <= 10 for post in Post.objects.all())
    assert all(post.publish_errors() == [] for post in Post.objects.all())

    verified = User.objects.get(email="demo.verified@example.org")
    unverified = User.objects.get(email="demo.unverified@example.org")
    assert verified.email_verified and not unverified.email_verified
    assert RSVP.objects.filter(user=verified, event=full).exists()


def test_seed_hides_credentials_when_not_debug(capsys, settings):
    settings.DEBUG = False
    call_command("seed_demo")
    out = capsys.readouterr().out
    assert "demo.verified@example.org" not in out
    assert "Demo accounts" not in out
