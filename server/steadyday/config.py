from dataclasses import dataclass, field
from os import environ
from pathlib import Path
from urllib.parse import quote, urlsplit
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default="sqlite:///./steadyday.sqlite3", repr=False)
    mode: str = "local"
    timezone: str = "Asia/Dhaka"
    session_days: int = 7
    active_session_limit: int = 300
    proxy_key: str = field(default="", repr=False)
    access_code: str = field(default="", repr=False)
    public_demo: bool = False
    app_origin: str = ""
    retrieval_enabled: bool = True
    assets: Path = Path(__file__).resolve().parents[2] / "web/public/steadyday"

    def __post_init__(self) -> None:
        ZoneInfo(self.timezone)
        if self.mode not in {"local", "hosted"}:
            raise ValueError("STEADYDAY_MODE must be local or hosted.")
        if not 1 <= self.session_days <= 30 or not 1 <= self.active_session_limit <= 10000:
            raise ValueError("Invalid session retention or capacity configuration.")
        if self.app_origin:
            url = urlsplit(self.app_origin)
            if url.scheme not in {"http", "https"} or not url.hostname or url.path or url.query or url.fragment or url.username or url.password:
                raise ValueError("APP_ORIGIN must be an origin with no path or credentials.")
        if self.mode == "hosted":
            if not self.database_url.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
                raise ValueError("Hosted mode requires PostgreSQL.")
            if len(self.proxy_key) < 32:
                raise ValueError("Hosted mode requires a strong PROXY_KEY.")
            if not self.public_demo and not 12 <= len(self.access_code) <= 128:
                raise ValueError("Hosted mode requires DEMO_ACCESS_CODE or DEMO_PUBLIC=1.")
            if self.public_demo and self.access_code:
                raise ValueError("Choose either DEMO_PUBLIC=1 or DEMO_ACCESS_CODE.")

    @classmethod
    def from_env(cls) -> "Settings":
        database_url = environ.get("DATABASE_URL")
        if not database_url and (host := environ.get("POSTGRES_HOST")):
            parts = [environ.get(key, "") for key in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB")]
            if not all(parts):
                raise ValueError("POSTGRES_HOST requires POSTGRES_USER, POSTGRES_PASSWORD and POSTGRES_DB.")
            user, password, dbname = (quote(part, safe="") for part in parts)
            database_url = f"postgresql+psycopg://{user}:{password}@{host}:5432/{dbname}"
        return cls(
            database_url=database_url or "sqlite:///./steadyday.sqlite3",
            mode=environ.get("STEADYDAY_MODE", "local"),
            timezone=environ.get("DEMO_TIMEZONE", "Asia/Dhaka"),
            session_days=int(environ.get("DEMO_SESSION_DAYS", "7")),
            active_session_limit=int(environ.get("DEMO_SESSION_LIMIT", "300")),
            proxy_key=environ.get("PROXY_KEY", ""),
            access_code=environ.get("DEMO_ACCESS_CODE", ""),
            public_demo=environ.get("DEMO_PUBLIC", "0") == "1",
            app_origin=environ.get("APP_ORIGIN", ""),
            retrieval_enabled=environ.get("RETRIEVAL_ENABLED", "1") != "0",
        )
