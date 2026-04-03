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


def apply_agent_session_token_binding(connection: sqlite3.Connection) -> None:
    ensure_column(connection, "agent_sessions", "token_hash", "TEXT NOT NULL DEFAULT ''")


def apply_task_display_title_fields(connection: sqlite3.Connection) -> None:
    ensure_column(connection, "video_tasks", "display_title", "TEXT")
    ensure_column(connection, "video_tasks", "title_source", "TEXT")


def apply_task_reliability_fields(connection: sqlite3.Connection) -> None:
    ensure_column(connection, "video_tasks", "risk_level", "TEXT")
    ensure_column(connection, "video_tasks", "generation_mode", "TEXT")
    ensure_column(connection, "video_tasks", "strategy_profile_id", "TEXT")
    ensure_column(connection, "video_tasks", "scene_spec_id", "TEXT")
    ensure_column(connection, "video_tasks", "quality_gate_status", "TEXT")
    ensure_column(connection, "video_tasks", "accepted_as_best", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(connection, "video_tasks", "accepted_version_rank", "INTEGER")


def apply_task_quality_scorecards(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS task_quality_scores (
            task_id TEXT PRIMARY KEY,
            scorecard_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )


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


def apply_delivery_case_scaffold(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS delivery_cases (
            case_id TEXT PRIMARY KEY,
            root_task_id TEXT NOT NULL,
            active_task_id TEXT,
            selected_task_id TEXT,
            selected_branch_id TEXT,
            status TEXT NOT NULL,
            delivery_status TEXT NOT NULL,
            completion_mode TEXT,
            stop_reason TEXT,
            case_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_runs (
            run_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            root_task_id TEXT NOT NULL,
            task_id TEXT,
            role TEXT NOT NULL,
            status TEXT NOT NULL,
            phase TEXT,
            summary TEXT,
            run_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_delivery_cases_root_task_id ON delivery_cases (root_task_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_runs_case_created_at ON agent_runs (case_id, created_at ASC)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_runs_case_role_created_at ON agent_runs (case_id, role, created_at ASC)"
    )


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


def apply_workflow_participant_scaffold(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS workflow_participants (
            root_task_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            role TEXT NOT NULL,
            capabilities_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (root_task_id, agent_id)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_workflow_participants_root_role
        ON workflow_participants (root_task_id, role, agent_id)
        """
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


def apply_video_thread_runtime_scaffold(connection: sqlite3.Connection) -> None:
    ensure_column(connection, "video_tasks", "thread_id", "TEXT")
    ensure_column(connection, "video_tasks", "iteration_id", "TEXT")
    ensure_column(connection, "video_tasks", "result_id", "TEXT")
    ensure_column(connection, "video_tasks", "execution_kind", "TEXT")
    connection.execute(
        """
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
        )
        """
    )
    connection.execute(
        """
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
        )
        """
    )
    connection.execute(
        """
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
        )
        """
    )
    connection.execute(
        """
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
        )
        """
    )
    connection.execute(
        """
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
        )
        """
    )
    connection.execute(
        """
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
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_video_iterations_thread_created_at
        ON video_iterations (thread_id, created_at ASC, iteration_id ASC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_video_turns_iteration_created_at
        ON video_turns (iteration_id, created_at ASC, turn_id ASC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_video_results_iteration_created_at
        ON video_results (iteration_id, created_at ASC, result_id ASC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_video_agent_runs_iteration_created_at
        ON video_agent_runs (iteration_id, created_at ASC, run_id ASC)
        """
    )


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
    SQLiteMigration(
        migration_id="004_agent_session_token_binding",
        description="bind agent sessions to the issuing token hash",
        apply=apply_agent_session_token_binding,
    ),
    SQLiteMigration(
        migration_id="005_task_display_title_fields",
        description="persist display titles and sources for tasks",
        apply=apply_task_display_title_fields,
    ),
    SQLiteMigration(
        migration_id="006_task_reliability_fields",
        description="persist reliability metadata for tasks",
        apply=apply_task_reliability_fields,
    ),
    SQLiteMigration(
        migration_id="007_task_quality_scorecards",
        description="create a table for task quality scorecards",
        apply=apply_task_quality_scorecards,
    ),
    SQLiteMigration(
        migration_id="008_strategy_profiles",
        description="create a table for strategy profiles",
        apply=apply_strategy_profiles,
    ),
    SQLiteMigration(
        migration_id="009_agent_learning_quality_split",
        description="persist quality-passed flags for agent learning events",
        apply=apply_agent_learning_quality_split,
    ),
    SQLiteMigration(
        migration_id="010_delivery_case_scaffold",
        description="persist delivery cases and agent runs for native orchestration scaffolding",
        apply=apply_delivery_case_scaffold,
    ),
    SQLiteMigration(
        migration_id="011_session_memory_snapshot_scaffold",
        description="persist session memory snapshots for restart recovery",
        apply=apply_session_memory_snapshot_scaffold,
    ),
    SQLiteMigration(
        migration_id="012_workflow_participant_scaffold",
        description="persist workflow participants for collaboration access control",
        apply=apply_workflow_participant_scaffold,
    ),
    SQLiteMigration(
        migration_id="013_task_event_ordering_indexes",
        description="index task events for ordered discussion thread loading",
        apply=apply_task_event_ordering_indexes,
    ),
    SQLiteMigration(
        migration_id="014_video_thread_runtime_scaffold",
        description="persist video thread runtime entities and task bindings",
        apply=apply_video_thread_runtime_scaffold,
    ),
)
