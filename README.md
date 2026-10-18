# rose

Website for a volunteer-run, members-only adult community nonprofit. Django REST API in
`/backend`, React single-page app in `/frontend`, project docs in `/docs`.

Privacy is the core requirement. Read [docs/architecture.md](docs/architecture.md) before
changing anything, especially the privacy checklist.

## Requirements

- Python 3.12
- Node 22 or newer
- Docker (for local Postgres and Redis)

## Local setup

1. **Start Postgres and Redis.**

   ```sh
   docker compose up -d
   ```

   Postgres listens on `localhost:5433` and Redis on `localhost:6380`. These ports avoid
   clashing with copies you may already run locally.

2. **Set up the backend.**

   ```sh
   cd backend
   python3.12 -m venv .venv
   .venv/bin/pip install -r requirements-dev.txt
   cp .env.example .env
   ```

   Open `backend/.env` and set `DJANGO_SECRET_KEY` to a long random string, for example the
   output of `.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(50))"`.

3. **Create the database tables and an admin account.**

   ```sh
   .venv/bin/python manage.py migrate
   .venv/bin/python manage.py createsuperuser
   ```

   You will be asked for an email address, a display name and a password (12 characters or more).

4. **Load the demo content.**

   ```sh
   .venv/bin/python manage.py seed_demo
   ```

   This loads site settings, 6 education opportunities and 8 FAQs. You can run it again
   safely; it updates the same rows.

5. **Run the API.**

   ```sh
   .venv/bin/python manage.py runserver 8000
   ```

   The admin is at http://localhost:8000/admin/ (move it with `DJANGO_ADMIN_PATH` in production).
   Emails are printed to this terminal.

6. **Set up and run the frontend** in a second terminal.

   ```sh
   cd frontend
   npm install
   cp .env.example .env.local
   npm run dev
   ```

   Open http://localhost:5173. Vite proxies `/api` and `/media` to the API on port 8000.

7. **Run the tests and checks.**

   ```sh
   cd backend
   .venv/bin/python -m pytest
   .venv/bin/ruff check . ../scripts

   cd ../frontend
   npm run lint
   npm run build
   ```

## Adding images

Images are never hotlinked. To add one:

1. Add a line to [docs/image-sources.txt](docs/image-sources.txt). The file explains the format
   and lists the image names the site already looks for.
2. Run `backend/.venv/bin/python scripts/fetch_images.py` from the repository root.
3. Open [docs/image-manifest.json](docs/image-manifest.json), check each new entry, and set
   `faces_visible` and `consent_confirmed` correctly.

New images are recorded as `faces_visible: true, consent_confirmed: false` unless you say
otherwise. Images in that state are never shown on the site, so nothing appears until someone
has looked at it.

## Layout

```
backend/    Django project "config" and apps under backend/apps/
frontend/   Vite + React + TypeScript + Tailwind
docs/       Architecture, decisions, design system, image manifest
scripts/    fetch_images.py
render.yaml Hosting blueprint stub (not deployed)
```
