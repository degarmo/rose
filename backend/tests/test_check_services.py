"""manage.py check_services: storage and email checked from the server, with no secrets shown."""

import io
import json

import pytest
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.management import CommandError, call_command

from apps.core.management.commands.check_services import clean
from apps.pages.models import SiteImage

pytestmark = pytest.mark.django_db

TOKEN = "pm-server-token-0123456789"


class RefusingBackend(BaseEmailBackend):
    """A provider that turns the message down, quoting its credentials back."""

    def send_messages(self, email_messages):
        token = settings.ANYMAIL["POSTMARK_SERVER_TOKEN"]
        raise RuntimeError(f"401 Unauthorized: server token {token} is not valid")


def run(address="ops@example.org"):
    out = io.StringIO()
    try:
        call_command("check_services", address, stdout=out)
    except CommandError as error:
        return out.getvalue(), str(error)
    return out.getvalue(), None


def public_policy(bucket):
    return json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{bucket}/*"],
                }
            ],
        }
    )


def test_everything_passes_and_nothing_is_left_behind(s3, mailoutbox):
    out, error = run()
    assert error is None
    assert out.count("PASS") == 3 and "FAIL" not in out
    assert "anonymous request refused (HTTP 403), signed URL worked" in out
    assert s3.keys(s3.public) == [] and s3.keys(s3.private) == []
    [message] = mailoutbox
    assert message.to == ["ops@example.org"] and message.subject == "Test message"
    # No key, secret or URL signature reaches the console.
    for secret in (settings.S3_ACCESS_KEY_ID, settings.S3_SECRET_ACCESS_KEY, "X-Amz-Signature"):
        assert secret not in out


def test_a_public_bucket_that_does_not_serve_its_files_fails(s3, mailoutbox):
    s3.client.delete_bucket_policy(Bucket=s3.public)
    out, error = run()
    assert "FAIL  Public bucket:" in out and "answered HTTP 403, not 200" in out
    assert "PASS  Private bucket" in out and "PASS  Email" in out
    assert error == "1 of 3 checks failed."
    assert s3.keys(s3.public) == []


def test_a_private_bucket_open_to_anyone_fails(s3, mailoutbox):
    s3.client.put_bucket_policy(Bucket=s3.private, Policy=public_policy(s3.private))
    out, error = run()
    assert "FAIL  Private bucket: an anonymous request was answered HTTP 200: it is public" in out
    assert error == "1 of 3 checks failed."
    assert s3.keys(s3.private) == []


def test_local_storage_fails_the_storage_checks(settings, mailoutbox):
    settings.STORAGE_BACKEND = "local"
    out, error = run()
    assert out.count("STORAGE_BACKEND is local, not s3") == 2
    assert "PASS  Email" in out
    assert error == "2 of 3 checks failed."


def test_an_email_provider_error_is_shown_without_its_token(settings, mailoutbox):
    settings.STORAGE_BACKEND = "local"
    settings.ANYMAIL = {**settings.ANYMAIL, "POSTMARK_SERVER_TOKEN": TOKEN}
    settings.EMAIL_BACKEND = "tests.test_check_services.RefusingBackend"
    out, _ = run()
    assert "FAIL  Email: 401 Unauthorized: server token [redacted] is not valid" in out
    assert TOKEN not in out


def test_clean_removes_signatures_and_keys(settings):
    settings.S3_SECRET_ACCESS_KEY = "very-secret-key"
    message = (
        "Forbidden https://bucket.example/a.txt?X-Amz-Signature=abc&X-Amz-Credential=k "
        "for very-secret-key\n(retry)"
    )
    assert clean(message) == (
        "Forbidden https://bucket.example/a.txt?[signature removed] for [redacted] (retry)"
    )


def test_the_starting_page_pictures_are_put_back_in_an_empty_bucket(s3):
    out = io.StringIO()
    call_command("store_site_image_seeds", stdout=out)
    assert "5 starting picture(s) stored" in out.getvalue()
    assert "Every page slot's picture is in storage." in out.getvalue()
    assert "site-images/dance-floor.webp" in s3.keys(s3.public, "site-images/")
    # Repeating it changes nothing; a slot whose own upload is gone is named.
    SiteImage.objects.filter(slot="about.hero").update(image="site-images/lost.webp")
    out = io.StringIO()
    call_command("store_site_image_seeds", stdout=out)
    assert "0 starting picture(s) stored" in out.getvalue()
    assert "upload again in Admin > Content > Page images: about.hero" in out.getvalue()
