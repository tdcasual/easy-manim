from __future__ import annotations

import sqlite3

from video_agent.adapters.storage.sqlite_schema_core import ensure_column


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
