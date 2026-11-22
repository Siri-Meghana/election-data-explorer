# Election Data Explorer: Build, Push to GitHub, Deploy

Every command in Parts 1, 2 and 4 was run from a clean copy of this project (fresh virtualenv, no `.env`, no database) on Python 3.13 with Django 5.2. Parts 3, 5 and 6 depend on outside services (the FEC API, GitHub, Render); what was and wasn't verified is stated in each.

**Free accounts you need:** GitHub, Render (for deployment), and an FEC API key (Part 3).
**Software you need:** Python 3.11 or newer (3.13 was tested), and Git.

Check your versions first:

```bash
python3 --version      # Windows: python --version   -> want 3.11 or higher
git --version
```

Windows note: use `python` instead of `python3`, and the Windows variants shown below. In PowerShell, if activating the virtualenv says "running scripts is disabled", run `Set-ExecutionPolicy -Scope Process Bypass` once and retry.

---

## Part 1: Run it on your computer (about 10 minutes)

**1. Unzip the project and open a terminal inside the `election-data-explorer` folder.**

**2. Create and activate a virtual environment**

```bash
# Mac / Linux
python3 -m venv venv
source venv/bin/activate

# Windows (PowerShell)
python -m venv venv
venv\Scripts\Activate.ps1
```

Your prompt should now start with `(venv)`.

**3. Install the dependencies**

```bash
pip install -r requirements.txt
```

**4. Create your `.env` file**

```bash
# Mac / Linux
cp .env.example .env

# Windows
copy .env.example .env
```

The defaults work as they are (SQLite database, debug on). If you skip this step, Django stops with "SECRET_KEY is not set". That is intentional.

**5. Create the database tables**

```bash
python manage.py migrate
```

**6. Run the tests** (expect `Ran 26 tests ... OK`)

```bash
python manage.py test elections
```

A warning about a missing `staticfiles` directory is harmless locally.

**7. Load fictional sample data and start the server**

```bash
python manage.py load_sample_data
python manage.py runserver
```

Open http://127.0.0.1:8000/ and click through the Dashboard, the Candidates list, and a candidate's page.candidates/

The sample data is invented (names like `SAMPLE, CANDIDATE 07`). Remove it with `python manage.py load_sample_data --clear` before importing real data.

**8. (Optional) Create an admin login**

```bash
python manage.py createsuperuser
```

Then visit http://127.0.0.1:8000/admin/

---

## Part 2: Put it on GitHub (about 5 minutes)

**1. Create the empty repo.** On github.com click **New repository**. Name it `election-data-explorer`, set it to **Public**, and leave "Add a README", ".gitignore" and "license" **unchecked**, because the project already has them.

**2. Commit and push from your project folder**

```bash
git init -b main
git add .
git status
```

Look at the `git status` list before committing. You must **not** see `.env`, `venv/`, `db.sqlite3` or `staticfiles/`. They are listed in `.gitignore`, so you should see about 32 files. Then:

```bash
git commit -m "Initial commit: Django election data explorer"
git remote add origin https://github.com/Siri-Meghana/election-data-explorer.git
git push -u origin main
```

If Git says it doesn't know who you are, run `git config --global user.name "Your Name"` and `git config --global user.email "you@example.com"`, then repeat the commit.

**Authentication:** GitHub no longer accepts your account password for pushes. When prompted, either sign in through the browser window Git opens, or install the GitHub CLI and run `gh auth login` first, or use a Personal Access Token as the password.

**3. Check it.** Refresh the repo page. You should see the README, and **no** `.env` file. If you ever commit a secret by accident, change that secret immediately.

From here on, make small commits as you add features (for example "Add Dockerfile", "Add Celery import task"), and don't squash them. A real history is better than one big commit.

---

## Part 3: Load real FEC data (about 10 minutes)

**Note:** the import command is tested with mocked API responses and has been confirmed to work against the live FEC API. If the FEC is slow it retries automatically; if something else fails, the command prints the FEC's own error message.

**1. Get a free API key** at https://api.open.fec.gov/developers/ (sign-up form, no payment). Open `.env` and set `FEC_API_KEY=your-key`. Without it the shared `DEMO_KEY` works but is rate limited.

**2. Clear the sample data, then import candidates**

```bash
python manage.py load_sample_data --clear
python manage.py import_candidates --cycle 2024 --office S --max-pages 10
```

Reload http://127.0.0.1:8000/ and you should see real Senate candidates. More options: `--state VA`, `--office H`, `--max-pages 10`. Re-running updates existing rows instead of duplicating them.

**3. Import more cycles.** Repeat the import for each cycle you want. A candidate who ran in several cycles gets one row per cycle, so earlier imports are never overwritten:

```bash
for y in 2022 2020 2018; do python manage.py import_candidates --cycle $y --office S --max-pages 10; done
```

