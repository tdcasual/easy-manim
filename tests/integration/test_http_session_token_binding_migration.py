from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.application.agent_session_service import AgentSessionService
from video_agent.config import Settings
from video_agent.server.http_api import create_http_api
from tests.support import bootstrapped_settings


LEGACY_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TEXT NOT NULL
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
"""


def test_bootstrap_adds_token_hash_column_and_invalidates_legacy_sessions(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    database_path = data_dir / "video_agent.db"
    plain_session_token = "esm_sess.legacy.deadbeef"
    legacy_session_hash = AgentSessionService.hash_session_token(plain_session_token)

    with sqlite3.connect(database_path) as connection:
        connection.executescript(LEGACY_SCHEMA_SQL)
        connection.execute(
            "INSERT INTO schema_migrations (migration_id, description, applied_at) VALUES (?, ?, ?)",
            ("001_initial_schema", "create the core sqlite schema", "2026-01-01T00:00:00+00:00"),
        )
        connection.execute(
            "INSERT INTO schema_migrations (migration_id, description, applied_at) VALUES (?, ?, ?)",
            ("002_legacy_shape_reconciliation", "reconcile legacy task and profile columns", "2026-01-01T00:00:01+00:00"),
        )
        connection.execute(
            "INSERT INTO schema_migrations (migration_id, description, applied_at) VALUES (?, ?, ?)",
            ("003_agent_learning_normalization", "dedupe learning events and create supporting indexes", "2026-01-01T00:00:02+00:00"),
        )
        connection.execute(
            "INSERT INTO agent_profiles (agent_id, name, status, profile_version, profile_json, policy_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("agent-a", "Agent A", "active", 1, "{}", "{}", "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"),
        )
        connection.execute(
            "INSERT INTO agent_sessions (session_id, session_hash, agent_id, status, created_at, expires_at, last_seen_at, revoked_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "sess-legacy",
                legacy_session_hash,
                "agent-a",
                "active",
                "2026-01-01T00:00:00+00:00",
                "2099-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
                None,
            ),
        )
        connection.commit()

    report = SQLiteBootstrapper(database_path).bootstrap()
    assert "004_agent_session_token_binding" in report.applied_migration_ids

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        cols = connection.execute("PRAGMA table_info(agent_sessions)").fetchall()
        assert any(row["name"] == "token_hash" for row in cols)
        legacy = connection.execute(
            "SELECT token_hash FROM agent_sessions WHERE session_id = ?", ("sess-legacy",)
        ).fetchone()
        assert legacy is not None
        assert legacy["token_hash"] == ""

    settings = bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=database_path,
            artifact_root=data_dir / "tasks",
            run_embedded_worker=False,
            auth_mode="required",
        )
    )
    client = TestClient(create_http_api(settings))

    response = client.get("/api/whoami", headers={"Authorization": "Bearer esm_sess.legacy.deadbeef"})
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_session_token"
