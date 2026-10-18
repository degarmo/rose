"""Copy every local media file to the S3 buckets, verified, without touching the database.

    python manage.py migrate_media_to_storage            # dry run: what would be copied
    python manage.py migrate_media_to_storage --commit   # copy and verify

Sources and destinations:
- DJANGO_MEDIA_ROOT (journal, education and event images)  -> public bucket, same names
- PRIVATE_MEDIA_ROOT (member images, avatars, exports)      -> private bucket, same names
- SITE_IMAGES_DIR (fetched site imagery)                    -> public bucket under site/

Object names are the names the database already stores, so no row changes.
Each copy is verified by size and MD5 checksum. Files already present with the
same checksum are skipped, so the command can be run again safely. Old local
watermark caches are not copied; copies are re-made on demand.
"""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import storages
from django.core.management.base import BaseCommand, CommandError
from storages.utils import clean_name

SKIP_DIRS = {"watermark-cache", "watermarks"}
SITE_PREFIX = "site/"


@dataclass
class Counts:
    scanned: int = 0
    present: int = 0
    copied: int = 0
    to_copy: int = 0
    replaced: int = 0
    failed: list = field(default_factory=list)


def md5_of(handle):
    digest = hashlib.md5(usedforsecurity=False)
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def remote_md5(storage, name):
    """The object's MD5: from its ETag when that is a plain MD5, otherwise by reading it."""
    etag = storage.bucket.Object(storage._normalize_name(clean_name(name))).e_tag
    etag = (etag or "").strip('"')
    if etag and "-" not in etag and len(etag) == 32:
        return etag
    with storage.open(name, "rb") as handle:
        return md5_of(handle)


def local_files(root):
    if not root.is_dir():
        return []
    files = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_file() and not (set(relative.parts) & SKIP_DIRS) and path.name != ".gitkeep":
            files.append((path, relative.as_posix()))
    return files


class Command(BaseCommand):
    help = "Copy local media to the S3 buckets with checksum verification. Dry run unless --commit."

    def add_arguments(self, parser):
        parser.add_argument("--commit", action="store_true", help="Copy for real.")
        parser.add_argument(
            "--dry-run", action="store_true", help="The default; listed for clarity."
        )

    def handle(self, *args, commit, dry_run, **options):
        if commit and dry_run:
            raise CommandError("Choose either --dry-run or --commit.")
        public, private = storages["default"], storages["private"]
        if not (hasattr(public, "bucket") and hasattr(private, "bucket")):
            raise CommandError("Set STORAGE_BACKEND=s3 (and the S3_* settings) first.")

        plan = [
            ("public", Path(settings.MEDIA_ROOT), public, ""),
            ("private", Path(settings.PRIVATE_MEDIA_ROOT), private, ""),
            ("site images", Path(settings.SITE_IMAGES_DIR), public, SITE_PREFIX),
        ]
        totals = Counts()
        for label, root, storage, prefix in plan:
            counts = self.copy_tree(root, storage, prefix, commit)
            self.stdout.write(
                f"{label}: {counts.scanned} files, {counts.present} already there, "
                f"{counts.copied if commit else counts.to_copy} "
                f"{'copied and verified' if commit else 'to copy'}"
                + (f", {counts.replaced} replaced" if counts.replaced else "")
                + (f", {len(counts.failed)} failed" if counts.failed else "")
            )
            for name in counts.failed:
                self.stdout.write(self.style.ERROR(f"  failed: {name}"))
            totals.scanned += counts.scanned
            totals.present += counts.present
            totals.copied += counts.copied
            totals.to_copy += counts.to_copy
            totals.failed += counts.failed
        if not commit:
            self.stdout.write("Dry run: nothing was copied. Run again with --commit.")
        if totals.failed:
            raise CommandError(f"{len(totals.failed)} files failed verification.")
        self.stdout.write(self.style.SUCCESS("Done. The database was not changed."))

    def copy_tree(self, root, storage, prefix, commit):
        counts = Counts()
        for path, relative in local_files(root):
            counts.scanned += 1
            name = f"{prefix}{relative}"
            size = path.stat().st_size
            with path.open("rb") as handle:
                checksum = md5_of(handle)
            exists = storage.exists(name)
            if exists and storage.size(name) == size and remote_md5(storage, name) == checksum:
                counts.present += 1
                continue
            if not commit:
                counts.to_copy += 1
                continue
            if exists:
                # Same name, different bytes: the local file is the source of truth.
                storage.delete(name)
                counts.replaced += 1
            with path.open("rb") as handle:
                stored = storage.save(name, File(handle, name=name))
            if (
                stored != name
                or storage.size(name) != size
                or remote_md5(storage, name) != checksum
            ):
                counts.failed.append(name)
                continue
            counts.copied += 1
        return counts
