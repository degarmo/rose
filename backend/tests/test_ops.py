"""Operations: test email, feed kill switch, retention, watermark purge and backups."""

import os
import subprocess
from datetime import timedelta
from io import StringIO

import pyrage
import pytest
from django.core import mail
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.contact.models import ContactMessage
from apps.contact.tasks import purge_old_messages
from apps.core import backups
from apps.core.models import AuditLog
from apps.core.private_media import private_media, watermark_name
from apps.feed.tasks import purge_old_watermarks

pytestmark = pytest.mark.django_db


# send_test_email


def test_send_test_email_is_staff_only_and_logged(make_user):
    with pytest.raises(CommandError):
        call_command("send_test_email", "someone@example.org", staff="nobody@example.org")
    member = make_user(email="member@example.org")
    with pytest.raises(CommandError):
        call_command("send_test_email", "someone@example.org", staff=member.email)
    staff = make_user(email="desk@example.org", is_staff=True)
    out = StringIO()
    call_command("send_test_email", "someone@example.org", staff=staff.email, stdout=out)
    (message,) = mail.outbox
    assert message.subject == "Test message"
    assert message.to == ["someone@example.org"]
    entry = AuditLog.objects.get(action="test_email_sent")
    assert entry.actor == staff and "someone@example.org" not in entry.target_label
    assert "someone@example.org" not in out.getvalue()


# Feed kill switch


@pytest.mark.parametrize(
    "path",
    ["/api/members/feed/", "/api/members/me/", "/api/members/notifications/", "/api/account/feed/"],
)
def test_feed_enabled_false_hides_every_feed_path(member_client, settings, path):
    client, _ = member_client()
    assert client.get(path).status_code == 200
    settings.FEED_ENABLED = False
    response = client.get(path)
    assert response.status_code == 404
    assert client.post(path, {}, format="json").status_code == 404


def test_feed_media_is_hidden_too(member_client, make_post, settings):
    client, member = member_client()
    post = make_post(member, images=1)
    url = f"/api/members/media/{post.images.get().public_id}/"
    settings.FEED_WATERMARK = False
    assert client.get(url).status_code == 200
    settings.FEED_ENABLED = False
    assert client.get(url).status_code == 404


# Retention


def test_handled_contact_messages_expire(settings):
    settings.CONTACT_RETENTION_DAYS = 30
    old = ContactMessage.objects.create(
        name="A", email="a@example.org", message="x" * 20, handled=True
    )
    open_case = ContactMessage.objects.create(name="B", email="b@example.org", message="x" * 20)
    recent = ContactMessage.objects.create(
        name="C", email="c@example.org", message="x" * 20, handled=True
    )
    ContactMessage.objects.filter(pk__in=[old.pk, open_case.pk]).update(
        created_at=timezone.now() - timedelta(days=31)
    )
    assert purge_old_messages() == 1
    assert set(ContactMessage.objects.values_list("pk", flat=True)) == {open_case.pk, recent.pk}


def test_old_watermark_copies_are_purged(private_root, settings):
    media = private_media()
    old_name = watermark_name("feed/a.webp", 1, "viewer 2026-10-01")
    new_name = watermark_name("feed/b.webp", 1, "viewer 2026-10-18")
    media.save(old_name, b"old")
    media.save(new_name, b"new")
    past = (timezone.now() - timedelta(days=8)).timestamp()
    os.utime(private_root / old_name, (past, past))
    assert purge_old_watermarks() == 1
    assert not media.exists(old_name) and media.exists(new_name)


def test_deleting_an_image_deletes_its_watermarked_copies(private_root):
    media = private_media()
    media.save("feed/photo.webp", b"pixels")
    copies = [watermark_name("feed/photo.webp", viewer, f"v{viewer}") for viewer in (1, 2, 3)]
    for copy in copies:
        media.save(copy, b"marked")
    unrelated = watermark_name("feed/other.webp", 1, "v1")
    media.save(unrelated, b"marked")
    media.delete("feed/photo.webp")
    assert not any(media.exists(copy) for copy in copies)
    assert media.exists(unrelated)


