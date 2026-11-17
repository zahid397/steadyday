from datetime import date, datetime, timedelta, timezone
import hashlib
import secrets
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from .config import Settings
from .db import Database, Transaction
from .models import CheckIn, GoalUpdate, Goals, HabitCompletion, HabitUpdate, Onboard, ProfileUpdate, Reminder
from .recommend import suggest

ACTIVE_MINUTES = 10  # Definition for the demo's count. It is not a medical target.
HISTORY_DAYS = 14
PRESET_HABITS = ("screen_break", "wind_down", "reflect")
CHECKIN_METRICS = ("sleep_minutes", "activity_minutes", "energy", "mood", "stress", "hydration")
OPTIONAL_CHECKIN = ("mood", "stress", "hydration", "notes")
MAX_CUSTOM_ITEMS = 50
PERSONAS = {
    "arif": {"name": "Arif", "offsets": (1, 2, 3, 4, 6, 8, 10, 12),
             "sleep": (390, 445, 360, 420, 405, 425, 385, 425),
             "move": (20, 15, 0, 30, 0, 25, 15, 0), "energy": (3, 4, 2, 3, 3, 3, 3, 2),
             "mood": (4, 4, 2, 3, 3, 3, 2, 3)},
    "samir": {"name": "Samir", "offsets": (4, 5, 6, 7, 9, 10, 11, 13),
              "sleep": (425, 430, 450, 420, 435, 390, 445, 440),
              "move": (20, 0, 25, 15, 0, 20, 0, 18), "energy": (3, 3, 4, 3, 2, 3, 4, 3),
              "mood": (3, 3, 4, 3, 2, 3, 4, 3)},
}

