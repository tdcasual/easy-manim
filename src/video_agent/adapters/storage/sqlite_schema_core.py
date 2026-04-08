from __future__ import annotations

import json
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
    thread_id TEXT,
    iteration_id TEXT,
    result_id TEXT,
    execution_kind TEXT,
    agent_id TEXT,
    session_id TEXT,
    status TEXT NOT NULL,
    phase TEXT NOT NULL,
    prompt TEXT NOT NULL,
    feedback TEXT,
    memory_context_summary TEXT,
    memory_context_digest TEXT,
    task_memory_context_json TEXT,
    selected_memory_ids_json TEXT,
    persistent_memory_context_summary TEXT,
    persistent_memory_context_digest TEXT,
    idempotency_key TEXT UNIQUE,
    current_script_artifact_id TEXT,
    best_result_artifact_id TEXT,
    display_title TEXT,
    title_source TEXT,
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

CREATE TABLE IF NOT EXISTS agent_runtime_definitions (
    agent_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    workspace TEXT NOT NULL,
    agent_dir TEXT NOT NULL,
    tools_allow_json TEXT NOT NULL,
    channels_json TEXT NOT NULL,
    delegate_metadata_json TEXT NOT NULL,
    definition_source TEXT NOT NULL,
    runtime_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_runtime_runs (
    run_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    trigger_kind TEXT NOT NULL,
    status TEXT NOT NULL,
    task_id TEXT,
    thread_id TEXT,
    iteration_id TEXT,
    summary TEXT,
    run_json TEXT NOT NULL,
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
    quality_passed INTEGER,
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
    token_hash TEXT NOT NULL DEFAULT '',
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

CREATE TABLE IF NOT EXISTS session_memory_snapshots (
    session_id TEXT PRIMARY KEY,
    agent_id TEXT,
    snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow_participants (
    root_task_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    role TEXT NOT NULL,
    capabilities_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (root_task_id, agent_id)
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

CREATE TABLE IF NOT EXISTS video_threads (
    thread_id TEXT PRIMARY KEY,
    owner_agent_id TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    current_iteration_id TEXT,
    selected_result_id TEXT,
    origin_prompt TEXT NOT NULL,
    origin_context_summary TEXT,
    thread_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    archived_at TEXT
);

CREATE TABLE IF NOT EXISTS video_iterations (
    iteration_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    parent_iteration_id TEXT,
    goal TEXT NOT NULL,
    requested_action TEXT,
    preserve_working_parts INTEGER,
    status TEXT NOT NULL,
    resolution_state TEXT NOT NULL,
    focus_summary TEXT,
    selected_result_id TEXT,
    source_result_id TEXT,
    initiated_by_turn_id TEXT,
    responsible_role TEXT,
    responsible_agent_id TEXT,
    iteration_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    closed_at TEXT
);

CREATE TABLE IF NOT EXISTS video_turns (
    turn_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    iteration_id TEXT NOT NULL,
    turn_type TEXT NOT NULL,
    speaker_type TEXT NOT NULL,
    speaker_agent_id TEXT,
    speaker_role TEXT,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    visibility TEXT NOT NULL,
    source_run_id TEXT,
    source_task_id TEXT,
    turn_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS video_results (
    result_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    iteration_id TEXT NOT NULL,
    source_task_id TEXT,
    status TEXT NOT NULL,
    video_resource TEXT,
    preview_resources_json TEXT NOT NULL,
    script_resource TEXT,
    validation_report_resource TEXT,
    result_summary TEXT NOT NULL,
    quality_summary TEXT,
    selected INTEGER NOT NULL DEFAULT 0,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS video_thread_participants (
    thread_id TEXT NOT NULL,
    participant_id TEXT NOT NULL,
    participant_type TEXT NOT NULL,
    agent_id TEXT,
    role TEXT NOT NULL,
    display_name TEXT NOT NULL,
    capabilities_json TEXT NOT NULL,
    participant_json TEXT NOT NULL,
    joined_at TEXT NOT NULL,
    left_at TEXT,
    PRIMARY KEY (thread_id, participant_id)
);

CREATE TABLE IF NOT EXISTS video_agent_runs (
    run_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    iteration_id TEXT NOT NULL,
    task_id TEXT,
    agent_id TEXT NOT NULL,
    role TEXT NOT NULL,
    status TEXT NOT NULL,
    phase TEXT,
    input_summary TEXT,
    output_summary TEXT,
    run_json TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    if not rows:
        return
    if any(row["name"] == column_name for row in rows):
        return
    connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def has_table(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def apply_initial_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(INITIAL_SCHEMA_SQL)


def apply_legacy_shape_reconciliation(connection: sqlite3.Connection) -> None:
    ensure_column(connection, "video_tasks", "agent_id", "TEXT")
    ensure_column(connection, "video_tasks", "session_id", "TEXT")
    ensure_column(connection, "video_tasks", "memory_context_summary", "TEXT")
    ensure_column(connection, "video_tasks", "memory_context_digest", "TEXT")
    ensure_column(connection, "agent_profiles", "profile_version", "INTEGER NOT NULL DEFAULT 1")


def apply_task_display_title_fields(connection: sqlite3.Connection) -> None:
    ensure_column(connection, "video_tasks", "display_title", "TEXT")
    ensure_column(connection, "video_tasks", "title_source", "TEXT")


def apply_task_memory_context_projection(connection: sqlite3.Connection) -> None:
    if not has_table(connection, "video_tasks"):
        return

    ensure_column(connection, "video_tasks", "task_memory_context_json", "TEXT")
    ensure_column(connection, "video_tasks", "selected_memory_ids_json", "TEXT")
    ensure_column(connection, "video_tasks", "persistent_memory_context_summary", "TEXT")
    ensure_column(connection, "video_tasks", "persistent_memory_context_digest", "TEXT")

    rows = connection.execute(
        """
        SELECT task_id, task_json
        FROM video_tasks
        """
    ).fetchall()
    for row in rows:
        payload = json.loads(row["task_json"] or "{}")
        task_memory_context = payload.get("task_memory_context")
        selected_memory_ids = payload.get("selected_memory_ids")
        connection.execute(
            """
            UPDATE video_tasks
            SET task_memory_context_json = ?,
                selected_memory_ids_json = ?,
                persistent_memory_context_summary = ?,
                persistent_memory_context_digest = ?
            WHERE task_id = ?
            """,
            (
                json.dumps(task_memory_context or {}, sort_keys=True, separators=(",", ":")),
                json.dumps(selected_memory_ids or [], sort_keys=True, separators=(",", ":")),
                payload.get("persistent_memory_context_summary"),
                payload.get("persistent_memory_context_digest"),
                row["task_id"],
            ),
        )


def apply_task_event_ordering_indexes(connection: sqlite3.Connection) -> None:
    if not has_table(connection, "task_events"):
        return
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_task_events_task_id_id
        ON task_events (task_id, id ASC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_task_events_task_type_id
        ON task_events (task_id, event_type, id ASC)
        """
    )
