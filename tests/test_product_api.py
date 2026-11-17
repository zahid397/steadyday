from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
from contextlib import closing
import tempfile
import unittest

from fastapi.testclient import TestClient

from steadyday.config import Settings
from steadyday.main import COOKIE, create_app


BASE = "/api/demo/"
ORIGIN = {"Origin": "http://testserver"}
CHECKIN = {"sleep_minutes": 400, "activity_minutes": 22, "energy": 3}
TODAY = "2026-11-12"


class ProductTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.cfg = Settings(database_url=f"sqlite:///{Path(tmp.name) / 'demo.sqlite3'}", session_days=30)
        self.now = datetime(2026, 11, 12, 10, tzinfo=timezone.utc)
        self.app = create_app(self.cfg, lambda: self.now)
        self.client = self.enterContext(TestClient(self.app))
        self.onboard(self.client)

    def onboard(self, client):
        response = client.post(BASE + "session", headers=ORIGIN, json={"persona": "arif", "consent": True})
        self.assertEqual(response.status_code, 201)

    def write(self, resource, data):
        response = self.client.put(BASE + resource, headers=ORIGIN, json=data)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def create_item(self, resource, title, key):
        response = self.client.post(BASE + resource, headers=ORIGIN, json={"title": title})
        self.assertEqual(response.status_code, 201)
        return next(item for item in response.json()[key] if item["title"] == title)

    def test_checkin_fields_unicode_validation_and_legacy_update(self):
        notes = "🌿" * 500
        fields = dict(CHECKIN, day=TODAY, mood=4, stress=80, hydration=6, notes=notes)
        escaped_payload = self.client.put(BASE + "check-in", headers={**ORIGIN, "Content-Type": "application/json"},
                                          content=json.dumps(fields, ensure_ascii=True))
        self.assertEqual(escaped_payload.status_code, 200)
        self.assertEqual(escaped_payload.json()["suggestion"]["reason_key"], "stress")
        self.write("check-in", dict(CHECKIN, energy=4))
        entry = self.client.get(BASE + "check-in", params={"day": TODAY}).json()["entry"]
        self.assertEqual(entry, dict(fields, energy=4, is_sample=False))
        self.assertEqual(self.client.get(BASE + "export").json()["entries"][-1]["notes"], notes)
        for invalid in ({"notes": notes + "a"}, {"mood": 0}, {"stress": 101}, {"hydration": "4"}):
            response = self.client.put(BASE + "check-in", headers=ORIGIN, json=dict(CHECKIN, **invalid))
            self.assertEqual(response.status_code, 422)
            self.assertNotIn("🌿", response.text)
        self.write("check-in", dict(CHECKIN, notes=None))
        self.assertNotIn("notes", self.client.get(BASE + "check-in").json()["entry"])

    def test_insights_ranges_aggregate_saved_values(self):
        self.write("check-in", dict(CHECKIN, mood=4, stress=30, hydration=8))
        self.write("habits", {"habit": "reflect", "day": TODAY, "completed": True})
        for period, start in {"week": "2026-11-09", "7": "2026-11-06", "14": "2026-10-30", "30": "2026-10-14"}.items():
            result = self.client.get(BASE + "insights", params={"days": period}).json()
            self.assertEqual((result["start"], result["end"]), (start, TODAY))
            self.assertTrue(all(start <= entry["day"] <= TODAY for entry in result["entries"]))
            mood = [entry["mood"] for entry in result["entries"] if "mood" in entry]
            self.assertEqual(result["averages"]["mood"], round(sum(mood) / len(mood), 2))
            self.assertEqual(result["averages"]["stress"], 30)
            self.assertEqual(result["habits"], {"completed": 1, "possible": 3, "percent": 33})
        self.assertEqual(self.client.get(BASE + "insights?days=31").status_code, 422)
        self.assertEqual(TestClient(self.app).get(BASE + "insights").status_code, 401)

    def test_profile_partial_updates_reminders_and_restart(self):
        updated = self.write("profile", {"name": "  সবুজ  ", "language": "bn", "theme": "dark", "reminder_enabled": False,
                                         "notifications_enabled": True})
        self.assertEqual(updated["profile"]["name"], "সবুজ")
        self.assertFalse(self.write("reminder", {"time": "00:00"})["reminder"]["due"])
        self.write("profile", {"theme": "light"})
        invalid = self.client.put(BASE + "profile", headers=ORIGIN, json={"notifications_enabled": "yes"})
        self.assertEqual(invalid.status_code, 422)
        with TestClient(create_app(self.cfg, lambda: self.now)) as restarted:
            restarted.cookies.set(COOKIE, self.client.cookies.get(COOKIE))
            profile = restarted.get(BASE + "profile").json()
            self.assertEqual(profile["language"], "bn")
            self.assertEqual(profile["theme"], "light")
            self.assertTrue(profile["notifications_enabled"])
            self.assertEqual(restarted.get(BASE + "export").json()["profile"], profile)

    def test_goal_habit_lifecycles_and_session_isolation(self):
        goal = self.create_item("goal", "Take a lunch break", "goals")
        habit = self.create_item("habit", "Read for fun", "custom_habits")
        completed = self.write("goal", {"id": goal["id"], "title": "Take a short break", "completed": True})["goals"][0]
        self.assertTrue(completed["completed"])
        self.assertEqual(completed["title"], "Take a short break")
        self.assertFalse(self.write("goal", {"id": goal["id"], "completed": False})["goals"][0]["completed"])
        self.write("habit", {"id": habit["id"], "title": "Read a chapter", "day": TODAY, "completed": True})
        self.now += timedelta(days=1)
        self.write("habit", {"id": habit["id"], "day": "2026-11-13", "completed": True})
        saved = self.client.get(BASE + "habits").json()["custom_habits"][0]
        self.assertEqual((saved["title"], saved["streak"], saved["days"]), ("Read a chapter", 2, [TODAY, "2026-11-13"]))
        undone = self.write("habit", {"id": habit["id"], "day": "2026-11-13", "completed": False})["custom_habits"][0]
        self.assertEqual(undone["days"], [TODAY])
        with TestClient(self.app) as another:
            self.onboard(another)
            for resource, item in (("goal", goal), ("habit", habit)):
                self.assertEqual(another.put(BASE + resource, headers=ORIGIN, json={"id": item["id"], "title": "Different"}).status_code, 404)
                self.assertEqual(another.delete(BASE + resource, headers=ORIGIN, params={"id": item["id"]}).status_code, 404)
        for resource, key, item in (("goal", "goals", goal), ("habit", "custom_habits", habit)):
            removed = self.client.delete(BASE + resource, headers=ORIGIN, params={"id": item["id"]})
            self.assertEqual(removed.json()[key], [])
        self.assertEqual(self.client.get(BASE + "export").json()["custom_habits"], [])

    def test_session_deletion_cascades_to_new_data(self):
        self.write("profile", {"name": "Example"})
        self.create_item("goal", "Stretch after a break", "goals")
        habit = self.create_item("habit", "Read for fun", "custom_habits")
        self.write("habit", {"id": habit["id"], "day": TODAY, "completed": True})
        self.assertEqual(self.client.delete(BASE + "session", headers=ORIGIN).status_code, 200)
        with self.app.state.db.transaction() as tx:
            for table in ("profile_settings", "custom_goals", "custom_habits", "custom_habit_completions"):
                self.assertEqual(tx.one(f"SELECT COUNT(*) AS count FROM {table}")["count"], 0)

    def test_direct_routes_render_the_existing_shell(self):
        for route in ("/demo", "/check-in", "/insights", "/goals-habits", "/coach", "/settings"):
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200)
            self.assertIn("Content-Security-Policy", response.headers)
            self.assertIn('id="steadyday"', response.text)


class MigrationTests(unittest.TestCase):
    def test_existing_checkins_survive_idempotent_migration(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "old.sqlite3"
            with closing(sqlite3.connect(path)) as connection, connection:
                connection.executescript("""
                    CREATE TABLE check_ins (
                        session_id VARCHAR(36), day VARCHAR(10), sleep_minutes INTEGER,
                        activity_minutes INTEGER, energy INTEGER, is_sample INTEGER, PRIMARY KEY (session_id, day)
                    );
                    INSERT INTO check_ins VALUES ('old', '2026-11-12', 380, 21, 4, 0);
                """)
            app = create_app(Settings(database_url=f"sqlite:///{path}"))
            for _ in range(2):
                with TestClient(app) as client:
                    self.assertEqual(client.get("/healthz").status_code, 200)
            with closing(sqlite3.connect(path)) as connection:
                self.assertEqual(connection.execute("SELECT * FROM check_ins").fetchone(),
                                 ("old", TODAY, 380, 21, 4, 0, None, None, None, None))
