# Object storage

Uploaded media lives in two S3-compatible buckets. The settings are generic
(`S3_*`), so Cloudflare R2, Backblaze B2, AWS S3 and MinIO all work. **R2 is the
default** in these instructions: it has no egress fees and its public buckets
sit behind Cloudflare's CDN.

| Bucket | Holds | Access |
| --- | --- | --- |
| public (`S3_PUBLIC_BUCKET`) | Site images (`site/`), journal, education and event images, and their 640/1280 px copies | Public read through a custom domain or the bucket's public URL; long browser cache |
| private (`S3_PRIVATE_BUCKET`) | Member feed images, avatars, watermarked copies (`watermarks/`), data exports (`exports/`), encrypted backups (`backups/`) | No public access, no listing. The app hands out 60-second signed links after its own checks |

## How files are served

- **Public**: the API returns `S3_PUBLIC_BASE_URL/<name>`. Uploaded names are
  random, so objects are cached for a year (`Cache-Control: public,
  max-age=31536000, immutable`). Site imagery keeps fixed names and is cached for
  a week.
- **Private**: every request goes to an access-checked view first
  (`/api/members/media/...`, `/api/members/avatars/...`). It re-checks access,
  blocks and post status, then answers `302` to a URL signed for 60 seconds
  (`S3_SIGNED_URL_SECONDS`). The view's own response is `Cache-Control:
  private, no-store`, and the signed URL makes the bucket answer `no-store` too.
- **Watermarks**: each viewer's copy is rendered once and stored under
  `watermarks/<image>/<viewer>-<label>.webp` (all parts are keyed hashes, so the
  names reveal nothing). Deleting an image deletes every copy made from it;
  deleting an account deletes every copy carrying that person's name.

## Settings

| Variable | R2 value |
| --- | --- |
| `STORAGE_BACKEND` | `s3` |
| `S3_ENDPOINT_URL` | `https://<account-id>.r2.cloudflarestorage.com` |
| `S3_REGION` | `auto` |
| `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | An R2 API token with Object Read & Write on **these two buckets only** |
| `S3_PUBLIC_BUCKET` | for example `site-media` |
| `S3_PRIVATE_BUCKET` | for example `site-private` (must differ from the public one) |
| `S3_PUBLIC_BASE_URL` | `https://media.<your-domain>` (the public bucket's custom domain) |
| `S3_ADDRESSING_STYLE` | leave unset (`virtual`); MinIO uses `path` |
| `S3_SIGNED_URL_SECONDS` | leave at `60` |

The production safety checks refuse to start if any of these is missing, if the
two buckets are the same, or if an endpoint is plain `http` or a local emulator.

## Creating the buckets on R2

1. Cloudflare dashboard > R2 > Create bucket: the public bucket, location
   automatic. Repeat for the private bucket.
2. Public bucket > Settings > Custom Domains > Connect `media.<your-domain>`.
   Leave "R2.dev subdomain" **disabled** (it is rate limited and not for
   production). Do not enable public access on the private bucket at all.
3. R2 > Manage API tokens > Create token: permission "Object Read & Write",
   restricted to the two buckets. Copy the access key id and secret into Render.
4. Set CORS on **both** buckets (below), then the lifecycle rules (below).

### CORS (both buckets)

Only the site may read, and only with GET:

```json
[
  {
    "AllowedOrigins": ["https://<your-domain>"],
    "AllowedMethods": ["GET"],
    "AllowedHeaders": [],
    "MaxAgeSeconds": 3600
  }
]
```

On R2: bucket > Settings > CORS Policy > paste. With the AWS CLI against any
provider: `aws s3api put-bucket-cors --bucket <name> --cors-configuration file://cors.json --endpoint-url $S3_ENDPOINT_URL`.

### Lifecycle rules (private bucket)

| Prefix | Delete after | Why |
| --- | --- | --- |
| `watermarks/` | 7 days | Per-viewer copies are re-made on demand; they carry a viewer's name |
| `exports/` | 2 days | Export links expire after 24 hours |
| `backups/` | 30 days | Nightly encrypted backups (`BACKUP_RETENTION_DAYS`) |

On R2: private bucket > Settings > Object lifecycle rules > Add rule, once per
prefix, "Delete objects" after N days. The app also prunes all three itself
(`purge_old_watermarks`, `purge_expired_exports`, the backup task), so a
missing rule never means data is kept forever, but the rules are the first line.

## Moving existing files

`python manage.py migrate_media_to_storage` copies local media into the buckets
under the same names (so no database row changes), verifies each copy by size
and MD5, skips files already present, and reports counts. It is a dry run unless
`--commit` is given, and can be run again safely. Run it from a one-off shell
with the production environment (docs/ops/deploy.md, step 14).

## Development and tests

`docker compose up -d minio` starts MinIO on `localhost:9000` (user
`minio-local`, password `minio-local-secret`) with `rose-public` (download
policy) and `rose-private` buckets. Local development keeps `STORAGE_BACKEND=local`
unless you want to try S3. The S3 tests (`tests/test_storage_s3.py`) create
their own buckets in MinIO and remove them afterwards; they are skipped if
MinIO is not running, except in CI, where `REQUIRE_S3_TESTS=1` makes that a
failure. The official MinIO images are no longer published, so the archived
`bitnamilegacy/minio` image is used for development and tests only.
