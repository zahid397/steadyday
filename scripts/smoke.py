"""Run a disposable fictional demo against the running app using the standard library."""

from http.cookiejar import CookieJar
import json
import sys
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, ProxyHandler, Request, build_opener


def smoke(origin: str) -> None:
    browser = build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar()))

    def request(path: str, method: str = "GET", payload: dict | None = None, status: int = 200):
        headers = {"Origin": origin} if method != "GET" else {}
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode()
        req = Request(origin + path, method=method, headers=headers, data=body)
        try:
            response = browser.open(req, timeout=7)
        except HTTPError as exc:
            response = exc
        with response:
            if response.status != status:
                raise RuntimeError(f"{method} {path}: expected {status}, got {response.status}")
            data = response.read()
            if response.headers.get_content_type() == "application/json":
                return json.loads(data)
            return data

    api = "/api/demo/"
    assert request("/api/health") == {"status": "ok"}
    assert b'lang="en"' in request("/")
    for screen in ("demo", "check-in", "insights", "goals-habits", "coach", "settings", "privacy"):
        assert b'id="steadyday"' in request("/" + screen)
    for asset in ("app.js", "copy.js", "copy-bn.js", "activities.js", "notifications.js"):
        request("/steadyday/" + asset)
    request(api + "dashboard", status=401)
    request(api + "session", "POST", {"persona": "samir", "consent": True}, status=201)
    try:
        initial = request(api + "dashboard")
        assert initial["profile"]["name"] == "Samir"
        assert initial["suggestion"]["id"] == "restart"
        assert isinstance(initial["suggestion"]["body"], str)
        request(api + "check-in", "PUT", {"sleep_minutes": 405, "activity_minutes": 25, "energy": 3,
                                           "mood": 4, "stress": 35, "hydration": 6, "notes": "Fictional entry"})
        assert request(api + "dashboard")["today_entry"]["activity_minutes"] == 25
        insights = request(api + "insights?days=30")
        assert insights["days"] == 30 and insights["entries"][-1]["mood"] == 4
        updated = request(api + "goals", "PUT", {"activity_days": 4, "checkin_days": 6})
        assert updated["week"]["activity_target"] == 4
        updated = request(api + "goal", "POST", {"title": "Plan a quiet evening"}, status=201)
        goal = next(item for item in updated["goals"] if item["title"] == "Plan a quiet evening")
        updated = request(api + "goal", "PUT", {"id": goal["id"], "completed": True})
        assert next(item for item in updated["goals"] if item["id"] == goal["id"])["completed"]
        request(api + "goal?id=" + goal["id"], "DELETE")
        updated = request(api + "reminder", "PUT", {"time": "19:30"})
        assert updated["reminder"]["time"] == "19:30"
        habit = {"habit": "screen_break", "day": initial["today"]}
        updated = request(api + "habits", "PUT", dict(habit, completed=True))
        assert updated["habit_completions"] == [habit]
        updated = request(api + "habit", "POST", {"title": "Set aside a quiet moment"}, status=201)
        custom = next(item for item in updated["custom_habits"] if item["title"] == "Set aside a quiet moment")
        updated = request(api + "habit", "PUT", {"id": custom["id"], "day": initial["today"], "completed": True})
        assert next(item for item in updated["custom_habits"] if item["id"] == custom["id"])["streak"] == 1
        request(api + "habit?id=" + custom["id"], "DELETE")
        request(api + "profile", "PUT", {"name": "Samir Practice", "language": "bn", "theme": "dark"})
        assert request(api + "dashboard")["profile"]["name"] == "Samir Practice"
        exported = request(api + "export")
        assert exported["synthetic_only"] and exported["entries"][-1]["activity_minutes"] == 25
        assert exported["habit_completions"] == [habit]
        updated = request(api + "check-in?day=" + initial["today"], "DELETE")
        assert updated["today_entry"] is None
    finally:
        request(api + "session", "DELETE")
    request(api + "dashboard", status=401)
    print("PASS: health, routes, onboarding, check-in, insights, goals, habits, profile, reminder, export and deletion.")


if __name__ == "__main__":
    try:
        smoke((sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/"))
    except Exception as error:
        sys.exit(f"Smoke test failed: {error}")
