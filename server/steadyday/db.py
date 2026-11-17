"""Common, parameterised SQL for SQLite and PostgreSQL via SQLAlchemy Core."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Any, Iterator

CHECKIN_COLUMNS = {
    "mood": "INTEGER CHECK (mood BETWEEN 1 AND 5)",
    "stress": "INTEGER CHECK (stress BETWEEN 0 AND 100)",
    "hydration": "INTEGER CHECK (hydration BETWEEN 0 AND 30)",
    "notes": "VARCHAR(500)",
}


class StoreUnavailable(RuntimeError):
    pass


class Transaction:
    def __init__(self, connection: Any, sql_text: Any = None):
        self.connection = connection
        self.sql_text = sql_text

    def execute(self, statement: str, **params: Any):
        return self.connection.execute(
            self.sql_text(statement) if self.sql_text is not None else statement,
            params,
        )

    def one(self, statement: str, **params: Any) -> dict[str, Any] | None:
        result = self.execute(statement, **params)
        row = result.mappings().first() if self.sql_text is not None else result.fetchone()
        return dict(row) if row is not None else None

    def all(self, statement: str, **params: Any) -> list[dict[str, Any]]:
        result = self.execute(statement, **params)
        rows = result.mappings().all() if self.sql_text is not None else result.fetchall()
        return [dict(row) for row in rows]


class Database:
    def __init__(self, url: str):
        self.engine = None
        self.sql_text = None
        if url.startswith("sqlite:///"):
            self.kind = "sqlite"
            target = url.removeprefix("sqlite:///")
            if target in {"", ":memory:"}:
                raise ValueError("Use a SQLite file for persistent local sessions.")
            self.path = Path(target).resolve()
        elif url.startswith(("postgresql://", "postgres://", "postgresql+psycopg://")):
            from sqlalchemy import create_engine, text
            from sqlalchemy.exc import SQLAlchemyError
            self.kind = "postgresql"
            dsn = "postgresql+psycopg://" + url.split("://", 1)[1]
            self.engine = create_engine(
                dsn, pool_pre_ping=True, pool_size=4, max_overflow=2,
                pool_timeout=5, pool_recycle=300, hide_parameters=True,
                connect_args={"connect_timeout": 5},
            )
            self.sql_text, self.sql_error = text, SQLAlchemyError
        else:
            raise ValueError("Use a SQLite or PostgreSQL DATABASE_URL.")

    @contextmanager
    def transaction(self, *, write: bool = False) -> Iterator[Transaction]:
        if self.engine is not None:
            try:
                with self.engine.begin() as connection:
                    yield Transaction(connection, self.sql_text)
            except self.sql_error as error:
                raise StoreUnavailable("Database operation failed.") from error
            return
        connection = None
        try:
            connection = sqlite3.connect(self.path, timeout=5)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield Transaction(connection)
            connection.commit()
        except sqlite3.Error as error:
            if connection is not None:
                connection.rollback()
            raise StoreUnavailable("Database operation failed.") from error
        except BaseException:
            if connection is not None:
                connection.rollback()
            raise
        finally:
            if connection is not None:
                connection.close()

    def init(self) -> None:
        if self.kind == "sqlite":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction(write=True) as tx:
            if self.kind == "postgresql":
                tx.execute("SELECT pg_advisory_xact_lock(843101)")
            for stmt in Path(__file__).with_name("schema.sql").read_text().split(";"):
                if stmt.strip():
                    tx.execute(stmt)
            self.migrate_checkins(tx)

    def migrate_checkins(self, tx: Transaction) -> None:
        if self.kind == "postgresql":
            columns = tx.all("""SELECT attname AS name FROM pg_attribute
                                WHERE attrelid=to_regclass('check_ins') AND attnum>0 AND NOT attisdropped""")
        else:
            columns = tx.all("PRAGMA table_info(check_ins)")
        existing = {column["name"] for column in columns}
        for name, definition in CHECKIN_COLUMNS.items():
            if name not in existing:
                tx.execute(f"ALTER TABLE check_ins ADD COLUMN {name} {definition}")

    def healthy(self) -> bool:
        try:
            with self.transaction() as tx:
                return tx.one("SELECT 1 AS ok") == {"ok": 1}
        except StoreUnavailable:
            return False

    def dispose(self) -> None:
        if self.engine is not None:
            self.engine.dispose()
