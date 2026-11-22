#!/usr/bin/env bash
# Build script for Render (run with: bash build.sh)
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
