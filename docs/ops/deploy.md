# Deploying

The site runs on Render from `render.yaml`: one Docker image (`Dockerfile`) as
a web service, a Celery worker and one Celery beat, with Render Postgres and
Render Key Value, in two environments, **staging** and **production**. Every
step below is done by a person; nothing here deploys automatically, and the
Blueprint creates paid resources.

## First-time setup

### Accounts and tools

1. Push this repository to a **private** GitHub repository. Check that
   `/prompts` is not in it (it is in `.gitignore`).
2. Create or choose: a Render account (with a payment method), a Cloudflare
   account for R2, an email provider account (Postmark is the default), and
   access to the DNS for your domain.
3. On your own computer, install `age` (or `pip install pyrage`) and the AWS CLI
   (only needed for CORS and restores).

### Secrets you generate yourself

4. **Django secret key**, one per environment:
   `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
5. **Admin path**, one per environment, for example
   `staff-` plus `python -c "import secrets; print(secrets.token_hex(4))"` and a
   trailing slash (`staff-8f3a91c2/`). Keep it private; it is not a secret in
   the cryptographic sense, but publishing it invites password guessing.
6. **Backup key pair** (once): `age-keygen -o age-key.txt`. The line starting
   `# public key: age1...` is `BACKUP_AGE_RECIPIENT`. Store `age-key.txt`
   offline in two places held by two named people (a password manager vault and
   a printed copy in a safe). **It never goes on the server.** Without it the
   nightly backups cannot be read.
7. **Staging basic-auth** user name and a long random password.

### Storage

8. Create the buckets, custom domain, API token, CORS and lifecycle rules as in
   [storage.md](storage.md), once for staging and once for production
   (four buckets in total; staging and production never share a bucket).

### Email

9. Set up the sending subdomain, sender and DNS records as in
   [email.md](email.md), create a "server" in Postmark per environment, and copy
   each server token.

### The Blueprint

10. Render dashboard > New > Blueprint > connect the GitHub repository > pick
    `render.yaml`. Render shows the project `rose` with its two environments.
    Create **staging first**; leave production for after the staging checks
    (step 18).
11. Render asks for every value marked `sync: false`. Enter them from this table
    (they go into the environment's `rose-<env>-secrets` group, which the web,
    worker and beat services all read):

| Name | Where it comes from |
| --- | --- |
| `DJANGO_SECRET_KEY` | Step 4 |
| `DJANGO_ALLOWED_HOSTS` | Your domain, comma-separated with the Render host name, for example `<domain>,www.<domain>,rose-production-web.onrender.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://<domain>,https://www.<domain>` (staging: its own domain) |
| `DJANGO_ADMIN_PATH` | Step 5 |
| `SITE_URL` | `https://<domain>` (used in email links) |
| `STAGING_BASIC_AUTH_USER`, `STAGING_BASIC_AUTH_PASSWORD` | Step 7 (staging only) |
| `S3_ENDPOINT_URL` | Cloudflare R2 > Overview: `https://<account-id>.r2.cloudflarestorage.com` |
| `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | The R2 API token from storage.md |
| `S3_PUBLIC_BUCKET`, `S3_PRIVATE_BUCKET` | The bucket names from step 8 |
| `S3_PUBLIC_BASE_URL` | `https://media.<domain>` (the public bucket's custom domain) |
| `POSTMARK_SERVER_TOKEN` | Postmark > Servers > the server > API Tokens |
| `EMAIL_SENDER_ADDRESS` | The neutral sender from email.md, for example `hello@mail.<domain>` |
| `CONTACT_NOTIFY_EMAIL` | A private staff inbox for "new message" notices |
| `BACKUP_AGE_RECIPIENT` | The public key from step 6 |

12. Apply. Render builds the image, runs the pre-deploy step (the safety checks,
    then migrations) and starts the services. If a safety check fails, the
    deploy log names it (`rose.E0xx`, see [security.md](security.md)); fix the
    value and redeploy.

### Domain and TLS

13. Render > the web service > Settings > Custom Domains > add `<domain>` and
    `www.<domain>` (staging: `staging.<domain>`). At your DNS host add the
    records Render shows (a CNAME to `<service>.onrender.com`, or for the bare
    domain the A/ALIAS record it lists). Render issues TLS certificates by
    itself once DNS resolves; wait for "Certificate issued". HTTPS is enforced by
    the app (HSTS for a year, so get the domain right before going live).

### Content and people

14. **Site images and existing uploads**: on the computer that holds them (after
    `scripts/fetch_images.py` and `review_images`), run with the environment's
    storage settings exported:
    `python manage.py migrate_media_to_storage` (dry run, read the counts), then
    `python manage.py migrate_media_to_storage --commit`. It is safe to repeat.
15. **First superuser**: Render > web service > Shell:
    `python manage.py make_owner <email>` (a superuser with the Admin role; it asks
    for a password and prints the next steps). Then log in on the site, and enrol the
    authenticator app when the staff section asks. Save the ten backup
    codes in a password manager. Create the other staff accounts in the admin
    (staff status, plus a "Door desk" group for door volunteers with only the
    membership view and change permissions); each enrols at first login.
16. **Existing members** (optional): in the web service shell, create the CSV
    (`cat > /tmp/members.csv`, paste, Ctrl-D), run
    `python manage.py import_members /tmp/members.csv` (dry run), read the
    output, then add `--commit`. Delete the file: `rm /tmp/members.csv`.
17. **Test email**: `python manage.py send_test_email <you> --staff <your staff email>`.

### Staging checks, then production

18. Against staging, run the browser smoke tests from your computer:
    `cd e2e && npm ci && E2E_SMOKE=1 E2E_BASE_URL=https://staging.<domain> E2E_BASIC_AUTH='<user>:<password>' E2E_ALLOWED_HOSTS=staging.<domain>,media-staging.<domain> npx playwright test --grep @smoke --grep-invert Accounts`
    (the accounts flow needs the local mail catcher, so it is left out here;
    try a real registration by hand instead). Work through
    [launch-checklist.md](../launch-checklist.md).
19. Repeat steps 10 to 17 for **production**. Do not run `seed_demo` anywhere
    deployed; it refuses, and a seeded database would stop the site starting.

## Routine deploys

1. Merge to the default branch only when the `checks` workflow is green.
2. Render deploys the services that use the image when the branch updates
   (auto-deploy), or press "Manual Deploy". Deploy **staging first**, check it,
   then production.
3. The pre-deploy step runs the safety checks and migrations before any traffic
   moves. Watch the deploy log; `/healthz` must answer `ok` before Render
   switches over.
4. After a deploy, open the site, sign in, and check the admin and the door desk
   load.

## Rolling back

- **Code only** (no migration in the bad release): Render > the service >
  Events > pick the previous successful deploy > "Rollback". Do it for web,
  worker and beat.
- **With a migration**: if the migration only added things, rolling back the
  code is enough (the old code ignores new columns). If it changed or removed
  data, restore the database from just before the deploy
  ([restore.md](restore.md), source A) into a new database, then roll back the
  code and point `DATABASE_URL` at the restored database.
- Keep `FEED_ENABLED=false` in mind as a fast switch if the problem is in the
  member feed ([incident.md](incident.md)).
