CREATE TABLE IF NOT EXISTS demo_sessions (
    id VARCHAR(36) PRIMARY KEY,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    persona VARCHAR(12) NOT NULL CHECK (persona IN ('arif', 'samir')),
    created_at BIGINT NOT NULL,
    expires_at BIGINT NOT NULL CHECK (expires_at > created_at),
    consent_version INTEGER NOT NULL CHECK (consent_version > 0),
    reminder_minute INTEGER CHECK (reminder_minute BETWEEN 0 AND 1439)
);

CREATE INDEX IF NOT EXISTS ix_demo_expiry ON demo_sessions (expires_at);

CREATE TABLE IF NOT EXISTS check_ins (
    session_id VARCHAR(36) NOT NULL REFERENCES demo_sessions (id) ON DELETE CASCADE,
    day VARCHAR(10) NOT NULL,
    sleep_minutes INTEGER NOT NULL CHECK (sleep_minutes BETWEEN 0 AND 1080),
    activity_minutes INTEGER NOT NULL CHECK (activity_minutes BETWEEN 0 AND 240),
    energy INTEGER NOT NULL CHECK (energy BETWEEN 1 AND 5),
    is_sample INTEGER NOT NULL CHECK (is_sample IN (0, 1)),
    PRIMARY KEY (session_id, day)
);

CREATE TABLE IF NOT EXISTS weekly_goals (
    session_id VARCHAR(36) NOT NULL REFERENCES demo_sessions (id) ON DELETE CASCADE,
    week_start VARCHAR(10) NOT NULL,
    activity_days INTEGER NOT NULL CHECK (activity_days BETWEEN 1 AND 7),
    checkin_days INTEGER NOT NULL CHECK (checkin_days BETWEEN 1 AND 7),
    PRIMARY KEY (session_id, week_start)
);

CREATE TABLE IF NOT EXISTS habit_completions (
    session_id VARCHAR(36) NOT NULL REFERENCES demo_sessions (id) ON DELETE CASCADE,
    day VARCHAR(10) NOT NULL,
    habit VARCHAR(16) NOT NULL CHECK (habit IN ('screen_break', 'wind_down', 'reflect')),
    PRIMARY KEY (session_id, day, habit)
);

CREATE TABLE IF NOT EXISTS profile_settings (
    session_id VARCHAR(36) PRIMARY KEY REFERENCES demo_sessions (id) ON DELETE CASCADE,
    name VARCHAR(60) NOT NULL,
    language VARCHAR(2) NOT NULL CHECK (language IN ('en', 'bn')),
    theme VARCHAR(6) NOT NULL CHECK (theme IN ('system', 'light', 'dark')),
    reminder_enabled INTEGER NOT NULL CHECK (reminder_enabled IN (0, 1)),
    notifications_enabled INTEGER NOT NULL CHECK (notifications_enabled IN (0, 1))
);

CREATE TABLE IF NOT EXISTS custom_goals (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES demo_sessions (id) ON DELETE CASCADE,
    week_start VARCHAR(10) NOT NULL,
    title VARCHAR(80) NOT NULL,
    completed INTEGER NOT NULL CHECK (completed IN (0, 1)),
    created_at BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_custom_goals_session_week ON custom_goals (session_id, week_start);

CREATE TABLE IF NOT EXISTS custom_habits (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES demo_sessions (id) ON DELETE CASCADE,
    title VARCHAR(80) NOT NULL,
    created_day VARCHAR(10) NOT NULL,
    created_at BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_custom_habits_session ON custom_habits (session_id);

CREATE TABLE IF NOT EXISTS custom_habit_completions (
    habit_id VARCHAR(36) NOT NULL REFERENCES custom_habits (id) ON DELETE CASCADE,
    day VARCHAR(10) NOT NULL,
    PRIMARY KEY (habit_id, day)
);
