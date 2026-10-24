"""Check object storage and email from the server, with the deployed settings.

    python manage.py check_services you@example.org

1. Public bucket: uploads a tiny image, fetches it back over S3_PUBLIC_BASE_URL (expects
   HTTP 200 and the same bytes), then deletes it.
2. Private bucket: uploads a small object, confirms an anonymous request for it is refused
   and that a signed URL (as members get) works, then deletes it.
3. Email: sends a neutral test message through the configured provider to the address given.

One PASS or FAIL line per check, and an error exit if any fails. On a failure it prints
the provider's message with keys, tokens and URL signatures taken out; it never prints a
signed URL, a key or a token.
"""

import re
import uuid
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from PIL import Image

from apps.core.email import send_neutral_mail
from apps.core.private_media import private_media

from .send_test_email import BODY, SUBJECT

PREFIX = "service-check"
TIMEOUT_SECONDS = 15
QUERY = re.compile(r"\?[^\s\"'<>]*")


class CheckFailed(Exception):
    pass


def tiny_png():
    buffer = BytesIO()
    Image.new("RGB", (1, 1), (206, 33, 86)).save(buffer, format="PNG")
    return buffer.getvalue()


def fetch(url):
    """(status, body) for an anonymous GET; an HTTP error is a status, not an exception."""
    request = Request(url, headers={"User-Agent": "rose-check-services"})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, b""
    except URLError as error:
        raise CheckFailed(f"could not reach {urlsplit(url).netloc}: {error.reason}") from error


def secret_values():
    values = [settings.S3_ACCESS_KEY_ID, settings.S3_SECRET_ACCESS_KEY]
    values += [value for key, value in settings.ANYMAIL.items() if isinstance(value, str)]
    values.append(getattr(settings, "EMAIL_HOST_PASSWORD", ""))
    return [value for value in values if value and len(value) >= 4]


def clean(error):
    """The provider's message, without secrets, signatures or line breaks."""
    text = QUERY.sub("?[signature removed]", str(error) or error.__class__.__name__)
    for value in secret_values():
        text = text.replace(value, "[redacted]")
    return " ".join(text.split())[:300]


def check_public():
    if settings.STORAGE_BACKEND != "s3":
        raise CheckFailed(f"STORAGE_BACKEND is {settings.STORAGE_BACKEND}, not s3")
    body = tiny_png()
    name = default_storage.save(f"{PREFIX}/{uuid.uuid4().hex}.png", ContentFile(body))
    try:
        url = default_storage.url(name)
        base = settings.S3_PUBLIC_BASE_URL
        if not url.startswith(f"{base}/"):
            raise CheckFailed(f"the public address is not under S3_PUBLIC_BASE_URL ({base})")
        status, fetched = fetch(url)
        if status != 200:
            raise CheckFailed(f"{urlsplit(base).netloc} answered HTTP {status}, not 200")
        if fetched != body:
            raise CheckFailed(f"{urlsplit(base).netloc} served different bytes")
    finally:
        default_storage.delete(name)
    if default_storage.exists(name):
        raise CheckFailed("the test image could not be deleted")
    return f"uploaded, fetched from {urlsplit(base).netloc} (HTTP 200) and deleted"


def check_private():
    if settings.STORAGE_BACKEND != "s3":
        raise CheckFailed(f"STORAGE_BACKEND is {settings.STORAGE_BACKEND}, not s3")
    media = private_media()
    body = f"service check {uuid.uuid4().hex}".encode()
    name = media.save(f"{PREFIX}/{uuid.uuid4().hex}.txt", body)
    try:
        signed = media.storage.signed_url(name, "text/plain")
        unsigned = signed.split("?", 1)[0]
        status, _ = fetch(unsigned)
        if status < 400:
            raise CheckFailed(f"an anonymous request was answered HTTP {status}: it is public")
        refused = status
        status, fetched = fetch(signed)
        if status != 200 or fetched != body:
            raise CheckFailed(f"the signed URL answered HTTP {status}, not 200 with the object")
    finally:
        media.delete(name)
    if media.exists(name):
        raise CheckFailed("the test object could not be deleted")
    return f"anonymous request refused (HTTP {refused}), signed URL worked, object deleted"


def check_email(address):
    sent = send_neutral_mail(SUBJECT, BODY, to=[address])
    if sent != 1:
        raise CheckFailed(f"the {settings.EMAIL_PROVIDER} backend reported {sent} sent, not 1")
    return f"test message accepted by {settings.EMAIL_PROVIDER}"


class Command(BaseCommand):
    help = "Check the public and private buckets and email from this server. Prints no secrets."

    def add_arguments(self, parser):
        parser.add_argument("address", help="Where to send the test email.")

    def handle(self, *args, address, **options):
        checks = [
            ("Public bucket", check_public),
            ("Private bucket", check_private),
            ("Email", lambda: check_email(address)),
        ]
        failed = 0
        for label, check in checks:
            # Whatever the provider raises becomes a FAIL line, and the next check still runs.
            try:
                detail = check()
            except Exception as error:
                failed += 1
                self.stdout.write(self.style.ERROR(f"FAIL  {label}: {clean(error)}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"PASS  {label}: {detail}"))
        if failed:
            raise CommandError(f"{failed} of {len(checks)} checks failed.")
        self.stdout.write(f"All {len(checks)} checks passed.")
