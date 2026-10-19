# rose

Website for a volunteer-run, members-only adult community nonprofit: a Django REST API with
Celery in `/backend`, a React single-page app in `/frontend`, and project docs in `/docs`.

Privacy is the core requirement. Read [docs/architecture.md](docs/architecture.md) before
changing anything, especially the privacy checklist and the RSVP privacy rules.

## Requirements

- Docker, for the full stack (option A) or just Postgres and Redis (option B)
- Python 3.12 and Node 22 or newer, for option B

## Option A: everything in Docker

1. **Start the stack.**

   ```sh
   docker compose up --build
   ```

   This runs Postgres, Redis, the API (migrations run on start), a Celery worker, Celery beat,
   the Vite dev server, Mailpit and MinIO. The site is at http://localhost:5173, the API and
   admin at http://localhost:8000, and every email the site sends at http://localhost:8025.

2. **Load demo content** in a second terminal.

   ```sh
   docker compose exec api python manage.py seed_demo
   ```

   This prints demo logins (one verified, one not, and a member-feed account); passwords
   change on every run. The verified account has feed access but has not joined, so you can
   try the join flow from `/account`.

3. **Create an admin account.**

   ```sh
   docker compose exec api python manage.py createsuperuser
   ```

   The admin asks you to set up an authenticator app at first login (two-step login is
   required for all staff, also locally).

4. **Run the backend tests.**

   ```sh
   docker compose exec api python -m pytest
   ```

If ports 5433, 6380, 8000 or 5173 are taken, override them, for example
`API_PORT=8010 WEB_PORT=5180 docker compose up --build`. `DB_PORT` and `CACHE_PORT` work the same way.

## Option B: run the app on your machine

1. **Start Postgres, Redis, Mailpit and MinIO.**

   ```sh
   docker compose up -d db cache mailpit minio
   ```

   Postgres listens on `localhost:5433`, Redis on `localhost:6380`, Mailpit on
   http://localhost:8025 and MinIO (used by the storage tests) on `localhost:9000`.

2. **Set up the backend.**

   ```sh
   cd backend
   python3.12 -m venv .venv
   .venv/bin/pip install -r requirements-dev.txt
   cp .env.example .env
   ```

   Open `backend/.env` and set `DJANGO_SECRET_KEY` to a long random string, for example the
   output of `.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(50))"`.

3. **Create the database tables, an admin account and demo content.**

   ```sh
   .venv/bin/python manage.py migrate
   .venv/bin/python manage.py createsuperuser
   .venv/bin/python manage.py seed_demo
   ```

4. **Run the API, the worker and beat**, each in its own terminal, from `backend/`.

   ```sh
   .venv/bin/python manage.py runserver 8000
   .venv/bin/celery -A config worker --loglevel=info --pool=threads
   .venv/bin/celery -A config beat --loglevel=info
   ```

   `--pool=threads` is needed on macOS; Linux can use the default pool. If you would rather
   not run a worker, set `CELERY_TASK_ALWAYS_EAGER=true` in `.env` and emails are sent inline.

5. **Run the frontend** in another terminal.

   ```sh
   cd frontend
   npm install
   cp .env.example .env.local
   npm run dev
   ```

   Open http://localhost:5173. Vite proxies `/api` and `/media` to the API on port 8000.

6. **Run the tests and checks.**

   ```sh
   cd backend
   .venv/bin/python -m pytest          # the storage tests need MinIO running (step 1)
   .venv/bin/ruff check . ../scripts
   .venv/bin/pip-audit -r requirements.txt

   cd ../frontend
   npm test
   npm run lint
   npm run build
   npm audit --omit=dev
   ```

## Browser tests

The end-to-end tests run against the production image with Postgres, Redis, MinIO and
Mailpit, in the Chrome already installed on your computer:

```sh
docker compose -f docker-compose.e2e.yml up -d --build --wait
cd e2e && npm ci && npx playwright test        # phone and desktop widths
docker compose -f docker-compose.e2e.yml down -v
```

The stack uses ports 8080 (site), 9100 (MinIO) and 8125 (Mailpit). CI runs the same suite
(`.github/workflows/checks.yml`).

## Deploying and operating

Production runs on Render from `render.yaml` (staging and production). Start with
[docs/ops/deploy.md](docs/ops/deploy.md); the rest of `docs/ops/` covers storage, email,
security, restores and what to do if data may have leaked. Volunteers get
[docs/staff-guide.md](docs/staff-guide.md), and [docs/launch-checklist.md](docs/launch-checklist.md)
lists what the club must supply before launch.

## Member feed

Members whose tier includes the feed, and anyone staff give access to from Admin > Accounts >
Profiles ("Grant member feed access"), can join it from `/account`. Moderators work from Admin > Feed > Feed posts > "Open queue"
(`/admin/feed/feedpost/moderation/`). Member uploads live in `backend/private_media/` locally
(the private bucket in production) and are only ever served through access-checked views;
never point a web server at that folder.

## Membership and payments

- **Joining**: `/join` (tier, agreement, then pay at the door or online). Staff work from
  Admin > "Door desk" on a tablet, and see counts, revenue and the logged CSV export under
  "Membership summary". How payments work, and how to add a real processor, is in
  [docs/payments.md](docs/payments.md).
- **Development payments**: with `DJANGO_DEBUG=True` the sandbox provider is on, so the
  online path works end to end with Pay, Fail and Cancel buttons and no money. The Celery
  worker must be running (or `CELERY_TASK_ALWAYS_EAGER=True`), because it delivers the
  sandbox webhooks. `SITE_URL` must be the address you open the site on, since the checkout
  redirects there.
- **Demo data**: `seed_demo` (DEBUG only) adds three placeholder tiers, a placeholder
  agreement, members in every status with payment history, two members-only classes and a
  `desk_volunteer` account with door desk permissions only. It prints their passwords.
- **Moving the clock** (DEBUG only): `python manage.py membership_clock --days 10
  [--member demo_active]` pretends days have passed and runs the daily lifecycle, so you can
  watch active become grace and then expired.
- **Importing existing members**: `python manage.py import_members members.csv` checks the
  file (columns `email,display_name,tier_slug,period_end,id_checked`) and writes nothing.
  Add `--commit` to import. Any problem row stops the whole import. Each person gets a neutral
  "Your account is ready" email. Email addresses are only printed with DEBUG on.

## Adding images

Images are never hotlinked. To add one:

1. Add a line to [docs/image-sources.txt](docs/image-sources.txt). The file explains the format
   and lists the image names the site already looks for.
2. Run `backend/.venv/bin/python scripts/fetch_images.py` from the repository root.
3. Review what is hidden: `backend/.venv/bin/python backend/manage.py review_images`, then mark
   each image as no faces, consent confirmed, or keep hidden. Volunteers can see the same
   status, with thumbnails, at Admin > Image review.

New images are recorded as `faces_visible: true, consent_confirmed: false` unless you say
otherwise, and images in that state are never shown on the site.

## Layout

```
backend/    Django project "config", apps under backend/apps/, admin templates, Dockerfile
frontend/   Vite + React + TypeScript + Tailwind, Vitest tests
e2e/        Playwright browser tests (phone and desktop)
docs/       Architecture, decisions, design system, payments, staff guide, launch checklist;
            docs/ops/ for deploy, storage, email, security, restore and incidents
scripts/    fetch_images.py, decrypt_backup.py
Dockerfile  Production image (web, worker and beat)
render.yaml Render Blueprint: staging and production
```
