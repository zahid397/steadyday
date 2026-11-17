# Install SteadyDay on Windows 11

Use PowerShell in the `SteadyDay` folder containing `compose.yaml`. The Docker setup runs the website, FastAPI and PostgreSQL. The native setup runs the same website and FastAPI with SQLite.

## Docker Desktop and PostgreSQL

1. Install and start [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/). Wait for the Linux engine to start.
2. From the project folder, run the following commands. The setup script creates `.env` with a generated password on a fresh copy and keeps an existing file intact.

   ```powershell
   docker compose version
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-env.ps1
   docker compose config --quiet
   docker compose up -d --build --wait
   docker compose ps
   docker compose exec -T app python scripts/smoke.py
   ```

3. Open [SteadyDay](http://127.0.0.1:8000/) and choose **Try the fictional demo**. Choose Samir to see the return-after-a-gap example. Confirm fictional use, then choose **Start demo**.

Docker Desktop supplies the container runtimes and Compose. The first build downloads images and packages. `.env` is ignored by Git and excluded from the Docker build context. Compose reads it from the project root.

| `.env` setting | Meaning |
| --- | --- |
| `APP_PORT` | Host port, default `8000`. Use this port in the browser. |
| `POSTGRES_USER`, `POSTGRES_DB`, `POSTGRES_PASSWORD` | Credentials used by both containers. Keep the original values for an initialized volume. |
| `DEMO_TIMEZONE` | Local calendar timezone, default `Asia/Dhaka`. |
| `DEMO_SESSION_DAYS` | Session access period, 1–30 days. Default `7`. |
| `DEMO_SESSION_LIMIT` | Maximum active sessions, 1–10,000. Default `300`. |
| `RETRIEVAL_ENABLED` | `1` enables catalogue matching. `0` uses the standard suggestion and keeps the low-energy support rule. |
| `PYTHON_IMAGE`, `POSTGRES_IMAGE` | Optional registry overrides for the same Python and PostgreSQL base images. |

To configure `.env` manually, copy [`.env.example`](../.env.example) on a fresh installation and fill in `POSTGRES_PASSWORD` before running Compose. If the database volume already exists, restore the `.env` that was used to initialize it.

### Troubleshooting

- Docker engine unavailable. Open Docker Desktop and retry after the Linux engine has started.
- Port already in use. Set `APP_PORT=8001` in `.env`, rerun `docker compose up -d --wait`, and open `http://127.0.0.1:8001/`.
- Service unhealthy. Run `docker compose ps` and `docker compose logs --tail=100 app db`. If PostgreSQL reports invalid credentials, check the `.env` used to initialize the volume.
- Docker Hub connection reset. Set the registry overrides for the failing images and retry in the same PowerShell window. To keep using these settings in later shells, uncomment the corresponding lines in `.env`.

  ```powershell
  $env:PYTHON_IMAGE = 'public.ecr.aws/docker/library/python:3.12-slim-bookworm'
  $env:POSTGRES_IMAGE = 'public.ecr.aws/docker/library/postgres:16-bookworm'
  docker compose up -d --build --wait
  ```

Run `docker compose down` to stop the stack and keep the `steadyday_data` volume. Run the startup commands again to resume.

## Python and SQLite

Install [Python](https://www.python.org/downloads/windows/) 3.11 or newer. Use a free port if Docker is already serving SteadyDay. From a fresh PowerShell window at the project root:

```powershell
if (-not (Test-Path .\.venv\Scripts\python.exe)) { py -3 -m venv .venv }
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r server/requirements.txt
$env:PYTHONPATH = 'server'
$env:STEADYDAY_MODE = 'local'
$env:DATABASE_URL = 'sqlite:///./steadyday.sqlite3'
.\.venv\Scripts\python.exe -m uvicorn steadyday.main:app --host 127.0.0.1 --port 8001 --no-access-log
```

Open [SteadyDay on port 8001](http://127.0.0.1:8001/). The local API explorer is at `/docs` and readiness is at `/api/health`. The database is `steadyday.sqlite3` in the project folder. These commands supply backend settings directly. Use `Ctrl+C` to stop Uvicorn.

## Next.js on Windows

For the Vercel-style frontend, install [Node.js](https://nodejs.org/en/download) 24 and start the Docker backend on port 8000. From the project root:

```powershell
Set-Location web
if (-not (Test-Path .env.local)) { Copy-Item .env.local.example .env.local }
npm.cmd ci
npm.cmd run typecheck
npm.cmd run build
npm.cmd start
```

Open [Next.js at localhost](http://localhost:3000/). Match this exact origin to `APP_ORIGIN` in `web/.env.local`. If using the Python fallback, set `API_BASE_URL=http://127.0.0.1:8001` and restart Next.js. Use `npm.cmd run dev` in place of the build and start commands for local development. See [deployment](DEPLOYMENT.md) for Render and Vercel settings.

## Using the demo

- **Check in.** Choose a date within the displayed 14-day window and enter fictional sleep, movement and energy. Saving again updates that date. To remove an entry, choose its date and confirm **Delete check-in**.
- **Review trends.** Open **Insights** for current-week and rolling 7-, 14-, and 30-day views. The chart and table use saved entries, and a missing measurement appears as a gap.
- **Set goals.** Set movement and check-in targets or add named goals for the week. Edit, complete, reopen, or delete your goals from **Goals & Habits**.
- **Track habits.** Add a fictional routine or use a preset. Select a day and mark it complete. Select it again to undo. Progress and streaks reflect saved completions.
- **Use the coach.** Open **Why am I seeing this?** to see what prompted the tip. The breathing and mindfulness timers let you choose a duration, pause, resume, and reset.
- **Update your profile.** Open **Profile & Settings** to edit a fictional name, choose English or Bangla, or select light, dark, or system appearance. These preferences are saved with the demo session.
- **Manage reminders and data.** Set a check-in reminder, enable optional browser alerts, export JSON, or permanently delete the demo in **Profile & Settings**. Alerts depend on browser permission and the app being open.
