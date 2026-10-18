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

   This runs Postgres, Redis, the API (migrations run on start), a Celery worker, Celery beat
   and the Vite dev server. The site is at http://localhost:5173 and the API and admin are at
   http://localhost:8000. Emails are printed in the `worker` and `api` logs.

2. **Load demo content** in a second terminal.

   ```sh
   docker compose exec api python manage.py seed_demo
   ```

   This prints two demo logins (one verified, one not); passwords change on every run.

3. **Create an admin account.**

   ```sh
   docker compose exec api python manage.py createsuperuser
   ```

4. **Run the backend tests.**

   ```sh
   docker compose exec api python -m pytest
   ```

Ports 8000 and 5173 must be free. Stop any copy of the app you run outside Docker first.

## Option B: run the app on your machine

1. **Start Postgres and Redis.**

   ```sh
   docker compose up -d db cache
   ```

   Postgres listens on `localhost:5433` and Redis on `localhost:6380`.

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
   .venv/bin/python -m pytest
   .venv/bin/ruff check . ../scripts

   cd ../frontend
   npm test
   npm run lint
   npm run build
   ```

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
docs/       Architecture, decisions, design system, image manifest
scripts/    fetch_images.py
render.yaml Hosting blueprint stub (not deployed)
```
