# Production image for the web service, the Celery worker and beat (render.yaml).
# Django serves the built React app itself, so one image holds everything.

FROM node:22.23.1-bookworm-slim AS frontend
WORKDIR /srv/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
COPY docs/image-manifest.json /srv/docs/image-manifest.json
RUN npm run build


FROM python:3.12.13-slim-bookworm AS app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FRONTEND_DIST=/srv/frontend/dist

# PostgreSQL 16 client, matching the database, for the nightly encrypted backup.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
        https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-16 \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 app
WORKDIR /srv/backend

COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY --chown=app:app backend/ ./
COPY --from=frontend --chown=app:app /srv/frontend/dist /srv/frontend/dist
COPY docs/image-manifest.json /srv/docs/image-manifest.json
# Pre-compressed copies (gzip and Brotli) that WhiteNoise serves to browsers that accept them.
RUN python -m whitenoise.compress /srv/frontend/dist

# Static files are collected at build time; no database or secret is involved.
RUN DJANGO_SECRET_KEY=build-only DATABASE_URL=sqlite:////tmp/build.sqlite3 \
    IMAGE_MANIFEST_PATH=/srv/docs/image-manifest.json \
    python manage.py collectstatic --noinput

USER app
ENV IMAGE_MANIFEST_PATH=/srv/docs/image-manifest.json
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--config", "gunicorn.conf.py"]
