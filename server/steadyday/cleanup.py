"""Operator-run expiry cleanup. The dashboard never reads expired sessions."""
from .config import Settings
from .db import Database
from .service import DemoService


def main() -> None:
    settings = Settings.from_env()
    db = Database(settings.database_url)
    try:
        db.init()
        print(f"Purged {DemoService(settings, db).purge_expired()} expired synthetic sessions.")
    finally:
        db.dispose()


if __name__ == "__main__":
    main()
