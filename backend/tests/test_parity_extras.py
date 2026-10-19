"""Smaller pieces of the parity work: the staff guide, private paths, logs, the sandbox guard."""

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse

from apps.core.logging import scrub_text
from apps.memberships.providers.sandbox import SandboxProvider
from tests.conftest import staff_login

pytestmark = pytest.mark.django_db


def test_staff_guide_is_rendered_for_staff(admin_client, settings, tmp_path):
    guide = tmp_path / "staff-guide.md"
    guide.write_text("# Staff guide\n\n**Never** share the door list.\n\n<script>x</script>\n")
    settings.STAFF_GUIDE_PATH = guide
    page = admin_client.get(reverse("admin:staff_guide")).content.decode()
    assert "<h1>Staff guide</h1>" in page and "<strong>Never</strong>" in page
    assert "<script>x</script>" not in page


def test_staff_guide_needs_a_staff_login(client):
    response = client.get(reverse("admin:staff_guide"))
    assert response.status_code == 302 and "/login/" in response["Location"]


def test_only_staff_sessions_carry_the_guide_link(signed_in, client, desk_staff):
    member, _ = signed_in()
    assert member.get("/api/account/session/").json()["user"]["staff_guide_url"] is None
    staff_login(client, desk_staff)
    data = client.get("/api/account/session/").json()
    assert data["user"]["staff_guide_url"] == reverse("admin:staff_guide")


@pytest.mark.parametrize("path", ["/subscribe/confirm", "/unsubscribe"])
def test_subscription_pages_are_not_indexed(client, path, settings, tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><head></head><body></body></html>")
    settings.FRONTEND_DIST = dist
    assert client.get(path)["X-Robots-Tag"] == "noindex, nofollow"


def test_unsubscribe_tokens_never_reach_the_logs():
    line = "POST /api/newsletter/unsubscribe/abcDEF123_secret-token/ 200"
    assert "abcDEF123_secret-token" not in scrub_text(line)


def test_sandbox_runs_in_the_e2e_stack_only(settings):
    settings.DEBUG = False
    settings.DJANGO_ENV = "production"
    with pytest.raises(ImproperlyConfigured):
        SandboxProvider()
    settings.DJANGO_ENV = "e2e"
    SandboxProvider()


def test_deploy_checks_still_refuse_the_sandbox(settings):
    from apps.core.checks import deployment_settings

    settings.DJANGO_ENV = "production"
    settings.PAYMENT_PROVIDERS = ["manual", "sandbox"]
    assert "rose.E002" in {error.id for error in deployment_settings()}
