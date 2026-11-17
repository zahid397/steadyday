# SteadyDay security review

SteadyDay is a fictional wellbeing prototype. Arif and Samir and their seeded check-ins are fictional. The charts summarize stored sample and practice entries. Keep real health and identifying information out of this demo.

| Area | Controls reviewed |
| --- | --- |
| Secrets and repository | The actual `.env` and `web/.env.local` are local files. `.env.example` and `web/.env.local.example` are templates. Local database files, generated artifacts and dependency directories stay outside Git. Set hosted credentials in the relevant hosting dashboard. |
| Sessions | A random opaque cookie is HttpOnly and SameSite Strict. Hosted cookies use Secure on the configured HTTPS origin. The database stores only the token hash. Session expiration applies to reads and writes. |
| Access and caching | API operations use the resolved session ID. The hosted FastAPI routes require a server credential, and browser writes require the configured origin. The frontend uses same-origin API calls. API responses prevent caching. |
| Inputs and storage | API requests use Pydantic validation and bounded payloads. Database queries bind values as parameters. The frontend escapes displayed values and limits recommendation links to approved sources. |
| Logging and credentials | Application launch commands disable Uvicorn access logs. Database queries hide bound parameters, initialization messages omit underlying connection errors, and settings representations omit credentials. A hosting provider may retain operational logs. |
| Data rights | JSON export excludes session credentials. Session deletion cascades to its check-ins, goals, habits and settings. Local exports and provider backups have separate retention. |

The fictional access model uses browser sessions, with an optional judge access code in hosted mode. It has no identity verification, account recovery, per-user ingress rate limit, or application-layer encryption for stored notes. Public hosting requires a separate approval and production verification of HTTPS, environment settings, persistence and retention. See [deployment](DEPLOYMENT.md) and [responsible AI and privacy](RESPONSIBLE_AI_AND_PRIVACY.md).

## Release checks

- The local release-file scan checked eligible paths for credential signatures and matches to current nonempty local credentials. It found no matches. Git ignore checks confirmed that the actual local environment files and a local SQLite database are excluded.
- A PyPI advisory check flagged the virtual environment’s bundled pip 24.2. After upgrading it to 26.3, the follow-up PyPI check found no advisories in the installed distribution versions. `pip check` passed. The production npm audit reported zero advisories.
- The [test report](TEST_REPORT.md) records the session isolation, export, deletion and other verification results. The audits cover the packages and paths tested for this release.
