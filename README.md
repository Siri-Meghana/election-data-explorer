# Election Data Explorer

A Django web app that imports U.S. federal campaign finance data from the [FEC API](https://api.open.fec.gov/developers/) and lets you explore how much Senate candidates raised and spent in each election cycle.

## Features

- **Dashboard**: totals raised and spent per cycle, fundraising by party, breakdown by office, top fundraisers
- **Candidate explorer**: search by name; filter by party, office, state and cycle; sortable by money raised, spent or cash on hand
- **Candidate detail**: finances, burn rate, and a table of the candidate's fundraising across election cycles
- **Import command** for the FEC API: paginated, retries when the FEC is slow, safe to re-run, and keeps one row per candidate per cycle
- **Offline demo data** (`load_sample_data`, clearly fictional), Django admin, automated tests
- Deployable to Render with PostgreSQL (`build.sh`, gunicorn, WhiteNoise, `DATABASE_URL`)

## Tech stack

Python, Django 5.2, PostgreSQL (SQLite for local development), gunicorn, WhiteNoise, Requests

## Quick start

```bash
python -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                               # Windows: copy .env.example .env
python manage.py migrate
python manage.py load_sample_data                  # fictional demo data
python manage.py runserver
```

Open http://127.0.0.1:8000/. For the full walkthrough (real FEC data, GitHub, Render deployment, troubleshooting) see **[SETUP_GUIDE.md](SETUP_GUIDE.md)**.

## Real data

Get a free key at https://api.open.fec.gov/developers/ and set `FEC_API_KEY` in `.env`, then:

```bash
python manage.py load_sample_data --clear
python manage.py import_candidates --cycle 2024 --office S --max-pages 10
```

Repeat with `--cycle 2022`, `2020` and so on. Use `--office H` for House candidates.

## Configuration

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Required (see `.env.example`) |
| `DEBUG` | `True` locally; leave unset in production |
| `DATABASE_URL` | PostgreSQL URL; SQLite is used when unset |
| `FEC_API_KEY` | FEC API key |
| `ALLOWED_HOSTS` | Extra comma-separated hostnames |

## Tests

```bash
python manage.py test elections
```

The FEC API is mocked in the tests, so they run offline.

## Roadmap

- Individual contributions (donors) per candidate
- REST API
- Docker and docker-compose with PostgreSQL
- Scheduled daily imports
