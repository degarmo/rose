# Security

How the deployed site is protected, and the settings behind each part. Privacy
rules live in [architecture.md](../architecture.md#privacy-checklist); this page
covers the operational side.

## Environments and startup checks

`DJANGO_ENV` is `development` (default), `test`, `e2e`, `staging` or
`production`. Staging and production refuse to start, in the web process, the
worker and beat alike, if any of these is true (`apps/core/checks.py`, tested
in `tests/test_deploy_checks.py`):

| Check | Condition |
| --- | --- |
| `rose.E001` | `DJANGO_DEBUG` is on |
| `rose.E002` | the sandbox payment provider is enabled (staging: anything but `manual`) |
| `rose.E003` | `DJANGO_SECRET_KEY` is shorter than 50 characters, low-variety or a known default |
| `rose.E004` | `DJANGO_ALLOWED_HOSTS` is empty or `*` |
| `rose.E005` | `DJANGO_CSRF_TRUSTED_ORIGINS` is empty or not all `https://` |
| `rose.E006` | media is not on S3, a bucket or credential is missing, the buckets are the same, or an endpoint is `http` or a local emulator (MinIO) |
| `rose.E007` | email goes to the console, memory, a file or nowhere |
| `rose.E008` | the admin is at the default `/admin/` |
| `rose.E009` | HTTPS redirect, secure cookies, a one-year HSTS, nosniff or the proxy HTTPS header is off |
| `rose.E010` | the database contains demo seed data (`seed_demo` writes a marker) |
| `rose.E011` | staging has no basic-auth credentials |

The same checks run in Render's pre-deploy step (`manage.py check --deploy
--database default`), so a bad configuration stops a deploy before migrations.
`seed_demo`, `membership_clock` and the sandbox refuse to run in staging and
production, and `e2e_fixtures` refuses to run anywhere but `DJANGO_ENV=e2e`.

## Staging

Every path except `/healthz` and payment webhooks needs HTTP basic auth
(`STAGING_BASIC_AUTH_USER`, `STAGING_BASIC_AUTH_PASSWORD`), every response
carries `X-Robots-Tag: noindex, nofollow, noarchive`, `robots.txt` disallows
everything, and payments are in person only.

## Staff two-factor

Every admin view, including the door desk, needs a staff account **and** a
second step in the same session (`apps/core/admin_auth.py`):

1. Email and password. Rate limited per IP, and five failures lock the email out
   for 15 minutes (shared with member login).
2. A six-digit code from an authenticator app (TOTP), or one of ten single-use
   backup codes. Wrong codes count toward the same lockout.

A staff member without an authenticator is taken through enrolment on their
first login: scan a QR code (made on the server, shown once), enter a code,
receive ten backup codes (shown once). There is no way to skip it. The
authenticator app shows the issuer (`OTP_ISSUER`, default "Rose") and the
display name, never the email. Enrolment and backup-code use are written to the
audit log. To reset a lost device, a superuser deletes that person's TOTP device
in Admin > Django OTP > TOTP devices; they enrol again at next login.

## Sessions

| Who | Rule |
| --- | --- |
| Members | Idle sessions end after `MEMBER_SESSION_DAYS` (14); every request extends the session |
| Staff | Sessions end when the browser closes and at most `STAFF_SESSION_HOURS` (12) after the two-step login |
| Everyone | The session key changes at login and at the second step. Changing someone's staff, superuser or active status, groups or permissions ends all their sessions |
| Members | "Sign out everywhere" on `/account` ends every session on every device, including the current one |

Sessions are ended through a per-account `session_epoch` mixed into the session
hash, so nothing has to search the session table.

## Headers

Asserted on a public page, a member page, an admin page and the media view in
`tests/test_headers.py` and on every route in the browser tests.

| Header | Value |
| --- | --- |
| `Content-Security-Policy` | `default-src 'self'`; `script-src 'self'` (no inline scripts, no `unsafe-inline` or `unsafe-eval`); `style-src 'self'`; `img-src 'self' data: blob:` plus the public bucket and the private bucket's signing host; `font-src 'self'`; `connect-src 'self'`; `object-src 'none'`; `base-uri 'self'`; `form-action 'self'`; `frame-ancestors 'none'`; `worker-src 'none'` |
| `Permissions-Policy` | Every device feature denied (`camera=()`, `microphone=()`, `geolocation=()`, `payment=()`, `usb=()`, `browsing-topics=()` and more). Only the door desk page has `camera=(self)`, for scanning codes |
| `Referrer-Policy` | `no-referrer`. The admin alone uses `same-origin`, because Django's admin forms post with an `Origin` header that `no-referrer` would turn into `null` (decision 174) |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Cross-Origin-Opener-Policy` | `same-origin` |
| `Cross-Origin-Resource-Policy` | `same-origin` |
| `Strict-Transport-Security` | one year, include subdomains, preload (staging and production) |
| `X-Robots-Tag` | `noindex, nofollow` on `/members`, `/account`, `/api`, `/media`, `/join/confirming`, `/dev` and the admin |

No response names the Django version; gunicorn's `Server` header says only
"gunicorn".

## Uploads

Every image upload (feed posts, avatars, admin images) is checked before it is
stored (`apps/core/images.py`): at most 15 MB, real format by magic bytes (JPEG,
PNG, WebP or HEIC, whatever the name or content type says), at most 40
megapixels and 12,000 px on a side, read from the header before any pixel is
decoded. Pillow's `MAX_IMAGE_PIXELS` is the same 40 megapixels, and its
decompression-bomb warning is treated as a refusal. Accepted images are
re-encoded to WebP with all metadata stripped and a random name.
`tests/test_uploads.py` uses a crafted 50,000 × 50,000 PNG header in a
200-byte file.

## Rate limits

Every key is a salted hash of the IP address, email or account; no raw address
reaches the cache. Over-limit requests get HTTP 429.

| Endpoint | Limit |
| --- | --- |
| Member login (`/api/account/login/`) | 20/hour per IP, 10/hour per email; 5 failures lock the email for 15 minutes |
| Admin login (password and code steps) | 20/hour per IP; shares the per-email lockout; wrong codes count |
| Registration | 5/hour per IP, 3/hour per email |
| Password reset request | 5/hour per IP, 3/hour per email |
| Resend verification email | 3/hour per account |
| Contact form | 5/hour per IP (invalid submissions count) |
| Join (membership) | 10/hour per account |
| Payment webhooks | 120/minute per IP |
| Display name change, password change, delete account, sign out everywhere, RSVP (create, update, cancel), feed export and erase requests, membership checkout, cancel and auto-renew | 30/hour per endpoint per account |
| Token links: verify email, reset password, cancel RSVP by link, export download | 30/hour per endpoint per IP |
| Feed posts | 10/day per member (`FEED_MAX_POSTS_PER_DAY`), plus the default below |
| Feed comments | 60/hour per member (`FEED_MAX_COMMENTS_PER_HOUR`), plus the default below |
| Every other write (likes, follows, blocks, mutes, reports, notifications, feed profile, avatar, joining the feed, logout, sandbox) | 120/hour per endpoint per account, or per IP when signed out |

Reads are not rate limited; the member directory returns at most 20 results.

## Optional breached-password check

`PASSWORD_BREACH_CHECK=true` checks new passwords against the Have I Been Pwned
range API. Only the first five characters of the password's SHA-1 hash leave the
server; the reply lists every hash suffix with that prefix (padded, so its size
says nothing either), and the comparison happens here.

**Trade-off**: it is an outbound call to a third party on every new password,
which this site otherwise never makes, and it reveals to that service (and the
network) that someone on this server is choosing a password at that moment. If
the service is down, the password is accepted and only that fact is logged. It
is **off by default**; the 12-character minimum and the common-password list
apply either way.

## Logs and error tracking

Logs are JSON lines on stdout. Every record, including gunicorn's access log,
passes through a scrubber (`apps/core/logging.py`, tested in
`tests/test_logging.py`) that removes email addresses, display names of the
requesting member, typed signature names, reference codes, IP addresses, session
ids, cookies, authorisation headers, and query strings and member handles on
account, feed, membership and payment paths. Request bodies are never logged.
The access log has no client address, query string or user agent. Django's
error emails are off (`ADMINS = []`).

Third-party error tracking is **off**, and leaving `SENTRY_DSN` unset is the
recommended default. If it is set, Sentry starts with `send_default_pii=False`,
request bodies off, local variables off, no performance tracing, and the same
scrubber as `before_send` and `before_breadcrumb`.

## Dependencies

`pip-audit -r backend/requirements.txt` and `npm audit` (site with
`--omit=dev`, and the browser-test tools) run in CI and must report no high or
critical issues. At the time of writing all three report none, with no
exceptions. Two choices were made to get there: `cryptography` is pinned at
50.0.2 (an older version came in through a transitive dependency), and
`django-anymail` is installed without its `amazon-ses` extra, which pulled in a
package that capped `cryptography` below the fixed version (SES still works:
it needs only `boto3`, which is installed). Dependabot opens grouped weekly
updates for pip, npm and GitHub Actions (`.github/dependabot.yml`).
