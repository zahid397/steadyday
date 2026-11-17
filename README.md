# SteadyDay

SteadyDay is an English and Bangla wellbeing prototype for men in Bangladesh. A fictional profile can log sleep, movement, mood, energy, stress, and hydration, review trends, manage weekly goals and habits, and receive suggestions based on saved check-ins. The demo uses fictional values and expires after seven days by default.

## Run with Docker

Start Docker Desktop in Linux-container mode. Clone the private repository with authorized GitHub credentials or extract the source archive. Open PowerShell in the `SteadyDay` folder next to `compose.yaml`.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-env.ps1
docker compose config --quiet
docker compose up -d --build --wait
```

See the [Windows installation and user guide](docs/INSTALLATION.md) for manual `.env` setup, the native Python and Next.js options, and troubleshooting.

Open [SteadyDay on port 8000](http://127.0.0.1:8000/) and choose **Try the fictional demo → Samir → confirm fictional use → Start demo**. The first build needs internet access to download the base images and Python packages. Docker supplies Python and PostgreSQL.

Compose starts PostgreSQL and waits for it to accept connections. The FastAPI container then creates the tables and serves the website and API at the same address. The app's port is bound to your computer's loopback interface. The database has no published port, and check-ins persist in the `steadyday_data` volume. The `.env` contains a generated password for this local database. It is excluded from Git and the Docker build context.

### Check and stop the app

```sh
docker compose ps
docker compose exec -T app python scripts/smoke.py
docker compose down
```

The smoke test makes and cleans up one fictional session. It checks readiness, UI assets, check-ins, goals, habits, reminders, export, and deletion. `docker compose down` stops the stack and keeps the database volume.

If port 8000 is busy, change `APP_PORT` in `.env` and open the new port in your browser. Use `docker compose logs app db` if a service fails to become healthy. Keep the generated database password while using the same volume: editing `.env` does not change the password of a database that already exists. See [deployment](docs/DEPLOYMENT.md) for settings and [verification](docs/VERIFICATION.md) for the checks run in this workspace.

## Run without Docker

The verified Python fallback uses a local SQLite file. In the project folder on macOS or Linux, with Python 3.11 or newer:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r server/requirements.txt
sh scripts/run-local.sh
```

On Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r server/requirements.txt
$env:PYTHONPATH = "server"
.\.venv\Scripts\python.exe -m uvicorn steadyday.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Open `http://127.0.0.1:8000/`. The API explorer is at `/docs` and readiness is at `/healthz`. The Python fallback writes `steadyday.sqlite3` and does not load the Compose `.env`.

## Development and submission

- [Architecture](docs/ARCHITECTURE.md), [API](docs/API_DOCUMENTATION.md), and [database schema](docs/DATABASE_SCHEMA.md) describe how the app runs. [Deployment](docs/DEPLOYMENT.md) covers the Render and Vercel settings.
- [Interaction checklist](docs/FUNCTIONALITY_CHECKLIST.md) maps UI controls to their handlers and tests.
- [Responsible AI and privacy](docs/RESPONSIBLE_AI_AND_PRIVACY.md) explains the ranking, safeguards and data controls.
- [Security](docs/SECURITY.md) describes the trust boundaries and what a hosted fictional demo requires.
- [Test report](docs/TEST_REPORT.md) lists what passed and what is still unverified.
- [Concept](docs/CONCEPT.md), [AMA questions](docs/AMA.md), [demo script](docs/DEMO_SCRIPT.md) and [submission checklist](docs/SUBMISSION_CHECKLIST.md) are included. The original source archive also contains pitch and walkthrough media in `submission/`.

For the Python API and Node proxy checks:

```sh
python -m pip install -r server/requirements-test.txt
PYTHONPATH=server python -m unittest discover -s tests -p 'test_*api.py' -v
python tests/run_proxy_tests.py
```

The proxy harness needs Node.js 22.18 or newer. To run the separate browser regression suite, install Chromium with `python -m playwright install chromium` and run `python -m unittest discover -s tests -p 'test_browser.py' -v`.
