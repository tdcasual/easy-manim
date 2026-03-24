from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Callable


MigrationAction = Callable[[sqlite3.Connection], None]


@dataclass(frozen=True)
class SQLiteMigration:
    migration_id: str
    description: str
    apply: MigrationAction


SCHEMA_MIGRATIONS_TABLE = "schema_migrations"

SCHEMA_MIGRATIONS_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TEXT NOT NULL
);
"""

INITIAL_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS video_tasks (
    task_id TEXT PRIMARY KEY,
    root_task_id TEXT NOT NULL,
    parent_task_id TEXT,
    agent_id TEXT,
    session_id TEXT,
    status TEXT NOT NULL,
    phase TEXT NOT NULL,
    prompt TEXT NOT NULL,
    feedback TEXT,
    memory_context_summary TEXT,
    memory_context_digest TEXT,
    idempotency_key TEXT UNIQUE,
    current_script_artifact_id TEXT,
    best_result_artifact_id TEXT,
    task_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_profiles (
    agent_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    profile_version INTEGER NOT NULL DEFAULT 1,
    profile_json TEXT NOT NULL,
    policy_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_profile_revisions (
    revision_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    patch_json TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_learning_events (
    event_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    session_id TEXT,
    status TEXT NOT NULL,
    issue_codes_json TEXT NOT NULL,
    quality_score REAL NOT NULL,
    profile_digest TEXT,
    memory_ids_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_profile_suggestions (
    suggestion_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    patch_json TEXT NOT NULL,
    rationale_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    applied_at TEXT
);

CREATE TABLE IF NOT EXISTS agent_tokens (
    token_hash TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    status TEXT NOT NULL,
    scopes_json TEXT NOT NULL,
    override_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_sessions (
    session_id TEXT PRIMARY KEY,
    session_hash TEXT NOT NULL UNIQUE,
    agent_id TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    revoked_at TEXT
);

CREATE TABLE IF NOT EXISTS agent_memories (
    memory_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    source_session_id TEXT NOT NULL,
    status TEXT NOT NULL,
    summary_text TEXT NOT NULL,
    summary_digest TEXT NOT NULL,
    lineage_refs_json TEXT NOT NULL,
    snapshot_json TEXT NOT NULL,
    enhancement_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    disabled_at TEXT
);

CREATE TABLE IF NOT EXISTS task_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_artifacts (
    artifact_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    artifact_kind TEXT NOT NULL,
    path TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_validations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    report_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_leases (
    task_id TEXT PRIMARY KEY,
    worker_id TEXT NOT NULL,
    lease_expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS worker_heartbeats (
    worker_id TEXT PRIMARY KEY,
    last_seen_at TEXT NOT NULL,
    details_json TEXT NOT NULL
);
"""


def ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    if any(row["name"] == column_name for row in rows):
        return
    connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def dedupe_agent_learning_events(connection: sqlite3.Connection) -> None:
    duplicate_rows = connection.execute(
        """
        SELECT task_id
        FROM agent_learning_events
        GROUP BY task_id
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    for duplicate in duplicate_rows:
        task_id = duplicate["task_id"]
        rows = connection.execute(
            """
            SELECT rowid
            FROM agent_learning_events
            WHERE task_id = ?
            ORDER BY created_at DESC, rowid DESC
            """,
            (task_id,),
        ).fetchall()
        if not rows:
            continue
        keep_rowid = rows[0]["rowid"]
        connection.execute(
            "DELETE FROM agent_learning_events WHERE task_id = ? AND rowid != ?",
            (task_id, keep_rowid),
        )


def create_agent_learning_indexes(connection: sqlite3.Connection) -> None:
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_learning_events_task_id ON agent_learning_events (task_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_learning_events_agent_created_at ON agent_learning_events (agent_id, created_at DESC)"
    )


def apply_initial_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(INITIAL_SCHEMA_SQL)


def apply_legacy_shape_reconciliation(connection: sqlite3.Connection) -> None:
    ensure_column(connection, "video_tasks", "agent_id", "TEXT")
    ensure_column(connection, "video_tasks", "session_id", "TEXT")
    ensure_column(connection, "video_tasks", "memory_context_summary", "TEXT")
    ensure_column(connection, "video_tasks", "memory_context_digest", "TEXT")
    ensure_column(connection, "agent_profiles", "profile_version", "INTEGER NOT NULL DEFAULT 1")


def apply_agent_learning_normalization(connection: sqlite3.Connection) -> None:
    dedupe_agent_learning_events(connection)
    create_agent_learning_indexes(connection)


SQLITE_MIGRATIONS: tuple[SQLiteMigration, ...] = (
    SQLiteMigration(
        migration_id="001_initial_schema",
        description="create the core sqlite schema",
        apply=apply_initial_schema,
    ),
    SQLiteMigration(
        migration_id="002_legacy_shape_reconciliation",
        description="reconcile legacy task and profile columns",
        apply=apply_legacy_shape_reconciliation,
    ),
    SQLiteMigration(
        migration_id="003_agent_learning_normalization",
        description="dedupe learning events and create supporting indexes",
        apply=apply_agent_learning_normalization,
    ),
)
