# API documentation

Browser base path: `/api/demo`. Backend service base path: `/v1`; hosted calls require `X-Proxy-Key`, and scoped operations require the bearer token. The browser uses the HttpOnly cookie instead. All write requests from the browser must have the exact allowed origin.

| Method and resource | Request | Successful response |
| --- | --- | --- |
| GET `/config` | None | Whether access code is needed, timezone, retention, synthetic-only flag |
| POST `/session` | `persona: arif or samir`, `consent: true`, optional `access_code` | 201, sets cookie locally/at proxy; backend returns its opaque token to the proxy |
| GET `/dashboard` | Session cookie | Profile, recent entries, goal and habit progress, suggestion and reminder |
| PUT `/check-in` | Integer `sleep_minutes`, `activity_minutes`, `energy`. Optional `day` defaults to today. Optional `mood` (1–5), `stress` (0–100), `hydration` (0–30 glasses) and `notes` (500 characters). | Updated dashboard |
| DELETE `/check-in` | Query `day` in `YYYY-MM-DD` | Updated dashboard |
| GET `/insights` | Query `days` as `week`, `7`, `14` or `30` | Saved entries, date bounds, metric averages and habit consistency |
| GET `/goals` | Session cookie | Current weekly goals |
| PUT `/goals` | Integer `activity_days`, `checkin_days` | Updated dashboard |
| POST `/goal` | Fictional `title` (1–80 characters) | 201 with updated dashboard |
| PUT `/goal` | `id` and at least one of `title` or Boolean `completed` | Updated dashboard |
| DELETE `/goal` | Query `id` | Updated dashboard |
| GET `/habits` | Session cookie | Habit lists and progress |
| PUT `/habits` | `habit` as `screen_break`, `wind_down` or `reflect`, `day` in the elapsed portion of this week, Boolean `completed` | Updated dashboard |
| POST `/habit` | Fictional `title` (1–80 characters) | 201 with updated dashboard |
| PUT `/habit` | `id`, and a `title` or a `day` and Boolean `completed` | Updated dashboard |
| DELETE `/habit` | Query `id` | Updated dashboard |
| GET `/profile` | Session cookie | Fictional profile and saved preferences |
| PUT `/profile` | At least one of `name`, `language` (`en` or `bn`), `theme` (`system`, `light`, `dark`), Boolean `reminder_enabled` or `notifications_enabled` | Updated dashboard |
| PUT `/reminder` | `time: "HH:MM"` (24-hour) or `null` | Updated dashboard |
| GET `/export` | Session cookie | Downloadable JSON with the session's fictional check-ins, goal and habit data, profile and settings |
| DELETE `/session` | Session cookie | Deletes records and clears cookie |
| GET `/api/health` or `/healthz` (backend) | None | `{"status":"ok"}` or 503 |

Errors use `{"error":{"code":"…","message":"…","fields":["…"]}}` for validated application errors. Field names are allowlisted; values are never echoed. Common cases: 401 expired or missing session, 403 invalid origin/code, 409 session already active, 413 body size, 415 media type, 422 field/consent error, 429 demo capacity, 503 unavailable API/DB. A write that failed at the network boundary is not shown as successful. The user can reload and inspect the latest saved state.