The number of candidates per cycle is higher than the number of Senate races, because it counts everyone who filed financial reports that cycle, including minor candidates.

---

## Part 4: Production-readiness check (already done, optional to repeat)

This runs the app the way a host will run it, locally:

```bash
# Mac / Linux
DEBUG=False SECRET_KEY=any-long-random-string bash build.sh
DEBUG=False SECRET_KEY=any-long-random-string gunicorn config.wsgi:application --bind 127.0.0.1:8002
```

Then open http://127.0.0.1:8002/. (Windows doesn't run gunicorn; skip this part, since Render runs Linux.)

---

## Part 5: Deploy on Render (about 15 minutes)

What I verified: `build.sh` and the gunicorn start command run correctly, HTTPS redirect and host checking behave correctly in a simulated Render environment, and the PostgreSQL connection string is parsed correctly. What I **could not** verify: Render's own dashboard and current free-tier terms. Render's screens and limits change, so follow the labels you actually see.

**1. Push to GitHub first** (Part 2).

**2. Create the database.** In Render: **New → PostgreSQL**. Give it a name, choose the **Free** plan if offered, create it, and wait until it shows **Available**. Copy two values from its page: the **Internal Database URL** and the **External Database URL**.

**3. Create the web service.** **New → Web Service**, connect your GitHub account, pick the `election-data-explorer` repo, then set:

| Field | Value |
|---|---|
| Language | Python 3 |
| Branch | `main` |
| Region | same region as the database |
| Build Command | `bash build.sh` |
| Start Command | `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT` |

**4. Add environment variables** (under Advanced / Environment):

| Key | Value |
|---|---|
| `SECRET_KEY` | click Generate, or paste any long random string |
| `DATABASE_URL` | the **Internal** Database URL from step 2 |
| `FEC_API_KEY` | your FEC key |

Do **not** set `DEBUG`. It defaults to off, which is what you want in production. Render sets the hostname variable the app needs by itself.

**5. Deploy.** Render runs `build.sh` (install, collect static files, create tables) and starts the app. Open the `*.onrender.com` URL when the logs say it's live. It will be empty, since the new database has no data yet.

**6. Put data and an admin user in the live database from your own computer.** Render's browser shell may not be available on the free plan, so use the **External** Database URL locally:

```bash
# Mac / Linux
export DATABASE_URL="paste-the-External-Database-URL-here"

# Windows PowerShell
$env:DATABASE_URL="paste-the-External-Database-URL-here"
```

With that variable set in the same terminal, run:

```bash
python manage.py migrate
python manage.py import_candidates --cycle 2024 --office S --max-pages 2
python manage.py createsuperuser
```

These now write to the live database. Reload your site to see the data. Close that terminal when you're done so the variable doesn't linger. Never commit the URL.

**Things to know about the free tier:** I couldn't confirm Render's current free-plan terms, and sources I found disagree. Free databases are time-limited (reported anywhere from 30 to 90 days) and free web services may sleep when idle, so the first page load after a pause can be slow. Check Render's pricing page, and for your resume or interviews be ready to re-create the database if it expires.

---

## Part 6: If something goes wrong

| Symptom | Fix |
|---|---|
| `SECRET_KEY is not set` | You skipped `.env`. Run the copy command in Part 1, step 4. |
| `python: command not found` | Use `python3` (Mac/Linux). On Windows use `python`; reinstall with "Add to PATH" ticked. |
| `No module named django` | The virtualenv isn't active. Re-run the activate command; the prompt must show `(venv)`. |
| `no such table` | Run `python manage.py migrate`. |
| Import says HTTP 429 | Rate limit. Use your own FEC key instead of `DEMO_KEY`, or wait and retry. |
| Import says HTTP 422 | The FEC rejected a parameter. Copy the full message to me. |
| Import says the FEC timed out (504) | The FEC's server is slow. The command already retried; wait a few minutes or use a smaller `--max-pages`. |
| Render: `DisallowedHost` / 400 | Add your site's hostname to an `ALLOWED_HOSTS` environment variable (comma separated). |
| Render build says a Python version is too old | Add environment variable `PYTHON_VERSION` set to a 3.12 or 3.13 release listed in Render's docs. |
| Render site shows no styles | Check the build log shows `collectstatic` ran; Build Command must be `bash build.sh`. |
| Render: tables missing | `migrate` runs in `build.sh`; check the build log for errors. |

---

## What to claim on your resume

Only list what the finished, deployed project actually uses: **Django, PostgreSQL, integration with a third-party REST API (the FEC API) with pagination, retries and tests, gunicorn/WhiteNoise, deployed on Render.** It does **not** include a REST API of its own, Vue.js, Docker, Celery or Azure. Add those to the resume only after you build them.
