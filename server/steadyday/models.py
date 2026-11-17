from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StringConstraints, model_validator

Persona = Literal["arif", "samir"]
Habit = Literal["screen_break", "wind_down", "reflect"]
Sleep = Annotated[int, Field(strict=True, ge=0, le=1080)]
Activity = Annotated[int, Field(strict=True, ge=0, le=240)]
Energy = Annotated[int, Field(strict=True, ge=1, le=5)]
Stress = Annotated[int, Field(strict=True, ge=0, le=100)]
Hydration = Annotated[int, Field(strict=True, ge=0, le=30)]
GoalDays = Annotated[int, Field(strict=True, ge=1, le=7)]
ClockTime = Annotated[str, StringConstraints(pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
Notes = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Onboard(Payload):
    persona: Persona
    consent: StrictBool
    access_code: Annotated[str, StringConstraints(max_length=128)] = ""


class CheckIn(Payload):
    sleep_minutes: Sleep
    activity_minutes: Activity
    energy: Energy
    day: date | None = None
    mood: Energy | None = None
    stress: Stress | None = None
    hydration: Hydration | None = None
    notes: Notes | None = None


class Goals(Payload):
    activity_days: GoalDays
    checkin_days: GoalDays


class Reminder(Payload):
    time: ClockTime | None


class HabitCompletion(Payload):
    habit: Habit
    day: date
    completed: StrictBool


class ProfileUpdate(Payload):
    name: DisplayName | None = None
    language: Literal["en", "bn"] | None = None
    theme: Literal["system", "light", "dark"] | None = None
    reminder_enabled: StrictBool | None = None
    notifications_enabled: StrictBool | None = None

    @model_validator(mode="after")
    def check_preferences(self):
        if not self.model_dump(exclude_none=True):
            raise ValueError("Supply a display name or preference.")
        return self


class TitledItem(Payload):
    title: Title


class GoalUpdate(Payload):
    id: UUID
    title: Title | None = None
    completed: StrictBool | None = None

    @model_validator(mode="after")
    def check_changes(self):
        if self.title is None and self.completed is None:
            raise ValueError("Supply a title or completion state.")
        return self


class HabitUpdate(GoalUpdate):
    day: date | None = None

    @model_validator(mode="after")
    def check_completion_day(self):
        if (self.completed is None) != (self.day is None):
            raise ValueError("Supply both day and completion state.")
        return self
