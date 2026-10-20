"""The club's name comes from one setting and reaches every place that shows it."""

import pytest
from django.core import mail
from django.urls import reverse

from apps.core.branding import merchant_name, otp_issuer, sender_name, site_name
from apps.core.email import send_neutral_mail
from apps.events import ics
from apps.feed import club
from apps.pages.models import SiteSettings

pytestmark = pytest.mark.django_db
NAME = "The Example House"


def test_default_is_rose():
    assert site_name() == "Rose"
    assert (sender_name(), merchant_name(), otp_issuer()) == ("Rose", "Rose", "Rose")


def test_the_setting_names_everything(settings):
    settings.SITE_NAME = NAME
    assert site_name() == NAME
    assert sender_name() == merchant_name() == otp_issuer() == NAME
    assert club.club_handle() == NAME
    assert ics.default_title() == f"{NAME} - Evening"


def test_site_settings_override_the_environment(settings):
    settings.SITE_NAME = "Rose"
    site = SiteSettings.load()
    assert site_name() == "Rose"  # cached now
    site.site_name = NAME
    site.save()  # clears the cache
    assert site_name() == NAME
    site.site_name = ""
    site.save()
    assert site_name() == "Rose"


def test_each_place_can_still_have_its_own_name(settings):
    settings.SITE_NAME = NAME
    settings.EMAIL_SENDER_NAME = "Notices"
    settings.MERCHANT_DISPLAY_NAME = "ROSE MEMBERSHIP"
    settings.OTP_TOTP_ISSUER = "Rose staff"
    assert (sender_name(), merchant_name(), otp_issuer()) == (
        "Notices",
        "ROSE MEMBERSHIP",
        "Rose staff",
    )


def test_email_comes_from_the_site_name(settings):
    settings.SITE_NAME = NAME
    settings.EMAIL_SENDER_ADDRESS = "notes@example.org"
    send_neutral_mail("Hello", "Body", ["someone@example.org"])
    assert mail.outbox[0].from_email == f"{NAME} <notes@example.org>"


def test_receipts_carry_the_site_name(settings, signed_in, make_membership):
    from apps.memberships.models import Payment

    settings.SITE_NAME = NAME
    client, user = signed_in()
    payment = Payment.objects.create(
        membership=make_membership(user=user), amount_cents=2500, method="cash"
    )
    receipt = client.get(f"/api/membership/receipts/{payment.pk}/").json()
    assert receipt["merchant"] == NAME


def test_the_page_carries_the_name_for_the_app(client, settings, tmp_path):
    settings.SITE_NAME = NAME
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><head><title>Rose</title></head><body></body></html>")
    settings.FRONTEND_DIST = dist
    html = client.get("/visit").content.decode()
    assert f"<title>{NAME}</title>" in html
    assert f'<meta name="rose-site-name" content="{NAME}" />' in html


def test_the_name_is_escaped_in_the_page(client, settings, tmp_path):
    settings.SITE_NAME = 'Rose "&" <Co>'
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><head><title>Rose</title></head></html>")
    settings.FRONTEND_DIST = dist
    html = client.get("/").content.decode()
    assert "<Co>" not in html and "&lt;Co&gt;" in html


def test_the_admin_shows_the_name(admin_client, settings):
    settings.SITE_NAME = NAME
    page = admin_client.get(reverse("admin:index")).content.decode()
    assert f"Dashboard | {NAME}" in page
    assert f'<span class="rose-wordmark">{NAME}</span>' in page


def test_the_sign_in_page_shows_the_name(client, settings):
    settings.SITE_NAME = NAME
    page = client.get(reverse("admin:login")).content.decode()
    assert NAME in page
