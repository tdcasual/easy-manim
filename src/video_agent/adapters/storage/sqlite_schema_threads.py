from __future__ import annotations

import sqlite3

from video_agent.adapters.storage.sqlite_schema_core import ensure_column


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