def test_viewer_copies_go_with_the_viewer(private_root):
    media = private_media()
    mine = [watermark_name(f"feed/{n}.webp", 7, "me") for n in range(3)]
    theirs = watermark_name("feed/0.webp", 8, "them")
    for name in [*mine, theirs]:
        media.save(name, b"x")
    media.delete_viewer_copies(7)
    assert not any(media.exists(name) for name in mine)
    assert media.exists(theirs)


def test_watermark_keys_reveal_nothing():
    name = watermark_name("feed/abc123.webp", 42, "velvet_fox  2026-10-18")
    assert "abc123" not in name and "42" not in name.split("/")[-1][:2] and "velvet" not in name
    assert name.startswith("watermarks/") and name.endswith(".webp")


# Backups


@pytest.fixture
def age_key(settings):
    identity = pyrage.x25519.Identity.generate()
    settings.BACKUP_AGE_RECIPIENT = str(identity.to_public())
    return identity


def pg_dump_available():
    """CI sets REQUIRE_PG_DUMP=1 so a missing pg_dump fails instead of skipping."""
    try:
        found = subprocess.run(["pg_dump", "--version"], capture_output=True).returncode == 0
    except FileNotFoundError:
        found = False
    if not found and os.environ.get("REQUIRE_PG_DUMP"):
        pytest.fail("pg_dump is required here")
    return found


@pytest.mark.django_db(transaction=True)
def test_backup_is_encrypted_and_restorable(private_root, age_key, settings, tmp_path):
    if not pg_dump_available():
        pytest.skip("pg_dump is not installed here")
    settings.BACKUP_ENABLED = True
    name = backups.run_backup()
    assert name.startswith("backups/") and name.endswith(".dump.age")
    sealed = private_media().read(name)
    assert b"PGDMP" not in sealed  # the custom-format magic is not visible
    plain = pyrage.decrypt(sealed, [age_key])
    assert plain.startswith(b"PGDMP")
    listing = subprocess.run(
        ["pg_restore", "--list"], input=plain, capture_output=True, check=True
    ).stdout.decode()
    assert "TABLE public accounts_user" in listing
    assert AuditLog.objects.filter(action="backup_created").exists()


def test_backup_needs_a_public_key(settings):
    from django.core.exceptions import ImproperlyConfigured

    settings.BACKUP_AGE_RECIPIENT = ""
    with pytest.raises(ImproperlyConfigured):
        backups.recipient()
    settings.BACKUP_AGE_RECIPIENT = "AGE-SECRET-KEY-1NOTAPUBLICKEY"
    with pytest.raises(ImproperlyConfigured):
        backups.recipient()


def test_backup_task_does_nothing_unless_enabled(settings):
    from apps.core.tasks import nightly_backup

    settings.BACKUP_ENABLED = False
    assert nightly_backup() is None


def test_old_backups_are_pruned(private_root, settings):
    settings.BACKUP_RETENTION_DAYS = 30
    media = private_media()
    media.save("backups/old.dump.age", b"x")
    media.save("backups/new.dump.age", b"y")
    past = (timezone.now() - timedelta(days=31)).timestamp()
    os.utime(private_root / "backups/old.dump.age", (past, past))
    assert backups.prune() == 1
    assert media.exists("backups/new.dump.age")


# verify_restore


def test_verify_restore_passes_and_writes_counts(tmp_path, make_user):
    import json

    make_user()
    out = StringIO()
    counts_file = tmp_path / "counts.json"
    call_command("verify_restore", write_counts=str(counts_file), stdout=out)
    assert "Restore verified" in out.getvalue()
    counts = json.loads(counts_file.read_text())
    assert counts["accounts_user"] == 1
    call_command("verify_restore", counts_file=str(counts_file), stdout=StringIO())


def test_verify_restore_reports_missing_rows(tmp_path, make_user):
    import json

    make_user()
    counts_file = tmp_path / "counts.json"
    counts_file.write_text(json.dumps({"accounts_user": 5}))
    out = StringIO()
    with pytest.raises(CommandError, match="problems found"):
        call_command("verify_restore", counts_file=str(counts_file), stdout=out)
    assert "accounts_user: 5 rows before, 1 after" in out.getvalue()
