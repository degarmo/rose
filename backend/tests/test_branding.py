"""The club's name comes from one setting and reaches every place people read the site.

Discreet places (email senders and subjects, calendar files, receipts, the authenticator
app, member-app tab titles, home-screen names) keep the neutral name. The tests set a
name with "Chicago" in it, so any leak into a discreet place shows up as that word.
"""

import pytest
from django.core import mail
from django.test import override_settings
from django.urls import reverse

from apps.core.branding import (
    display_name,
    merchant_name,
    neutral_name,
    otp_issuer,
    sender_name,
    short_name,
)
from apps.core.email import send_neutral_mail
from apps.events import ics
from apps.feed import club
from apps.pages.models import SiteSettings

pytestmark = pytest.mark.django_db
NAME = "The Chicago Example"
SHORT = "Chicago Example"
LEAK = "Chicago"


@pytest.fixture
def named(settings):
    settings.SITE_DISPLAY_NAME = NAME
    settings.SITE_SHORT_NAME = SHORT
    settings.EMAIL_SENDER_ADDRESS = "notes@example.org"


@pytest.fixture
def built_page(settings, tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><head><title>Rose</title></head><body></body></html>")
    settings.FRONTEND_DIST = dist


def test_defaults_are_rose():
    assert display_name() == short_name() == "Rose"
    assert (neutral_name(), sender_name(), merchant_name(), otp_issuer()) == ("Rose",) * 4


def test_the_settings_name_the_site(named):
    assert display_name() == NAME
    assert short_name() == SHORT
    assert club.club_handle() == NAME


def test_site_settings_override_the_environment(named):
    site = SiteSettings.load()
    assert display_name() == NAME  # cached now
    site.site_display_name = "Another House"
    site.save()  # clears the cache
    # A name set in the admin without a short form is its own short form.
    assert (display_name(), short_name()) == ("Another House", "Another House")
    site.site_short_name = "Another"
    site.save()
    assert short_name() == "Another"
    site.site_display_name = site.site_short_name = ""
    site.save()
    assert (display_name(), short_name()) == (NAME, SHORT)


# Discreet places never carry the club's name


def test_neutral_names_ignore_the_club_name(named):
    for name in (neutral_name(), sender_name(), merchant_name(), otp_issuer()):
        assert name == "Rose"


def test_the_neutral_settings_can_be_renamed(named):
    with override_settings(
        EMAIL_SENDER_NAME="Notices",
        MERCHANT_DISPLAY_NAME="ROSE MEMBERSHIP",
        OTP_TOTP_ISSUER="Rose staff",
    ):
        assert (sender_name(), merchant_name(), otp_issuer()) == (
            "Notices",
            "ROSE MEMBERSHIP",
            "Rose staff",
        )


def test_email_sender_and_subject_stay_neutral(named, csrf_client):
    send_neutral_mail("Hello", "Body", ["someone@example.org"])
    csrf_client.post("/api/newsletter/subscribe/", {"email": "reader@example.org"}, format="json")
    assert len(mail.outbox) == 2
    for message in mail.outbox:
        assert message.from_email == "Rose <notes@example.org>"
        assert LEAK not in message.subject


def test_calendar_files_stay_neutral(named, api_client, make_event):
    assert ics.default_title() == "Rose - Evening"
    event = make_event(title="Evening")
    body = api_client.get(f"/api/events/{event.slug}/calendar.ics").content.decode()
    assert "SUMMARY:Rose - Evening" in body and "PRODID:-//Rose//" in body
    assert LEAK not in body


def test_receipts_stay_neutral(named, signed_in, make_membership):
    from apps.memberships.models import Payment

    client, user = signed_in()
    payment = Payment.objects.create(
        membership=make_membership(user=user), amount_cents=2500, method="cash"
    )
    receipt = client.get(f"/api/membership/receipts/{payment.pk}/").json()
    assert receipt["merchant"] == "Rose"
    assert LEAK not in str(receipt)


def test_the_authenticator_app_stays_neutral(named, make_user):
    from django_otp.plugins.otp_totp.models import TOTPDevice

    from apps.core.admin_auth import _otpauth_url

    staff = make_user()
    url, _ = _otpauth_url(TOTPDevice.objects.create(user=staff, name="app"), staff)
    assert "issuer=Rose&" in url and LEAK not in url


def test_member_app_tabs_and_home_screen_names_stay_neutral(named, client, built_page):
    html = client.get("/members/feed").content.decode()
    assert "<title>Rose</title>" in html
    assert '<meta name="apple-mobile-web-app-title" content="Rose" />' in html
    assert '<meta name="application-name" content="Rose" />' in html
    assert "og:title" not in html and "og:site_name" not in html
    # The app still knows the short name for its sidebar.
    assert f'<meta name="rose-site-short-name" content="{SHORT}" />' in html


# Headings and titles use the setting


def test_public_pages_carry_the_name(named, client, built_page):
    html = client.get("/visit").content.decode()
    assert f"<title>{NAME}</title>" in html
    assert f'<meta property="og:title" content="{NAME}" />' in html
    assert f'<meta property="og:site_name" content="{NAME}" />' in html
    assert f'<meta name="rose-site-display-name" content="{NAME}" />' in html
    assert f'<meta name="rose-site-short-name" content="{SHORT}" />' in html
    assert '<meta name="rose-site-neutral-name" content="Rose" />' in html
    assert '<meta name="apple-mobile-web-app-title" content="Rose" />' in html
    # Only the member app is neutral, not a page whose path starts the same way.
    assert f"<title>{NAME}</title>" in client.get("/membership").content.decode()


def test_the_name_is_escaped_in_the_page(settings, client, built_page):
    settings.SITE_DISPLAY_NAME = settings.SITE_SHORT_NAME = 'Rose "&" <Co>'
    html = client.get("/").content.decode()
    assert "<Co>" not in html and "&lt;Co&gt;" in html


def test_the_admin_shows_the_name(named, admin_client):
    page = admin_client.get(reverse("admin:index")).content.decode()
    assert f"Dashboard | {NAME}" in page
    assert f'<span class="rose-wordmark">{NAME}</span>' in page


def test_the_sign_in_page_shows_the_name(named, client):
    page = client.get(reverse("admin:login")).content.decode()
    assert NAME in page


def test_page_copy_and_faqs_fill_in_the_name(named, api_client):
    from apps.pages.models import FAQItem, PageContent

    PageContent.objects.create(page="home", key="intro", value="{display_name} is a club.")
    PageContent.objects.create(
        page="home", key="body", value="<p>Welcome to {short_name}</p>", format="rich"
    )
    FAQItem.objects.create(question="What is {display_name}?", answer="{short_name} is a club.")
    entries = api_client.get("/api/content/home/").json()["entries"]
    assert entries["intro"]["value"] == f"{NAME} is a club."
    assert entries["body"]["value"] == f"<p>Welcome to {SHORT}</p>"
    faq = api_client.get("/api/faqs/").json()[0]
    assert faq["question"] == f"What is {NAME}?" and faq["answer"] == f"{SHORT} is a club."


def test_the_filled_in_name_follows_a_change(api_client):
    from apps.pages.models import PageContent

    PageContent.objects.create(page="home", key="intro", value="{display_name} is a club.")
    assert api_client.get("/api/content/home/").json()["entries"]["intro"]["value"] == (
        "Rose is a club."
    )
    site = SiteSettings.load()
    site.site_display_name = NAME
    site.save()
    assert api_client.get("/api/content/home/").json()["entries"]["intro"]["value"] == (
        f"{NAME} is a club."
    )


def test_demo_tiers_carry_the_name(named):
    from apps.memberships.demo import upsert_tiers

    tiers = upsert_tiers(placeholder=True)
    assert tiers["rose"].name == NAME and tiers["rose-plus"].name == f"{NAME} +"


def test_loaded_tiers_fill_in_the_name(named, tmp_path, make_tier):
    import yaml
    from django.core.management import call_command

    from apps.memberships.models import Tier

    make_tier(slug="plus", price_cents=6000)
    (tmp_path / "join.yaml").write_text(
        yaml.safe_dump(
            {
                "status": "approved",
                "source_url": [],
                "tiers": [
                    {
                        "slug": "plus",
                        "name": "{display_name} +",
                        "description": "Every event at {short_name}.",
                    }
                ],
            }
        )
    )
    call_command("load_site_content", "--dir", str(tmp_path), "--commit", stdout=None)
    tier = Tier.objects.get(slug="plus")
    assert (tier.name, tier.description) == (f"{NAME} +", f"Every event at {SHORT}.")
