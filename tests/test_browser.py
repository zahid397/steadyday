import json
from contextlib import nullcontext
import os
from pathlib import Path
import re
import unittest

from playwright.sync_api import expect, sync_playwright
from browser_support import launch, local_api

EVIDENCE = Path(os.environ.get("STEADYDAY_EVIDENCE_DIR") or Path(__file__).resolve().parents[1]/"evidence")


class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        url = os.environ.get("STEADYDAY_TEST_URL")
        cls.server = nullcontext(url.rstrip("/")) if url else local_api()
        cls.url=cls.server.__enter__()
        cls.addClassCleanup(cls.server.__exit__,None,None,None)
        cls.p=sync_playwright().start()
        cls.addClassCleanup(cls.p.stop)
        cls.browser=launch(cls.p)
        cls.addClassCleanup(cls.browser.close)
        EVIDENCE.mkdir(exist_ok=True)

    def new_page(self, **kwargs):
        ctx=self.browser.new_context(**kwargs)
        self.addCleanup(ctx.close)
        self.addCleanup(lambda: ctx.request.delete(self.url+"/api/demo/session", headers={"Origin": self.url}))
        page=ctx.new_page()
        errors=[]
        page.on("pageerror",lambda error:errors.append(str(error)))
        self.addCleanup(lambda:self.assertEqual(errors,[]))
        return ctx,page

    def onboard(self, page, persona="arif"):
        page.goto(self.url+"/demo")
        expect(page.get_by_role("heading",name="Choose a fictional profile")).to_be_visible()
        if persona=="samir":
            page.locator('label.profile-choice').filter(has=page.locator('input[value="samir"]')).click()
        page.get_by_role("checkbox",name="I am an adult using this demo",exact=False).check()
        page.get_by_role("button",name="Start demo").click()
        expect(page.get_by_role("heading",name="Your wellbeing",exact=True)).to_be_visible()

    def test_desktop_workflow_saved_to_api_and_data_controls(self):
        ctx,page=self.new_page(viewport={"width":1440,"height":1000},accept_downloads=True)
        page.goto(self.url)
        expect(page.get_by_role("heading",level=1)).to_have_text(re.compile(r"Healthy routines,\s*at your pace\."))
        page.screenshot(path=EVIDENCE/"01-landing.png",full_page=True)
        page.get_by_role("link",name="Try the fictional demo").click()
        expect(page.get_by_role("heading",name="Choose a fictional profile")).to_be_visible()
        page.locator('label.profile-choice').filter(has=page.locator('input[value="samir"]')).click()
        page.get_by_role("checkbox").check()
        page.get_by_role("button",name="Start demo").click()
        expect(page.get_by_role("heading",name="Make the next check-in easy")).to_be_visible()
        page.get_by_text("Why am I seeing this?",exact=True).click()
        expect(page.get_by_text("There is a gap",exact=False)).to_be_visible()
        page.screenshot(path=EVIDENCE/"02-dashboard-desktop.png",full_page=True)

        initial = ctx.request.get(self.url+"/api/demo/dashboard").json()
        sample = initial["entries"][-1]
        date_field = page.locator("#checkin-day")
        date_field.fill(sample["day"])
        expect(page.get_by_role("heading", name="Past check-in")).to_be_visible()
        expect(page.get_by_label("Movement (minutes)")).to_have_value(str(sample["activity_minutes"]))
        date_field.fill(initial["today"])
        expect(page.get_by_role("heading", name="Today’s check-in")).to_be_visible()
        page.get_by_label("Sleep (hours)").fill("19")
        page.get_by_label("Movement (minutes)").fill("25")
        page.locator('label.energy-choice').filter(has=page.locator('input[name="energy"][value="3"]')).click()
        page.get_by_role("button",name="Save check-in").click()
        self.assertFalse(page.get_by_label("Sleep (hours)").evaluate("el => el.validity.valid"))
        self.assertIsNone(ctx.request.get(self.url+"/api/demo/dashboard").json()["today_entry"])
        page.get_by_role("button",name="Use sample values").click()
        page.get_by_label("Movement (minutes)").fill("25")
        page.locator("#check-form details summary").click()
        page.locator('#check-form textarea').fill("Fictional check-in for the test")
        page.get_by_role("button",name="Save check-in").click()
        expect(page.locator("#status")).to_have_text("Check-in saved.")
        page.reload()
        expect(page.get_by_label("Movement (minutes)")).to_have_value("25")
        page.locator("#check-form details summary").click()
        expect(page.locator('#check-form textarea')).to_have_value("Fictional check-in for the test")
        expect(page.get_by_role("button",name="Update check-in")).to_be_visible()
        page.get_by_label("Movement (minutes)").fill("27")
        page.get_by_role("button",name="Update check-in").click()
        expect(page.locator("#status")).to_have_text("Check-in saved.")
        page.get_by_role("button",name="Movement",exact=True).click()
        expect(page.get_by_role("button",name="Movement",exact=True)).to_have_attribute("aria-pressed","true")
        page.get_by_text("View the underlying data",exact=True).click()
        expect(page.get_by_role("table")).to_be_visible()
        expect(page.get_by_role("cell",name="27 min",exact=True).first).to_be_visible()

        self.navigate(page, "goals-habits")
        page.get_by_label("Movement days target").fill("4")
        page.get_by_role("button",name="Save goals").click()
        expect(page.locator("#status")).to_have_text("Weekly goals updated.")
        self.navigate(page, "settings")
        page.locator("#reminder-time").fill("19:30")
        page.get_by_role("button",name="Save reminder").click()
        expect(page.locator("#status")).to_have_text("Reminder saved.")
        page.get_by_role("button",name="Turn off reminder").click()
        expect(page.locator("#reminder-time")).to_have_value("")
        self.navigate(page, "goals-habits")
        habit = page.get_by_role("button", name="Take a screen break")
        habit.click()
        expect(habit).to_have_attribute("aria-pressed", "true")
        page.reload()
        expect(habit).to_have_attribute("aria-pressed", "true")
        self.navigate(page, "settings")
        with page.expect_download() as d:
            page.get_by_role("button",name="Export demo JSON").click()
        export=json.loads(d.value.path().read_text())
        self.assertTrue(export["synthetic_only"])
        self.assertEqual(export["entries"][-1]["activity_minutes"],27)
        self.assertEqual(export["entries"][-1]["notes"], "Fictional check-in for the test")
        self.assertEqual(export["weekly_goals"][-1]["activity_days"],4)
        self.assertEqual(export["habit_completions"][0]["habit"], "screen_break")
        self.navigate(page, "check-in")
        page.get_by_role("button", name="Delete check-in", exact=True).click()
        page.get_by_role("dialog").get_by_role("button", name="Delete permanently").click()
        expect(page.locator("#status")).to_have_text("Check-in deleted.")
        page.reload()
        expect(page.get_by_role("button",name="Save check-in")).to_be_visible()
        self.navigate(page, "settings")
        page.get_by_role("button",name="Delete demo",exact=True).click()
        expect(page.get_by_role("dialog")).to_be_visible()
        page.keyboard.press("Escape")
        expect(page.get_by_role("dialog")).not_to_be_visible()
        page.get_by_role("button",name="Delete demo",exact=True).click()
        page.get_by_role("button",name="Delete permanently").click()
        expect(page.get_by_text("Your demo and its entries were deleted.")).to_be_visible()
        self.assertEqual(ctx.request.get(self.url+"/api/demo/dashboard").status,401)

    def navigate(self, page, route):
        link = page.locator(f'a[data-route][href="/{route}"]:visible').first
        expect(link).to_be_visible()
        link.click()
        expect(page).to_have_url(re.compile(f"/{route}$"))

    def test_all_app_routes_and_activity_timers(self):
        _, page = self.new_page(viewport={"width": 1280, "height": 840}, reduced_motion="reduce")
        self.onboard(page)
        headings = {
            "check-in": "Daily Check-in", "insights": "Insights", "goals-habits": "Goals & Habits",
            "coach": "Wellbeing Coach", "settings": "Profile & Settings", "demo": "Your wellbeing",
        }
        for route, heading in headings.items():
            self.navigate(page, route)
            expect(page.get_by_role("heading", name=heading, level=1)).to_be_visible()
            response = page.reload()
            self.assertEqual(response.status, 200)
            expect(page.get_by_role("heading", name=heading, level=1)).to_be_visible()

        page.clock.install()
        for kind, title, cue in (
            ("breathing", "Guided breathing", "Breathe in gently"),
            ("mindfulness", "Mindful pause", "Notice what is here"),
        ):
            trigger = page.locator(f'[data-activity="{kind}"]:visible').first
            trigger.click()
            dialog = page.get_by_role("dialog", name=title)
            expect(dialog).to_be_visible()
            dialog.get_by_label("Duration (minutes)").select_option("1")
            expect(dialog.get_by_role("timer")).to_have_text("01:00")
            dialog.get_by_role("button", name="Start", exact=True).click()
            expect(dialog.get_by_role("status")).to_have_text(cue)
            page.clock.run_for(2000)
            dialog.get_by_role("button", name="Pause").click()
            expect(dialog.get_by_role("status")).to_have_text("Paused")
            paused = dialog.get_by_role("timer").inner_text()
            page.clock.run_for(2500)
            expect(dialog.get_by_role("timer")).to_have_text(paused)
            dialog.get_by_role("button", name="Resume").click()
            page.clock.fast_forward(61000)
            expect(dialog.get_by_role("status")).to_have_text("Practice complete")
            dialog.get_by_role("button", name="Reset").click()
            expect(dialog.get_by_role("timer")).to_have_text("01:00")
            page.keyboard.press("Escape")
            expect(dialog).not_to_be_visible()
            expect(trigger).to_be_focused()

    def test_goals_habits_insights_and_profile_persist(self):
        ctx, page = self.new_page(viewport={"width": 1360, "height": 920})
        self.onboard(page)
        dashboard_url = self.url + "/api/demo/dashboard"

        self.navigate(page, "goals-habits")
        for noun, name, replacement, list_key in (
            ("goal", "Make space for an evening break", "Plan an evening break", "goals"),
            ("habit", "Put devices aside", "Put devices aside after dinner", "custom_habits"),
        ):
            form = page.locator(f"#custom-{noun}-form")
            form.get_by_label(noun.capitalize() + " name").fill(name)
            form.get_by_role("button", name=re.compile(r"Add", re.I)).click()
            toggle = page.get_by_role("button", name=name, exact=True)
            expect(toggle).to_have_attribute("aria-pressed", "false")
            toggle.click()
            expect(toggle).to_have_attribute("aria-pressed", "true")
            page.reload()
            expect(toggle).to_have_attribute("aria-pressed", "true")
            record = next(item for item in ctx.request.get(dashboard_url).json()[list_key] if item["title"] == name)
            if noun == "habit":
                self.assertEqual(record["streak"], 1)
            else:
                self.assertTrue(record["completed"])
            toggle.click()
            expect(toggle).to_have_attribute("aria-pressed", "false")
            page.get_by_role("button", name=re.compile(f"Edit.*{re.escape(name)}", re.I)).click()
            edit = page.get_by_role("dialog", name="Edit " + noun)
            edit.get_by_label(noun.capitalize() + " name").fill(replacement)
            edit.get_by_role("button", name="Save changes").click()
            expect(page.get_by_role("button", name=replacement, exact=True)).to_be_visible()
            page.get_by_role("button", name=re.compile(f"Delete.*{re.escape(replacement)}", re.I)).click()
            delete = page.get_by_role("dialog")
            delete.get_by_role("button", name=re.compile("Delete", re.I)).click()
            expect(page.get_by_role("button", name=replacement, exact=True)).to_have_count(0)
            self.assertFalse(any(item["id"] == record["id"] for item in ctx.request.get(dashboard_url).json()[list_key]))

        self.navigate(page, "demo")
        page.get_by_role("button", name="Use sample values").click()
        page.get_by_role("button", name="Save check-in").click()
        expect(page.locator("#status")).to_have_text("Check-in saved.")
        self.navigate(page, "insights")
        with page.expect_response(re.compile(r"/api/demo/insights\?days=30$")) as response:
            page.get_by_role("button", name="30 days", exact=True).click()
        insights = response.value.json()
        self.assertEqual(insights["days"], 30)
        self.assertGreater(insights["entries"][-1]["mood"], 0)
        expect(page.get_by_role("button", name="30 days", exact=True)).to_have_attribute("aria-pressed", "true")
        page.screenshot(path=EVIDENCE / "04-insights.png", full_page=True)

        self.navigate(page, "settings")
        profile = page.locator("#profile-form")
        profile.get_by_label("Fictional display name").fill("Demo Arif")
        profile.get_by_role("button", name=re.compile("Save", re.I)).click()
        expect(page.locator("#status")).to_contain_text(re.compile("saved|updated", re.I))
        page.reload()
        expect(profile.get_by_label("Fictional display name")).to_have_value("Demo Arif")
        self.assertEqual(ctx.request.get(dashboard_url).json()["profile"]["name"], "Demo Arif")
        with page.expect_response(lambda value: value.url.endswith("/api/demo/profile") and value.request.method == "PUT") as saved:
            page.get_by_label("Enable browser reminder notifications").check()
        self.assertTrue(saved.value.json()["profile"]["notifications_enabled"])
        page.reload()
        expect(page.get_by_label("Enable browser reminder notifications")).to_be_checked()

    def test_mobile_bangla_themes_and_keyboard(self):
        _,page=self.new_page(viewport={"width":390,"height":844},is_mobile=True,has_touch=True,device_scale_factor=2)
        page.goto(self.url)
        skip = page.get_by_role("link", name="Skip to content")
        expect(skip).to_be_attached()
        page.keyboard.press("Tab")
        expect(skip).to_be_focused()
        self.onboard(page)
        expect(page.locator("html")).to_have_attribute("lang","en")
        expect(page.get_by_role("heading",name="Your wellbeing",exact=True)).to_be_visible()
        self.navigate(page, "settings")
        expect(page.get_by_role("heading", name="Profile & Settings", level=1)).to_be_visible()
        page.get_by_label("Language").select_option("bn")
        expect(page.locator("html")).to_have_attribute("lang", "bn")
        page.get_by_label("দেখতে কেমন হবে").select_option("dark")
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        page.reload()
        expect(page.locator("html")).to_have_attribute("lang", "bn")
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        self.navigate(page, "demo")
        expect(page.get_by_role("heading",name="আপনার সুস্থতা",exact=True)).to_be_visible()
        expect(page.locator(".app-top-title small")).to_be_visible()
        self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
        page.screenshot(path=EVIDENCE/"03-dashboard-mobile.png",full_page=True)
        page.set_viewport_size({"width":320,"height":750})
        self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
        self.navigate(page, "settings")
        page.get_by_label("দেখতে কেমন হবে").select_option("light")
        page.get_by_label("ভাষা").select_option("en")
        self.navigate(page, "demo")
        expect(page.locator("html")).to_have_attribute("data-theme", "light")
        expect(page.get_by_role("heading",name="Your wellbeing",exact=True)).to_be_visible()

    def test_backend_failure_and_retry(self):
        _,page=self.new_page()
        page.route("**/api/demo/dashboard",lambda route:route.abort())
        page.goto(self.url+"/demo")
        expect(page.get_by_role("heading",name="The demo service is unavailable")).to_be_visible()
        page.unroute("**/api/demo/dashboard")
        page.get_by_role("button",name="Try again").click()
        expect(page.get_by_role("heading",name="Choose a fictional profile")).to_be_visible()

    def test_ui_session_isolation_and_support(self):
        _,a=self.new_page()
        _,b=self.new_page()
        self.onboard(a)
        self.onboard(b)
        a.get_by_role("button",name="Use sample values").click()
        a.locator('label.energy-choice').filter(has=a.locator('input[name="energy"][value="1"]')).click()
        a.get_by_role("button",name="Save check-in").click()
        expect(a.get_by_role("heading",name="Make space for qualified support")).to_be_visible()
        b.reload()
        expect(b.get_by_role("button",name="Save check-in")).to_be_visible()
        self.assertIsNone(b.request.get(self.url+"/api/demo/dashboard").json()["today_entry"])
        a.get_by_role("link",name="When to seek qualified support").click()
        expect(a.get_by_role("heading",name="Your data and safety")).to_be_visible()


if __name__=="__main__":
    unittest.main()
