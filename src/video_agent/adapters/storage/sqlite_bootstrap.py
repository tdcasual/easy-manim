from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from video_agent.adapters.storage.sqlite_schema import (
    SCHEMA_MIGRATIONS_SQL,
    SCHEMA_MIGRATIONS_TABLE,
    SQLITE_MIGRATIONS,
    SQLiteMigration,
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def bootstrap_command_for_data_dir(data_dir: Path) -> str:
    return f"easy-manim-db-bootstrap --data-dir {Path(data_dir)}"


@dataclass(frozen=True)
class SQLiteBootstrapStatus:
    database_path: Path
    applied_migration_ids: list[str]
    pending_migration_ids: list[str]

    @property
    def is_bootstrapped(self) -> bool:
        return not self.pending_migration_ids


@dataclass(frozen=True)
class SQLiteBootstrapReport:
    database_path: Path
    applied_migration_ids: list[str]
    recorded_migration_ids: list[str]

    @property
    def already_bootstrapped(self) -> bool:
        return not self.applied_migration_ids

    def as_json(self) -> str:
        return json.dumps(
            {
                "database_path": str(self.database_path),
                "applied_migration_ids": self.applied_migration_ids,
                "recorded_migration_ids": self.recorded_migration_ids,
                "already_bootstrapped": self.already_bootstrapped,
            }
        )


class DatabaseBootstrapRequiredError(RuntimeError):
    """Raised when runtime code is started before database bootstrap."""


class SQLiteBootstrapper:
    def __init__(
        self,
        database_path: Path,
        *,
        migrations: tuple[SQLiteMigration, ...] = SQLITE_MIGRATIONS,
    ) -> None:
        self.database_path = Path(database_path)
        self.migrations = migrations

    def bootstrap(self) -> SQLiteBootstrapReport:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        applied_now: list[str] = []
        with _connect(self.database_path) as connection:
            self._ensure_metadata_table(connection)
            applied_before = set(self._load_applied_migration_ids(connection))
            for migration in self.migrations:
                if migration.migration_id in applied_before:
                    continue
                with connection:
                    migration.apply(connection)
                    connection.execute(
                        f"""
                        INSERT INTO {SCHEMA_MIGRATIONS_TABLE} (migration_id, description, applied_at)
                        VALUES (?, ?, ?)
                        """,
                        (migration.migration_id, migration.description, _utcnow_iso()),
                    )
                applied_now.append(migration.migration_id)
            recorded = self._load_applied_migration_ids(connection)
        return SQLiteBootstrapReport(
            database_path=self.database_path,
            applied_migration_ids=applied_now,
            recorded_migration_ids=recorded,
        )

    def status(self) -> SQLiteBootstrapStatus:
        applied: list[str] = []
        if self.database_path.exists():
            with _connect(self.database_path) as connection:
                if self._metadata_table_exists(connection):
                    applied = self._load_applied_migration_ids(connection)
        applied_set = set(applied)
        pending = [migration.migration_id for migration in self.migrations if migration.migration_id not in applied_set]
        return SQLiteBootstrapStatus(
            database_path=self.database_path,
            applied_migration_ids=applied,
            pending_migration_ids=pending,
        )

    def require_bootstrapped(self, *, data_dir: Path) -> SQLiteBootstrapStatus:
        status = self.status()
        if status.is_bootstrapped:
            return status
        command = bootstrap_command_for_data_dir(data_dir)
        raise DatabaseBootstrapRequiredError(
            f"Database at {self.database_path} is not bootstrapped. Run `{command}` before starting easy-manim services."
        )

    def _ensure_metadata_table(self, connection: sqlite3.Connection) -> None:
        connection.execute(SCHEMA_MIGRATIONS_SQL)

    def _load_applied_migration_ids(self, connection: sqlite3.Connection) -> list[str]:
        rows = connection.execute(
            f"SELECT migration_id FROM {SCHEMA_MIGRATIONS_TABLE} ORDER BY migration_id ASC"
        ).fetchall()
        return [row["migration_id"] for row in rows]

    def _metadata_table_exists(self, connection: sqlite3.Connection) -> bool:
        row = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = ?
            """,
            (SCHEMA_MIGRATIONS_TABLE,),
        ).fetchone()
        return row is not None
