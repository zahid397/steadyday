# SteadyDay release verification

Verified on Windows 11 on 16 November 2026, using disposable fictional sessions. Local browser captures are under `evidence/release-native`, `evidence/release-docker`, and `evidence/release-next` when the corresponding test suites run. Generated evidence and earlier submission media stay out of Git.

| Check | Status | Result |
| --- | --- | --- |
| Backend and SQLite | PASS | 28 tests including profile changes, insights, goal and habit CRUD, demo isolation, export, cascading deletion and additive migration. Fixed a Windows-only fixture cleanup error by closing its SQLite connections explicitly. |
| Next.js proxy | PASS | 3 Node tests covering isolation, origin checks, invalid requests, export, writes, ranged insights and expired or deleted sessions. |
| Native Chrome | PASS | 6 scenarios covering navigation and reload, dated check-ins, goals and habits, recommendation and timers, language and theme, reminders, data controls, offline state and mobile layout. |
| Docker and PostgreSQL | PASS | Compose configuration, image build, healthy startup, API smoke test and a full app/database restart. A disposable check-in, habit and profile update survived the restart. |
| Next.js build | PASS | Production build and TypeScript checks. The wrapper uses the shared production stylesheet. |
| Dependency checks | PASS | Ruff syntax and undefined-name checks, browser JavaScript syntax checks, `pip check`, `pip-audit` on Python runtime dependencies, and npm audit. Both vulnerability audits found zero known issues in the audited dependencies. |
| Cloud configuration | PASS | Render Blueprint and Vercel configuration validated against provider schemas. |
| Live HTTPS and cloud persistence | NOT TESTED | Public deployment requires approval. See [deployment](DEPLOYMENT.md) for the exact provider settings and verification steps. |
| OS notification delivery | NOT TESTED | Chromium tests cover saved reminder and notification settings. OS alerts depend on device support and permission. |

See [the interaction checklist](FUNCTIONALITY_CHECKLIST.md) for feature coverage and the [API documentation](API_DOCUMENTATION.md) for request formats. GitHub Actions results are recorded by commit in the [repository’s Actions tab](https://github.com/zahid397/steadyday/actions).

## Reproduce in PowerShell

```powershell
$env:PYTHONPATH = 'server'
.\.venv\Scripts\python.exe -m pip install -r server/requirements-postgres.txt -r server/requirements-test.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*api.py' -v
.\.venv\Scripts\python.exe tests/run_proxy_tests.py
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_browser.py' -v
docker compose config --quiet
docker compose up -d --build --wait
docker compose exec -T app python scripts/smoke.py
```

The browser suite defaults to a temporary SQLite app. Set `STEADYDAY_TEST_URL` to an already-running code-free fictional demo origin to test Docker or Next.js. Set `STEADYDAY_EVIDENCE_DIR` to choose a capture directory, and `CHROMIUM_PATH` if using an installed Chromium-based browser. Start Docker using the [installation guide](INSTALLATION.md), which also covers the Python image mirror used for this Windows verification.

## Release limits

SteadyDay supports a time-limited fictional session. It has no persistent sign-in for real wellbeing records. The coach uses rule-based selection, with general non-clinical guidance. Browser notifications work only while the app is open and are subject to the browser’s permission. The earlier packaged walkthrough shows an older interface.
