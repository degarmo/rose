"""Nightly encrypted database backup (in addition to Render's own Postgres backups).

pg_dump writes a custom-format dump, which is encrypted on the way out with
an age public key (BACKUP_AGE_RECIPIENT). The matching private key is never on
the server, so the server cannot read its own backups. The result goes to the
private bucket under backups/, kept BACKUP_RETENTION_DAYS (the bucket's
lifecycle rule; this module also prunes, as a backstop). Restoring is in
docs/ops/restore.md.
"""

import os
import subprocess
import tempfile
from datetime import timedelta

import pyrage
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files import File
from django.utils import timezone

from .models import AuditLog, audit
from .private_media import BACKUP_PREFIX, private_media


class BackupError(Exception):
    pass


def _pg_env_and_args():
    db = settings.DATABASES["default"]
    env = {**os.environ, "PGPASSWORD": db.get("PASSWORD") or ""}
    args = [
        settings.PG_DUMP_PATH,
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        f"--host={db.get('HOST') or 'localhost'}",
        f"--port={db.get('PORT') or 5432}",
        f"--username={db.get('USER') or ''}",
        f"--dbname={db['NAME']}",
    ]
    return env, args


def recipient():
    if not settings.BACKUP_AGE_RECIPIENT:
        raise ImproperlyConfigured("BACKUP_AGE_RECIPIENT is not set.")
    try:
        return pyrage.x25519.Recipient.from_str(settings.BACKUP_AGE_RECIPIENT)
    except pyrage.RecipientError as exc:
        raise ImproperlyConfigured("BACKUP_AGE_RECIPIENT is not an age public key.") from exc


def run_backup(now=None):
    """Dump, encrypt, upload. Returns the stored name."""
    now = now or timezone.now()
    key = recipient()
    env, args = _pg_env_and_args()
    with tempfile.TemporaryFile() as dump, tempfile.TemporaryFile() as sealed:
        result = subprocess.run(args, stdout=dump, stderr=subprocess.PIPE, env=env, check=False)
        if result.returncode != 0:
            # pg_dump's message names the database, never data; keep it short.
            raise BackupError(f"pg_dump failed: {result.stderr.decode()[-300:].strip()}")
        dump.seek(0)
        pyrage.encrypt_io(dump, sealed, [key])
        sealed.seek(0)
        name = f"{BACKUP_PREFIX}{now:%Y-%m-%dT%H%M%SZ}.dump.age"
        stored = private_media().storage.save(name, File(sealed, name=name))
    prune(now)
    audit(AuditLog.Category.OPERATIONS, "backup_created", None, "Nightly database backup", "backup")
    return stored


def prune(now=None):
    now = now or timezone.now()
    cutoff = now - timedelta(days=settings.BACKUP_RETENTION_DAYS)
    media = private_media()
    removed = 0
    for name in media.iter_prefix(BACKUP_PREFIX):
        if media.modified(name) < cutoff:
            media.storage.delete(name)
            removed += 1
    return removed
