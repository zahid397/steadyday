from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from steadyday.config import Settings
from steadyday.main import create_app, COOKIE
from steadyday.recommend import rank, suggest

LOCAL = "/api/demo/"
ORIGIN = {"Origin": "http://testserver"}
GOOD = {"sleep_minutes": 405, "activity_minutes": 20, "energy": 3}


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.now = datetime(2026, 11, 12, 11, tzinfo=timezone.utc)
        self.cfg = Settings(database_url="sqlite:///" + str(Path(self.tmp.name)/"demo.db"))
        self.app = create_app(self.cfg, lambda: self.now)
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.client.__exit__, None, None, None)

    def onboard(self, persona="arif"):
        return self.client.post(LOCAL+"session", headers=ORIGIN, json={"persona":persona, "consent":True})

    def write(self, route, data):
        return self.client.put(LOCAL+route, headers=ORIGIN, json=data)

    def test_onboarding_and_synthetic_dashboard(self):
        response = self.onboard()
        self.assertEqual(response.status_code,201,response.text)
        self.assertEqual(response.json(),{"created":True})
        self.assertIn("HttpOnly",response.headers["set-cookie"])
        self.assertIn("SameSite=strict",response.headers["set-cookie"])
        dashboard = self.client.get(LOCAL+"dashboard").json()
        self.assertEqual(dashboard["profile"]["persona"],"arif")
        self.assertEqual(dashboard["profile"]["name"],"Arif")
        self.assertIsInstance(dashboard["suggestion"]["title"],str)
        self.assertEqual(dashboard["today"],"2026-11-12")
        self.assertTrue(all(e["is_sample"] for e in dashboard["entries"]))
        self.assertNotIn("session_token",str(dashboard))

    def test_invalid_input_and_consent(self):
        self.assertEqual(self.client.post(LOCAL+"session",headers=ORIGIN,json={"persona":"arif","consent":False}).status_code,422)
        self.assertEqual(self.client.post(LOCAL+"session",headers=ORIGIN,json={"persona":"guest","consent":True,"notes":"sensitive text"}).status_code,422)
        self.assertEqual(self.onboard().status_code,201)
        for bad in ({"energy":6},{"activity_minutes":241},{"sleep_minutes":"400"},{"activity_minutes":True},{"unexpected":"sensitive text"}):
            r=self.write("check-in",dict(GOOD,**bad))
            self.assertEqual(r.status_code,422,r.text)
            self.assertNotIn("sensitive text",r.text)
        self.assertEqual(self.write("goals",{"activity_days":0,"checkin_days":8}).status_code,422)
        self.assertEqual(self.write("reminder",{"time":"25:01"}).status_code,422)

    def test_write_checks_origin_and_content_type(self):
        self.assertEqual(self.client.post(LOCAL+"session",json={"persona":"arif","consent":True}).status_code,403)
        self.assertEqual(self.client.post(LOCAL+"session",headers=ORIGIN,content="plain").status_code,415)
        self.assertEqual(self.client.post(LOCAL+"session",headers=ORIGIN,json={"a":"x"*3000}).status_code,413)

    def test_today_upsert_persists_after_restart(self):
        self.onboard()
        self.assertEqual(self.write("check-in",GOOD).status_code,200)
        changed = dict(GOOD,activity_minutes=35)
        self.assertEqual(self.write("check-in",changed).json()["today_entry"]["activity_minutes"],35)
        with TestClient(create_app(self.cfg, lambda:self.now)) as other:
            other.cookies.set(COOKIE,self.client.cookies.get(COOKIE))
            r=other.get(LOCAL+"dashboard").json()
            self.assertEqual(r["today_entry"]["activity_minutes"],35)
            self.assertEqual(sum(x["day"]==r["today"] for x in r["entries"]),1)
            self.assertFalse(r["today_entry"]["is_sample"])

    def test_dated_checkin_edit_and_delete_are_scoped(self):
        self.onboard()
        day = "2026-11-11"
        for bad_day in ("2026-02-30", "2026-10-28", "2026-11-13"):
            self.assertEqual(self.write("check-in", dict(GOOD, day=bad_day)).status_code, 422)
            self.assertEqual(self.client.delete(LOCAL+"check-in", params={"day":bad_day}, headers=ORIGIN).status_code, 422)
        changed = self.write("check-in", dict(GOOD, day=day)).json()
        self.assertEqual(changed["entries"][-1], dict(GOOD, day=day, is_sample=False, mood=4))
        self.assertIsNone(changed["today_entry"])
        with TestClient(self.app) as other:
            self.assertEqual(other.post(LOCAL+"session", headers=ORIGIN, json={"persona":"arif", "consent":True}).status_code, 201)
            other.delete(LOCAL+"check-in", params={"day":day}, headers=ORIGIN).raise_for_status()
        self.assertEqual(self.client.get(LOCAL+"dashboard").json()["entries"][-1]["day"], day)
        self.client.delete(LOCAL+"check-in", params={"day":day}, headers=ORIGIN).raise_for_status()
        self.assertFalse(any(row["day"] == day for row in self.client.get(LOCAL+"export").json()["entries"]))

    def test_habit_toggle_persists_and_exports(self):
        self.onboard()
        check = {"habit": "screen_break", "day": "2026-11-12", "completed": True}
        self.assertEqual(self.write("habits", dict(check, day="2026-11-13")).status_code, 422)
        self.assertEqual(self.write("habits", dict(check, habit="unknown")).status_code, 422)
        self.assertEqual(self.write("habits", check).status_code, 200)
        self.assertEqual(self.write("habits", check).status_code, 200)
        rows = [{"habit": "screen_break", "day": "2026-11-12"}]
        self.assertEqual(self.client.get(LOCAL+"dashboard").json()["habit_completions"], rows)
        self.assertEqual(self.client.get(LOCAL+"export").json()["habit_completions"], rows)
        self.assertEqual(self.write("habits", dict(check, completed=False)).json()["habit_completions"], [])
        self.write("habits", check).raise_for_status()
        self.client.delete(LOCAL+"session", headers=ORIGIN).raise_for_status()
        with self.app.state.db.transaction() as tx:
            self.assertEqual(tx.one("SELECT COUNT(*) AS n FROM habit_completions")["n"], 0)

    def test_weekly_goals_and_progress(self):
        self.onboard()
        d=self.write("goals",{"activity_days":4,"checkin_days":6}).json()
        self.assertEqual(d["week"]["activity_target"],4)
        self.assertEqual(d["week"]["checkin_target"],6)
        before=d["week"]["activity_done"]
        r=self.write("check-in",GOOD).json()
        self.assertEqual(r["week"]["activity_done"],before+1)
        self.assertEqual(r["week"]["start"],"2026-11-09")

    def test_restart_prompt_keeps_history(self):
        self.onboard("samir")
        d=self.client.get(LOCAL+"dashboard").json()
        self.assertEqual(d["suggestion"]["id"],"restart")
        self.assertEqual(d["suggestion"]["kind"],"retrieval")
        old = d["entries"]
        new=self.write("check-in",GOOD).json()
        self.assertEqual(new["entries"][:-1],old)
        self.assertNotEqual(new["suggestion"]["id"],"restart")

    def test_support_never_recommends_more_activity(self):
        self.onboard()
        r=self.write("check-in",dict(GOOD,energy=1)).json()["suggestion"]
        self.assertEqual(r["kind"],"support")
        self.assertIn("qualified healthcare professional",r["body"])
        self.assertIn("cannot assess",r["body"])
        self.assertNotIn("walk",r["body"])

    def test_private_sessions_and_export(self):
        self.onboard()
        self.write("check-in",dict(GOOD,activity_minutes=101))
        with TestClient(self.app) as other:
            self.assertEqual(other.get(LOCAL+"dashboard").status_code,401)
            self.assertEqual(other.get(LOCAL+"export").status_code,401)
            self.assertEqual(other.post(LOCAL+"session",headers=ORIGIN,json={"persona":"arif","consent":True}).status_code,201)
            self.assertIsNone(other.get(LOCAL+"dashboard").json()["today_entry"])
            self.assertNotEqual(other.cookies.get(COOKIE),self.client.cookies.get(COOKIE))
        export=self.client.get(LOCAL+"export")
        self.assertTrue(export.json()["synthetic_only"])
        self.assertEqual(export.json()["entries"][-1]["activity_minutes"],101)
        self.assertNotIn("token",export.text)
        self.assertIn("no-store",export.headers["cache-control"])

    def test_reminder_and_delete_cascade(self):
        self.onboard()
        reminder=self.write("reminder",{"time":"00:00"}).json()["reminder"]
        self.assertEqual(reminder,{"time":"00:00","due":True})
        self.assertFalse(self.write("check-in",GOOD).json()["reminder"]["due"])
        self.assertIsNone(self.write("reminder",{"time":None}).json()["reminder"]["time"])
        self.assertEqual(self.client.delete(LOCAL+"session",headers=ORIGIN).status_code,200)
        self.assertEqual(self.client.get(LOCAL+"dashboard").status_code,401)
        with self.app.state.db.transaction() as tx:
            for table in ("demo_sessions","weekly_goals","check_ins"):
                self.assertEqual(tx.one("SELECT COUNT(*) AS n FROM "+table)["n"],0)

    def test_expired_session_denied_and_purged(self):
        self.onboard()
        self.now+=timedelta(days=8)
        self.assertEqual(self.client.get(LOCAL+"dashboard").status_code,401)
        self.assertEqual(self.app.state.demo.purge_expired(),1)

    def test_capacity_and_no_duplicate_browser_session(self):
        self.onboard()
        self.assertEqual(self.onboard().status_code,409)

    def test_health_unavailable(self):
        self.assertEqual(self.client.get("/healthz").status_code,200)
        self.assertEqual(self.client.get("/api/health").status_code,200)
        with patch.object(self.app.state.db,"healthy",return_value=False):
            self.assertEqual(self.client.get("/healthz").status_code,503)

    def test_bearer_api_and_proxy_key(self):
        cfg=Settings(database_url=self.cfg.database_url,proxy_key="x"*32,access_code="practice-code")
        with TestClient(create_app(cfg, lambda:self.now)) as c:
            p={"persona":"arif","consent":True,"access_code":"practice-code"}
            self.assertEqual(c.post("/v1/session",json=p).status_code,403)
            headers={"X-Proxy-Key":"x"*32}
            self.assertEqual(c.post("/v1/session",headers=headers,json=dict(p,access_code="bad")).status_code,403)
            r=c.post("/v1/session",headers=headers,json=p)
            self.assertEqual(r.status_code,201)
            headers["Authorization"]="Bearer "+r.json()["session_token"]
            self.assertEqual(c.get("/v1/dashboard",headers=headers).status_code,200)


