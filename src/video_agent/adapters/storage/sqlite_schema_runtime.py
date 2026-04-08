from __future__ import annotations

import sqlite3


def apply_agent_runtime_definition_scaffold(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
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
        )
        """
    )
    connection.execute(
        """
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
        )
        """
    )
