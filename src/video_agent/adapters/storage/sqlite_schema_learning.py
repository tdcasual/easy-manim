from __future__ import annotations

import sqlite3

from video_agent.adapters.storage.sqlite_schema_core import ensure_column


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


def apply_agent_learning_normalization(connection: sqlite3.Connection) -> None:
    dedupe_agent_learning_events(connection)
    create_agent_learning_indexes(connection)


def apply_agent_session_token_binding(connection: sqlite3.Connection) -> None:
    ensure_column(connection, "agent_sessions", "token_hash", "TEXT NOT NULL DEFAULT ''")


def apply_strategy_profiles(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS strategy_profiles (
            strategy_id TEXT PRIMARY KEY,
            scope TEXT NOT NULL,
            prompt_cluster TEXT,
            status TEXT NOT NULL,
            params_json TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )


def apply_agent_learning_quality_split(connection: sqlite3.Connection) -> None:
    ensure_column(connection, "agent_learning_events", "quality_passed", "INTEGER")


def apply_session_memory_snapshot_scaffold(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS session_memory_snapshots (
            session_id TEXT PRIMARY KEY,
            agent_id TEXT,
            snapshot_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_session_memory_snapshots_agent_updated_at
        ON session_memory_snapshots (agent_id, updated_at ASC, session_id ASC)
        """
    )