CHECKIN_SQL = """INSERT INTO check_ins
(session_id, day, sleep_minutes, activity_minutes, energy, is_sample, mood, stress, hydration, notes)
VALUES (:session_id, :day, :sleep_minutes, :activity_minutes, :energy, :is_sample, :mood, :stress, :hydration, :notes)
ON CONFLICT (session_id, day) DO UPDATE SET sleep_minutes=EXCLUDED.sleep_minutes,
activity_minutes=EXCLUDED.activity_minutes, energy=EXCLUDED.energy, is_sample=EXCLUDED.is_sample,
mood=CASE WHEN :set_mood THEN EXCLUDED.mood ELSE check_ins.mood END,
stress=CASE WHEN :set_stress THEN EXCLUDED.stress ELSE check_ins.stress END,
hydration=CASE WHEN :set_hydration THEN EXCLUDED.hydration ELSE check_ins.hydration END,
notes=CASE WHEN :set_notes THEN EXCLUDED.notes ELSE check_ins.notes END"""
CHECKIN_SELECT = "SELECT day, sleep_minutes, activity_minutes, energy, is_sample, mood, stress, hydration, notes FROM check_ins"
GOAL_SQL = """INSERT INTO weekly_goals (session_id, week_start, activity_days, checkin_days)
VALUES (:session_id, :week_start, :activity_days, :checkin_days)
ON CONFLICT (session_id, week_start) DO UPDATE SET activity_days=EXCLUDED.activity_days,
checkin_days=EXCLUDED.checkin_days"""


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(code)
        self.status, self.code, self.message = status, code, message


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def digest(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def week_start(today: date) -> date:
    return today - timedelta(days=today.weekday())


def iso_epoch(seconds: int) -> str:
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat()


def checkin_record(row: dict[str, Any]) -> dict[str, Any]:
    entry = dict(row, is_sample=bool(row["is_sample"]))
    return {key: value for key, value in entry.items() if value is not None}


def checkin_parameters(values: dict[str, Any]) -> dict[str, Any]:
    return {
        **dict.fromkeys(OPTIONAL_CHECKIN), **values,
        **{f"set_{key}": key in values for key in OPTIONAL_CHECKIN},
    }


def streak(days: list[str], today: date) -> int:
    completed = set(days)
    day = today if today.isoformat() in completed else today - timedelta(days=1)
    length = 0
    while day.isoformat() in completed:
        length += 1
        day -= timedelta(days=1)
    return length


class DemoService:
    def __init__(self, settings: Settings, db: Database, clock=utcnow):
        self.settings, self.db, self.clock = settings, db, clock
        self.zone = ZoneInfo(settings.timezone)

    def local_now(self) -> datetime:
        return self.clock().astimezone(self.zone)

    def get(self, token: str) -> dict[str, Any]:
        with self.db.transaction() as tx:
            row = tx.one("SELECT * FROM demo_sessions WHERE token_hash=:hash AND expires_at > :now",
                         hash=digest(token), now=int(self.clock().timestamp()))
        if not row:
            raise AppError(401, "SESSION_REQUIRED", "Start a new demo or resume an active one.")
        return row

    def purge_expired(self) -> int:
        with self.db.transaction(write=True) as tx:
            return tx.execute("DELETE FROM demo_sessions WHERE expires_at <= :now", now=int(self.clock().timestamp())).rowcount

    def create(self, data: Onboard) -> tuple[str, int]:
        if not data.consent:
            raise AppError(422, "CONSENT_REQUIRED", "Confirm that this session will use only fictional data.")
        if self.settings.access_code and not secrets.compare_digest(data.access_code.encode(), self.settings.access_code.encode()):
            raise AppError(403, "DEMO_CODE", "The demo access code is not valid.")
        raw, sid = secrets.token_urlsafe(32), str(uuid4())
        local = self.local_now()
        created, ttl = int(local.timestamp()), self.settings.session_days * 86400
        seed = PERSONAS[data.persona]
        with self.db.transaction(write=True) as tx:
            if self.db.kind == "postgresql":
                tx.execute("SELECT pg_advisory_xact_lock(843102)")
            tx.execute("DELETE FROM demo_sessions WHERE expires_at <= :now", now=created)
            active = tx.one("SELECT COUNT(*) AS total FROM demo_sessions")
            if active is not None and active["total"] >= self.settings.active_session_limit:
                raise AppError(429, "DEMO_CAPACITY", "The demo is currently at capacity.")
            tx.execute("""INSERT INTO demo_sessions
                          (id, token_hash, persona, created_at, expires_at, consent_version)
                          VALUES (:id, :token_hash, :persona, :created_at, :expires_at, 1)""",
                       id=sid, token_hash=digest(raw), persona=data.persona, created_at=created, expires_at=created + ttl)
            records = zip(seed["offsets"], seed["sleep"], seed["move"], seed["energy"], seed["mood"], strict=True)
            for offset, sleep, move, energy, mood in records:
                tx.execute(CHECKIN_SQL, session_id=sid, day=(local.date()-timedelta(days=offset)).isoformat(),
                           **checkin_parameters({"sleep_minutes": sleep, "activity_minutes": move, "energy": energy,
                                                 "is_sample": 1, "mood": mood}))
            tx.execute(GOAL_SQL, session_id=sid, week_start=week_start(local.date()).isoformat(),
                       activity_days=3, checkin_days=5)
        return raw, ttl

    def dashboard(self, session: dict[str, Any]) -> dict[str, Any]:
        sid = session["id"]
        now = self.local_now()
        day = now.date()
        first = day - timedelta(days=HISTORY_DAYS-1)
        week = week_start(day)
        with self.db.transaction() as tx:
            entries = self.checkin_entries(tx, sid, first, day)
            goals = tx.one("""SELECT activity_days, checkin_days FROM weekly_goals
                WHERE session_id=:sid AND week_start <= :start ORDER BY week_start DESC LIMIT 1""",
                           sid=sid, start=week.isoformat()) or {"activity_days": 3, "checkin_days": 5}
            habits = tx.all("""SELECT day, habit FROM habit_completions
                WHERE session_id=:sid AND day <= :end ORDER BY day, habit""", sid=sid, end=day.isoformat())
            profile = self.profile_for(tx, session)
            custom_goals = self.custom_goals_for(tx, sid, week)
            custom_habits = self.custom_habits_for(tx, sid, day)
        this_week = [r for r in entries if r["day"] >= week.isoformat()]
        active = sum(r["activity_minutes"] >= ACTIVE_MINUTES for r in this_week)
        today_entry = entries[-1] if entries and entries[-1]["day"] == day.isoformat() else None
        minute = session["reminder_minute"]
        return {
            "profile": profile,
            "today": day.isoformat(), "today_entry": today_entry, "entries": entries,
            "trend_start": first.isoformat(),
            "goals": custom_goals,
            "custom_habits": custom_habits,
            "habit_completions": [r for r in habits if r["day"] >= week.isoformat()],
            "habit_streaks": {habit: streak([r["day"] for r in habits if r["habit"] == habit], day) for habit in PRESET_HABITS},
            "week": {"start": week.isoformat(), "end": (week+timedelta(days=6)).isoformat(),
                     "activity_target": goals["activity_days"], "checkin_target": goals["checkin_days"],
                     "activity_done": active, "checkin_done": len(this_week),
                     "activity_day_minutes": ACTIVE_MINUTES},
            "suggestion": suggest(entries, day, active, goals["activity_days"], self.settings.retrieval_enabled),
            "reminder": {"time": f"{minute//60:02d}:{minute%60:02d}" if minute is not None else None,
                         "due": profile["reminder_enabled"] and minute is not None and today_entry is None
                         and now.hour * 60 + now.minute >= minute},
        }

    def checkin_entries(self, tx: Transaction, sid: str, first: date, last: date) -> list[dict[str, Any]]:
        return [checkin_record(row) for row in tx.all(
            CHECKIN_SELECT + " WHERE session_id=:sid AND day BETWEEN :first AND :last ORDER BY day",
            sid=sid, first=first.isoformat(), last=last.isoformat(),
        )]

    def checkin(self, session: dict[str, Any], data: CheckIn) -> dict[str, Any]:
        day = self.checkin_day(data.day)
        with self.db.transaction(write=True) as tx:
            tx.execute(CHECKIN_SQL, session_id=session["id"], day=day,
                       **checkin_parameters(dict(data.model_dump(exclude={"day"}, exclude_unset=True), is_sample=0)))
        return self.dashboard(session)

    def get_checkin(self, session: dict[str, Any], day: date | None) -> dict[str, Any] | None:
        day_key = self.checkin_day(day)
        with self.db.transaction() as tx:
            row = tx.one(CHECKIN_SELECT + " WHERE session_id=:sid AND day=:day", sid=session["id"], day=day_key)
        return checkin_record(row) if row else None

    def checkin_day(self, day: date | None) -> str:
        today = self.local_now().date()
        day = day or today
        if not today - timedelta(days=HISTORY_DAYS - 1) <= day <= today:
            raise AppError(422, "VALIDATION_ERROR", "Choose a date in the current check-in window.")
        return day.isoformat()

    def delete_checkin(self, session: dict[str, Any], day: date) -> dict[str, Any]:
        day_key = self.checkin_day(day)
        with self.db.transaction(write=True) as tx:
            tx.execute("DELETE FROM check_ins WHERE session_id=:sid AND day=:day", sid=session["id"], day=day_key)
        return self.dashboard(session)

    def goals(self, session: dict[str, Any], data: Goals) -> dict[str, Any]:
        with self.db.transaction(write=True) as tx:
            tx.execute(GOAL_SQL, session_id=session["id"], week_start=week_start(self.local_now().date()).isoformat(),
                       **data.model_dump())
        return self.dashboard(session)

    def reminder(self, session: dict[str, Any], data: Reminder) -> dict[str, Any]:
        minute = None
        if data.time is not None:
            hour, minutes = map(int, data.time.split(":"))
            minute = 60 * hour + minutes
        with self.db.transaction(write=True) as tx:
            tx.execute("UPDATE demo_sessions SET reminder_minute=:minute WHERE id=:sid",
                       minute=minute, sid=session["id"])
        return self.dashboard(dict(session, reminder_minute=minute))

    def profile_for(self, tx: Transaction, session: dict[str, Any]) -> dict[str, Any]:
        defaults = {"name": PERSONAS[session["persona"]]["name"], "language": "en", "theme": "system",
                    "reminder_enabled": True, "notifications_enabled": False}
        saved = tx.one("""SELECT name, language, theme, reminder_enabled, notifications_enabled
                           FROM profile_settings WHERE session_id=:sid""", sid=session["id"])
        if saved:
            defaults.update(saved, reminder_enabled=bool(saved["reminder_enabled"]),
                            notifications_enabled=bool(saved["notifications_enabled"]))
        return {**defaults, "persona": session["persona"], "expires_at": iso_epoch(session["expires_at"]),
                "timezone": self.settings.timezone}

    def profile(self, session: dict[str, Any]) -> dict[str, Any]:
        with self.db.transaction() as tx:
            return self.profile_for(tx, session)

    def update_profile(self, session: dict[str, Any], data: ProfileUpdate) -> dict[str, Any]:
        fields = data.model_dump(exclude_none=True)
        for name in ("reminder_enabled", "notifications_enabled"):
            if name in fields:
                fields[name] = int(fields[name])
        with self.db.transaction(write=True) as tx:
            tx.execute("""INSERT INTO profile_settings
                (session_id, name, language, theme, reminder_enabled, notifications_enabled)
                VALUES (:sid, COALESCE(:name, :default_name), COALESCE(:language, 'en'), COALESCE(:theme, 'system'),
                        COALESCE(:reminder_enabled, 1), COALESCE(:notifications_enabled, 0))
                ON CONFLICT (session_id) DO UPDATE SET
                    name=COALESCE(:name, profile_settings.name), language=COALESCE(:language, profile_settings.language),
                    theme=COALESCE(:theme, profile_settings.theme),
                    reminder_enabled=COALESCE(:reminder_enabled, profile_settings.reminder_enabled),
                    notifications_enabled=COALESCE(:notifications_enabled, profile_settings.notifications_enabled)""",
                sid=session["id"], default_name=PERSONAS[session["persona"]]["name"],
                **{**dict.fromkeys(("name", "language", "theme", "reminder_enabled", "notifications_enabled")), **fields},
            )
        return self.dashboard(session)

    def custom_goals_for(self, tx: Transaction, sid: str, week: date | None = None) -> list[dict[str, Any]]:
        query = "SELECT id, title, completed, week_start FROM custom_goals WHERE session_id=:sid"
        filters = {"sid": sid}
        if week is not None:
            query += " AND week_start=:week"
            filters["week"] = week.isoformat()
        rows = tx.all(query + " ORDER BY week_start, created_at, id", **filters)
        return [dict(row, completed=bool(row["completed"])) for row in rows]

    def list_goals(self, session: dict[str, Any]) -> list[dict[str, Any]]:
        with self.db.transaction() as tx:
            return self.custom_goals_for(tx, session["id"], week_start(self.local_now().date()))

    def lock_session(self, tx: Transaction, sid: str) -> None:
        if self.db.kind == "postgresql":
            row = tx.one("SELECT id FROM demo_sessions WHERE id=:sid FOR UPDATE", sid=sid)
            if row is None:
                raise AppError(401, "SESSION_REQUIRED", "Start a new demo or resume an active one.")

    def create_goal(self, session: dict[str, Any], title: str) -> dict[str, Any]:
        sid = session["id"]
        now = self.local_now()
        week = week_start(now.date()).isoformat()
        with self.db.transaction(write=True) as tx:
            self.lock_session(tx, sid)
            row = tx.one("SELECT COUNT(*) AS count FROM custom_goals WHERE session_id=:sid AND week_start=:week",
                         sid=sid, week=week)
            if row and row["count"] >= MAX_CUSTOM_ITEMS:
                raise AppError(409, "ITEM_LIMIT", "Remove a goal before adding another.")
            tx.execute("""INSERT INTO custom_goals (id, session_id, week_start, title, completed, created_at)
                          VALUES (:id, :sid, :week, :title, 0, :created)""",
                       id=str(uuid4()), sid=sid, week=week, title=title, created=int(now.timestamp()))
        return self.dashboard(session)

    def update_goal(self, session: dict[str, Any], data: GoalUpdate) -> dict[str, Any]:
        with self.db.transaction(write=True) as tx:
            updated = tx.execute("""UPDATE custom_goals SET title=COALESCE(:title, title), completed=COALESCE(:completed, completed)
                                    WHERE session_id=:sid AND id=:id""", sid=session["id"], id=str(data.id),
                                 title=data.title, completed=int(data.completed) if data.completed is not None else None)
            if not updated.rowcount:
                raise AppError(404, "NOT_FOUND", "This goal is unavailable.")
        return self.dashboard(session)

    def delete_goal(self, session: dict[str, Any], item_id: str) -> dict[str, Any]:
        with self.db.transaction(write=True) as tx:
            deleted = tx.execute("DELETE FROM custom_goals WHERE session_id=:sid AND id=:id", sid=session["id"], id=item_id)
            if not deleted.rowcount:
                raise AppError(404, "NOT_FOUND", "This goal is unavailable.")
        return self.dashboard(session)

    def custom_habits_for(self, tx: Transaction, sid: str, today: date) -> list[dict[str, Any]]:
        rows = tx.all("""SELECT id, title, created_day FROM custom_habits
                         WHERE session_id=:sid ORDER BY created_at, id""", sid=sid)
        completions = tx.all("""SELECT c.habit_id, c.day FROM custom_habit_completions c
                                JOIN custom_habits h ON c.habit_id=h.id
                                WHERE h.session_id=:sid AND c.day<=:today ORDER BY c.day""",
                             sid=sid, today=today.isoformat())
        days_by_habit: dict[str, list[str]] = {}
        for completion in completions:
            days_by_habit.setdefault(completion["habit_id"], []).append(completion["day"])
        result = []
        for row in rows:
            days = days_by_habit.get(row["id"], [])
            result.append(dict(row, days=days, streak=streak(days, today)))
        return result

    def list_habits(self, session: dict[str, Any]) -> list[dict[str, Any]]:
        with self.db.transaction() as tx:
            return self.custom_habits_for(tx, session["id"], self.local_now().date())

    def create_habit(self, session: dict[str, Any], title: str) -> dict[str, Any]:
        sid = session["id"]
        now = self.local_now()
        with self.db.transaction(write=True) as tx:
            self.lock_session(tx, sid)
            row = tx.one("SELECT COUNT(*) AS count FROM custom_habits WHERE session_id=:sid", sid=sid)
            if row and row["count"] >= MAX_CUSTOM_ITEMS:
                raise AppError(409, "ITEM_LIMIT", "Remove a habit before adding another.")
            tx.execute("""INSERT INTO custom_habits (id, session_id, title, created_day, created_at)
                          VALUES (:id, :sid, :title, :day, :created)""",
                       id=str(uuid4()), sid=sid, title=title, day=now.date().isoformat(), created=int(now.timestamp()))
        return self.dashboard(session)

    def update_habit(self, session: dict[str, Any], data: HabitUpdate) -> dict[str, Any]:
        item_id = str(data.id)
        today = self.local_now().date()
        with self.db.transaction(write=True) as tx:
            updated = tx.one("""UPDATE custom_habits SET title=COALESCE(:title, title)
                                WHERE session_id=:sid AND id=:id RETURNING created_day""",
                             sid=session["id"], id=item_id, title=data.title)
            if not updated:
                raise AppError(404, "NOT_FOUND", "This habit is unavailable.")
            if data.day is not None:
                first_day = max(week_start(today), date.fromisoformat(updated["created_day"]))
                if not first_day <= data.day <= today:
                    raise AppError(422, "VALIDATION_ERROR", "Choose an elapsed day since this habit started this week.")
                if data.completed:
                    tx.execute("""INSERT INTO custom_habit_completions (habit_id, day) VALUES (:id, :day)
                                  ON CONFLICT (habit_id, day) DO NOTHING""", id=item_id, day=data.day.isoformat())
                else:
                    tx.execute("DELETE FROM custom_habit_completions WHERE habit_id=:id AND day=:day",
                               id=item_id, day=data.day.isoformat())
        return self.dashboard(session)

    def delete_habit(self, session: dict[str, Any], item_id: str) -> dict[str, Any]:
        with self.db.transaction(write=True) as tx:
            deleted = tx.execute("DELETE FROM custom_habits WHERE session_id=:sid AND id=:id", sid=session["id"], id=item_id)
            if not deleted.rowcount:
                raise AppError(404, "NOT_FOUND", "This habit is unavailable.")
        return self.dashboard(session)

    def insights(self, session: dict[str, Any], period: str) -> dict[str, Any]:
        sid = session["id"]
        today = self.local_now().date()
        start = week_start(today) if period == "week" else today - timedelta(days=int(period) - 1)
        days = (today - start).days + 1
        joined = datetime.fromtimestamp(session["created_at"], self.zone).date()
        first_habit_day = max(joined, start)
        with self.db.transaction() as tx:
            entries = self.checkin_entries(tx, sid, start, today)
            preset = tx.one("""SELECT COUNT(*) AS count, MIN(day) AS earliest FROM habit_completions
                               WHERE session_id=:sid AND day BETWEEN :first AND :last""",
                            sid=sid, first=start.isoformat(), last=today.isoformat())
            habits = self.custom_habits_for(tx, sid, today)
        averages = {}
        for metric in CHECKIN_METRICS:
            values = [row[metric] for row in entries if metric in row]
            averages[metric] = round(sum(values) / len(values), 2) if values else None
        if preset and preset["earliest"]:
            first_habit_day = min(first_habit_day, date.fromisoformat(preset["earliest"]))
        possible = max((today - first_habit_day).days + 1, 0) * len(PRESET_HABITS)
        completed = preset["count"] if preset else 0
        for habit in habits:
            first_day = max(start, date.fromisoformat(habit["created_day"]))
            possible += max((today - first_day).days + 1, 0)
            completed += sum(day >= first_day.isoformat() for day in habit["days"])
        percent = round(completed * 100 / possible) if possible else None
        return {"days": days, "start": start.isoformat(), "end": today.isoformat(), "entries": entries,
                "averages": averages, "habits": {"completed": completed, "possible": possible, "percent": percent}}

    def habit(self, session: dict[str, Any], data: HabitCompletion) -> dict[str, Any]:
        today = self.local_now().date()
        if not week_start(today) <= data.day <= today:
            raise AppError(422, "VALIDATION_ERROR", "Choose an elapsed day in the current week.")
        with self.db.transaction(write=True) as tx:
            params = {"sid": session["id"], "day": data.day.isoformat(), "habit": data.habit}
            if data.completed:
                tx.execute("""INSERT INTO habit_completions (session_id, day, habit) VALUES (:sid, :day, :habit)
                           ON CONFLICT (session_id, day, habit) DO NOTHING""", **params)
            else:
                tx.execute("DELETE FROM habit_completions WHERE session_id=:sid AND day=:day AND habit=:habit", **params)
        return self.dashboard(session)

    def export(self, session: dict[str, Any]) -> dict[str, Any]:
        sid = session["id"]
        today = self.local_now().date()
        with self.db.transaction() as tx:
            rows = tx.all(CHECKIN_SELECT + " WHERE session_id=:sid ORDER BY day", sid=sid)
            goals = tx.all("""SELECT week_start, activity_days, checkin_days FROM weekly_goals
                            WHERE session_id=:sid ORDER BY week_start""", sid=sid)
            habits = tx.all("SELECT day, habit FROM habit_completions WHERE session_id=:sid ORDER BY day, habit",
                            sid=sid)
            profile = self.profile_for(tx, session)
            custom_goals = self.custom_goals_for(tx, sid)
            custom_habits = self.custom_habits_for(tx, sid, today)
        minute = session["reminder_minute"]
        return {"schema_version": 2, "synthetic_only": True, "persona": session["persona"], "profile": profile,
                "timezone": self.settings.timezone, "consent_version": session["consent_version"],
                "created_at": iso_epoch(session["created_at"]),
                "reminder": f"{minute//60:02d}:{minute%60:02d}" if minute is not None else None,
                "entries": [checkin_record(row) for row in rows], "goals": custom_goals,
                "weekly_goals": goals, "habit_completions": habits, "custom_habits": custom_habits}

    def delete(self, session: dict[str, Any]) -> None:
        with self.db.transaction(write=True) as tx:
            tx.execute("DELETE FROM demo_sessions WHERE id=:sid", sid=session["id"])
