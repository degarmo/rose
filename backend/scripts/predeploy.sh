#!/usr/bin/env bash
# Render's pre-deploy step for staging and production (render.yaml, render.production.yaml).
# It runs in the new image before traffic moves to it: the safety checks first, so a bad
# configuration stops the deploy, then the migrations.
set -euo pipefail
python manage.py check --deploy --database default --fail-level ERROR
python manage.py migrate --noinput
