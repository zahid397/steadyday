# Prepare SteadyDay for Render and Vercel

For a hosted release, Vercel serves the Next.js frontend and proxies `/api/demo/*` to a Render Docker web service. Render PostgreSQL stores the fictional sessions on its own storage. Each browser gets a separate session and copy of the sample data. For local use, follow the [Windows installation guide](INSTALLATION.md).

## Prepare the repository

Confirm the intended commit is on the private repository's `main` branch and the **Verify SteadyDay** workflow passed for that SHA. Confirm the repository includes `render.yaml`, `Dockerfile`, and `web/package-lock.json`. The local `.env`, `web/.env.local`, credentials, databases, and installed dependencies stay outside Git. Both providers need explicit access to the private repository.

Public deployment requires approval. Applying the Render Blueprint or clicking Deploy in Vercel can create a publicly reachable URL, even when the source repository is private. Verify that billing and plan selections match what was approved before creating resources.

## Render API and PostgreSQL

1. Validate the root Blueprint using `render blueprints validate render.yaml` with Render CLI v2.7 or later. In Render, select **New → Blueprint**, connect the private repository and select `main`.
2. Review the plan before applying. The Blueprint sets up a Docker web service and an internal-only PostgreSQL 16 database in Singapore. It matches the Dockerfile's `0.0.0.0:8000` listener and checks `/api/health`. The service's automatic code deploys are off. In the Blueprint settings, also disable Auto Sync so infrastructure changes are applied manually. For subsequent releases, deploy the commit whose CI checks passed. [Blueprint reference](https://render.com/docs/blueprint-spec) · [Blueprint sync settings](https://render.com/docs/infrastructure-as-code) · [Docker on Render](https://render.com/docs/docker)
3. Enter the independent `PROXY_KEY` and `DEMO_ACCESS_CODE` secrets when Render prompts for them. Save the proxy key in a secure location so the Vercel server can use the same value. Confirm the configuration below.

   | Variable | Value |
   | --- | --- |
   | `STEADYDAY_MODE` | `hosted`, set by the Blueprint. |
   | `PORT` | `8000`, set by the Blueprint. |
   | `DATABASE_URL` | Injected from the managed database’s internal connection string. The database role needs schema creation rights for startup. |
   | `PROXY_KEY` | Generate a random server secret of at least 32 characters. Use the identical value on Vercel. |
   | `DEMO_ACCESS_CODE` | Generate a separate 12–128 character reviewer code. Share it separately with reviewers. |
   | `DEMO_TIMEZONE` | `Asia/Dhaka`, set by the Blueprint. |
   | `DEMO_SESSION_DAYS` | `7`, set by the Blueprint. |
   | `DEMO_SESSION_LIMIT` | `300` active sessions, set by the Blueprint. |
   | `RETRIEVAL_ENABLED` | `1`, set by the Blueprint. |

4. After approval, apply the Blueprint. In the Render dashboard, check that the Docker build and health check succeed. Keep the Vercel deployment on hold until the Render URL returns `{"status":"ok"}` at `/api/health`, and direct requests to `/v1/config` receive HTTP `403`.

The Free Blueprint suits a short fictional review. The web service can sleep when idle. Free Render Postgres survives web service restarts but expires 30 days after creation and lacks backups. Review a persistent paid plan separately if the review needs to last longer. [Render Free limits](https://render.com/docs/free)

The backend applies additive changes during startup and keeps records in PostgreSQL. New sessions trigger expired-session cleanup. Where the hosting plan provides operator command access, `python -m steadyday.cleanup` from the running image also clears expired sessions. Hosted mode keeps `/v1` behind the proxy key and exposes the health endpoints. [Render environment variables](https://render.com/docs/configure-environment-variables)

## Vercel frontend

1. After deployment approval, import the same private repository and select `web` as Root Directory with the **Next.js** framework preset. Use Node 24, `npm ci` for installation and `npm run build` for the build. Select the verified release commit and configure production variables before taking the frontend live.
2. Set these variables for **Production**. Set `APP_ORIGIN` using the fixed production domain assigned to the project. Redeploy after changing the variables. `web/vercel.json` disables automatic Git deployments. For subsequent releases, use **Deployments → Create Deployment** with the verified commit SHA. [Vercel Git deployments](https://vercel.com/docs/git) · [Vercel Git configuration](https://vercel.com/docs/project-configuration/git-configuration)

   | Variable | Value |
   | --- | --- |
   | `API_BASE_URL` | Actual Render HTTPS origin, with no path. |
   | `APP_ORIGIN` | Exact Vercel HTTPS origin reviewers will open, without a trailing slash. |
   | `PROXY_KEY` | The same secret as Render. |

The browser sends requests to the Vercel origin. The Vercel server sends requests to Render. This same-origin design uses no cross-origin browser requests or `NEXT_PUBLIC_*` variables. `DATABASE_URL` and `DEMO_ACCESS_CODE` belong on Render. Use the production domain for testing writes because the proxy checks the exact origin. [Next.js on Vercel](https://vercel.com/docs/frameworks/full-stack/nextjs) · [Vercel environment variables](https://vercel.com/docs/environment-variables)

## Verify the deployed release

1. Open the Vercel production link in a clean browser. Confirm it opens over HTTPS with the intended reviewer access. In PowerShell, check Render with `curl.exe -fsS "$env:RENDER_API_ORIGIN/api/health"` after setting `RENDER_API_ORIGIN` to the actual HTTPS origin without a trailing slash. The health response should be `{"status":"ok"}`. A direct browser visit to `/v1/config` should return `403`.
2. Start a fictional demo. Save a check-in, refresh, edit it, and verify it appears in the chart and export. Use a second browser context to verify that the edit is private to the first session. Check the mobile layout and switch language and theme.
3. With a disposable fictional session still open, redeploy the Render service and confirm that the session, check-in and habit remain. Delete the session afterward and check that its cookie no longer opens the dashboard.
4. Inspect the browser console and Network tab for failed requests. Check the dashboard’s retry state if the backend is temporarily unavailable. For a code-free deployment, the browser suite can use the deployed origin via `STEADYDAY_TEST_URL`.
5. Record the actual Vercel app, Render API, Render `/api/health`, and GitHub repository URLs after the checks pass.