class RecommendationTests(unittest.TestCase):
    def test_catalogue_ranking_and_cold_start(self):
        self.assertEqual(rank("sleep irregular bedtime")[0],"wind_down")
        self.assertEqual(rank("gap restart checkin")[0],"restart")
        self.assertEqual(rank("movement active activity goal")[0],"movement")
        self.assertEqual(suggest([], datetime.now().date(),0,3,True)["kind"],"fallback")

    def test_disabled_and_failed_retrieval_have_same_static_fallback(self):
        now=datetime(2026,11,12).date()
        entries=[{"day":now.isoformat(),"energy":3,"sleep_minutes":410,"activity_minutes":5}]
        disabled=suggest(entries,now,0,3,False)
        with patch("steadyday.recommend.rank",side_effect=RuntimeError):
            failed=suggest(entries,now,0,3,True)
        self.assertEqual(disabled,failed)
        self.assertEqual(failed["id"],"starter")

    def test_hosted_profile_refuses_sqlite(self):
        with self.assertRaises(ValueError):
            Settings(mode="hosted")

    def test_hosted_public_mode_requires_explicit_opt_in_and_proxy_key(self):
        settings = {"mode":"hosted", "database_url":"postgresql://localhost/demo", "proxy_key":"x"*32}
        with self.assertRaisesRegex(ValueError, "DEMO_PUBLIC"):
            Settings(**settings)
        self.assertTrue(Settings(**settings, public_demo=True).public_demo)
        with self.assertRaisesRegex(ValueError, "PROXY_KEY"):
            Settings(**dict(settings, proxy_key=""), public_demo=True)


class SettingsTests(unittest.TestCase):
    def test_compose_connection_escapes_credentials(self):
        variables = {
            "POSTGRES_HOST": "db", "POSTGRES_USER": "local+user",
            "POSTGRES_PASSWORD": "a:b@c/d#e", "POSTGRES_DB": "test-db",
        }
        with patch.dict(os.environ, variables, clear=True):
            self.assertEqual(Settings.from_env().database_url,
                             "postgresql+psycopg://local%2Buser:a%3Ab%40c%2Fd%23e@db:5432/test-db")

    def test_missing_compose_settings_fail_instead_of_using_sqlite(self):
        with patch.dict(os.environ, {"POSTGRES_HOST": "db"}, clear=True):
            with self.assertRaisesRegex(ValueError, "requires POSTGRES_USER"):
                Settings.from_env()


if __name__=="__main__":
    unittest.main()
