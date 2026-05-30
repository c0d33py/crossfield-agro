#!/usr/bin/env bash
# Render build step: install deps, collect static, run migrations.
# Referenced by render.yaml (buildCommand). Runs on every deploy.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Hash + compress static assets into STATIC_ROOT for WhiteNoise to serve.
python manage.py collectstatic --noinput

# Apply DB migrations. Safe to run on every deploy (no-op when up to date).
python manage.py migrate --noinput
