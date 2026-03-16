from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.domain.models import VideoTask
from video_agent.domain.validation_models import ValidationReport



def _utcnow() -> datetime:
    return datetime.now(timezone.utc)



def _utcnow_iso() -> str:
    return _utcnow().isoformat()


class SQLiteTaskStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            schema_path = Path(__file__).with_name("schema.sql")
            connection.executescript(schema_path.read_text())
            self._ensure_column(connection, "video_tasks", "agent_id", "TEXT")
            self._ensure_column(connection, "video_tasks", "session_id", "TEXT")
            self._ensure_column(connection, "video_tasks", "memory_context_summary", "TEXT")
            self._ensure_column(connection, "video_tasks", "memory_context_digest", "TEXT")

    def create_task(self, task: VideoTask, idempotency_key: Optional[str] = None) -> VideoTask:
        with self._connect() as connection:
            if idempotency_key:
                existing = connection.execute(
                    "SELECT task_json FROM video_tasks WHERE idempotency_key = ?",
                    (idempotency_key,),
                ).fetchone()
                if existing is not None:
                    return VideoTask.model_validate_json(existing["task_json"])

            connection.execute(
                """
                INSERT INTO video_tasks (
                    task_id, root_task_id, parent_task_id, agent_id, session_id, status, phase, prompt, feedback,
                    memory_context_summary, memory_context_digest, idempotency_key,
                    current_script_artifact_id, best_result_artifact_id, task_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.task_id,
                    task.root_task_id,
                    task.parent_task_id,
                    task.agent_id,
                    task.session_id,
                    task.status.value,
                    task.phase.value,
                    task.prompt,
                    task.feedback,
                    task.memory_context_summary,
                    task.memory_context_digest,
                    idempotency_key,
                    task.current_script_artifact_id,
                    task.best_result_artifact_id,
                    task.model_dump_json(),
                    task.created_at.isoformat(),
                    task.updated_at.isoformat(),
                ),
            )
        return task

    def get_task(self, task_id: str) -> Optional[VideoTask]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT task_json FROM video_tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        return VideoTask.model_validate_json(row["task_json"])

    def update_task(self, task: VideoTask) -> None:
        task.updated_at = _utcnow()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE video_tasks
                SET root_task_id = ?, parent_task_id = ?, agent_id = ?, session_id = ?, status = ?, phase = ?, prompt = ?,
                    feedback = ?, memory_context_summary = ?, memory_context_digest = ?, current_script_artifact_id = ?,
                    best_result_artifact_id = ?, task_json = ?, updated_at = ?
                WHERE task_id = ?
                """,
                (
                    task.root_task_id,
                    task.parent_task_id,
                    task.agent_id,
                    task.session_id,
                    task.status.value,
                    task.phase.value,
                    task.prompt,
                    task.feedback,
                    task.memory_context_summary,
                    task.memory_context_digest,
                    task.current_script_artifact_id,
                    task.best_result_artifact_id,
                    task.model_dump_json(),
                    task.updated_at.isoformat(),
                    task.task_id,
                ),
            )

    def upsert_agent_profile(self, profile: AgentProfile) -> None:
        profile.updated_at = _utcnow()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_profiles (
                    agent_id, name, status, profile_json, policy_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    name = excluded.name,
                    status = excluded.status,
                    profile_json = excluded.profile_json,
                    policy_json = excluded.policy_json,
                    updated_at = excluded.updated_at
                """,
                (
                    profile.agent_id,
                    profile.name,
                    profile.status,
                    json.dumps(profile.profile_json),
                    json.dumps(profile.policy_json),
                    profile.created_at.isoformat(),
                    profile.updated_at.isoformat(),
                ),
            )

    def get_agent_profile(self, agent_id: str) -> Optional[AgentProfile]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT agent_id, name, status, profile_json, policy_json, created_at, updated_at
                FROM agent_profiles
                WHERE agent_id = ?
                """,
                (agent_id,),
            ).fetchone()
        if row is None:
            return None
        return AgentProfile(
            agent_id=row["agent_id"],
            name=row["name"],
            status=row["status"],
            profile_json=json.loads(row["profile_json"]),
            policy_json=json.loads(row["policy_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def issue_agent_token(self, token: AgentToken) -> None:
        token.updated_at = _utcnow()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_tokens (
                    token_hash, agent_id, status, scopes_json, override_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(token_hash) DO UPDATE SET
                    agent_id = excluded.agent_id,
                    status = excluded.status,
                    scopes_json = excluded.scopes_json,
                    override_json = excluded.override_json,
                    updated_at = excluded.updated_at
                """,
                (
                    token.token_hash,
                    token.agent_id,
                    token.status,
                    json.dumps(token.scopes_json),
                    json.dumps(token.override_json),
                    token.created_at.isoformat(),
                    token.updated_at.isoformat(),
                ),
            )

    def get_agent_token(self, token_hash: str) -> Optional[AgentToken]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT token_hash, agent_id, status, scopes_json, override_json, created_at, updated_at
                FROM agent_tokens
                WHERE token_hash = ?
                """,
                (token_hash,),
            ).fetchone()
        if row is None:
            return None
        return AgentToken(
            token_hash=row["token_hash"],
            agent_id=row["agent_id"],
            status=row["status"],
            scopes_json=json.loads(row["scopes_json"]),
            override_json=json.loads(row["override_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def list_agent_tokens(self, agent_id: str) -> list[AgentToken]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT token_hash, agent_id, status, scopes_json, override_json, created_at, updated_at
                FROM agent_tokens
                WHERE agent_id = ?
                ORDER BY created_at ASC
                """,
                (agent_id,),
            ).fetchall()
        return [
            AgentToken(
                token_hash=row["token_hash"],
                agent_id=row["agent_id"],
                status=row["status"],
                scopes_json=json.loads(row["scopes_json"]),
                override_json=json.loads(row["override_json"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in rows
        ]

    def disable_agent_token(self, token_hash: str) -> bool:
        with self._connect() as connection:
            result = connection.execute(
                """
                UPDATE agent_tokens
                SET status = ?, updated_at = ?
                WHERE token_hash = ?
                """,
                ("disabled", _utcnow_iso(), token_hash),
            )
        return result.rowcount > 0

    def create_agent_memory(self, record: AgentMemoryRecord) -> AgentMemoryRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_memories (
                    memory_id, agent_id, source_session_id, status, summary_text, summary_digest,
                    lineage_refs_json, snapshot_json, enhancement_json, created_at, disabled_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.memory_id,
                    record.agent_id,
                    record.source_session_id,
                    record.status,
                    record.summary_text,
                    record.summary_digest,
                    json.dumps(record.lineage_refs),
                    json.dumps(record.snapshot),
                    json.dumps(record.enhancement),
                    record.created_at.isoformat(),
                    None if record.disabled_at is None else record.disabled_at.isoformat(),
                ),
            )
        return record

    def get_agent_memory(self, memory_id: str) -> Optional[AgentMemoryRecord]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    memory_id, agent_id, source_session_id, status, summary_text, summary_digest,
                    lineage_refs_json, snapshot_json, enhancement_json, created_at, disabled_at
                FROM agent_memories
                WHERE memory_id = ?
                """,
                (memory_id,),
            ).fetchone()
        if row is None:
            return None
        return AgentMemoryRecord(
            memory_id=row["memory_id"],
            agent_id=row["agent_id"],
            source_session_id=row["source_session_id"],
            status=row["status"],
            summary_text=row["summary_text"],
            summary_digest=row["summary_digest"],
            lineage_refs=json.loads(row["lineage_refs_json"]),
            snapshot=json.loads(row["snapshot_json"]),
            enhancement=json.loads(row["enhancement_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            disabled_at=None if row["disabled_at"] is None else datetime.fromisoformat(row["disabled_at"]),
        )

    def list_agent_memories(self, agent_id: str, include_disabled: bool = False) -> list[AgentMemoryRecord]:
        query = """
            SELECT
                memory_id, agent_id, source_session_id, status, summary_text, summary_digest,
                lineage_refs_json, snapshot_json, enhancement_json, created_at, disabled_at
            FROM agent_memories
            WHERE agent_id = ?
        """
        params: list[Any] = [agent_id]
        if not include_disabled:
            query += " AND status = ?"
            params.append("active")
        query += " ORDER BY created_at ASC"
        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [
            AgentMemoryRecord(
                memory_id=row["memory_id"],
                agent_id=row["agent_id"],
                source_session_id=row["source_session_id"],
                status=row["status"],
                summary_text=row["summary_text"],
                summary_digest=row["summary_digest"],
                lineage_refs=json.loads(row["lineage_refs_json"]),
                snapshot=json.loads(row["snapshot_json"]),
                enhancement=json.loads(row["enhancement_json"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                disabled_at=None if row["disabled_at"] is None else datetime.fromisoformat(row["disabled_at"]),
            )
            for row in rows
        ]

    def disable_agent_memory(self, memory_id: str) -> bool:
        disabled_at = _utcnow_iso()
        with self._connect() as connection:
            result = connection.execute(
                """
                UPDATE agent_memories
                SET status = ?, disabled_at = ?
                WHERE memory_id = ?
                """,
                ("disabled", disabled_at, memory_id),
            )
        return result.rowcount > 0

    def append_event(self, task_id: str, event_type: str, payload: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO task_events (task_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?)",
                (task_id, event_type, json.dumps(payload), _utcnow_iso()),
            )

    def register_artifact(
        self,
        task_id: str,
        artifact_kind: str,
        path: Path,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        artifact_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO task_artifacts (artifact_id, task_id, artifact_kind, path, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (artifact_id, task_id, artifact_kind, str(path), json.dumps(metadata or {}), _utcnow_iso()),
            )
        return artifact_id

    def list_artifacts(self, task_id: str, artifact_kind: Optional[str] = None) -> list[dict[str, Any]]:
        query = "SELECT artifact_id, task_id, artifact_kind, path, metadata_json, created_at FROM task_artifacts WHERE task_id = ?"
        params: list[Any] = [task_id]
        if artifact_kind is not None:
            query += " AND artifact_kind = ?"
            params.append(artifact_kind)
        query += " ORDER BY created_at ASC"
        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [
            {
                "artifact_id": row["artifact_id"],
                "task_id": row["task_id"],
                "artifact_kind": row["artifact_kind"],
                "path": row["path"],
                "metadata": json.loads(row["metadata_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def list_tasks(
        self,
        limit: int = 50,
        status: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT task_id, status, phase, prompt, created_at, updated_at FROM video_tasks"
        params: list[Any] = []
        clauses: list[str] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if agent_id is not None:
            clauses.append("agent_id = ?")
            params.append(agent_id)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [
            {
                "task_id": row["task_id"],
                "status": row["status"],
                "phase": row["phase"],
                "prompt": row["prompt"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def count_tasks(self, statuses: list[str]) -> int:
        if not statuses:
            return 0
        placeholders = ", ".join("?" for _ in statuses)
        query = f"SELECT COUNT(*) AS task_count FROM video_tasks WHERE status IN ({placeholders})"
        with self._connect() as connection:
            row = connection.execute(query, tuple(statuses)).fetchone()
        return int(row["task_count"])

    def count_lineage_tasks(self, root_task_id: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS task_count FROM video_tasks WHERE root_task_id = ?",
                (root_task_id,),
            ).fetchone()
        return int(row["task_count"])

    def list_events(self, task_id: str, limit: int = 200) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_type, payload_json, created_at
                FROM task_events
                WHERE task_id = ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (task_id, limit),
            ).fetchall()
        return [
            {
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def record_validation(self, task_id: str, report: ValidationReport) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO task_validations (task_id, report_json, created_at) VALUES (?, ?, ?)",
                (task_id, report.model_dump_json(), _utcnow_iso()),
            )

    def get_latest_validation(self, task_id: str) -> Optional[ValidationReport]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT report_json FROM task_validations WHERE task_id = ? ORDER BY id DESC LIMIT 1",
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        return ValidationReport.model_validate_json(row["report_json"])

    def claim_next_task(self, worker_id: str, lease_seconds: int) -> Optional[VideoTask]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            now_iso = _utcnow_iso()
            row = connection.execute(
                """
                SELECT t.task_id
                FROM video_tasks AS t
                LEFT JOIN task_leases AS l ON l.task_id = t.task_id
                WHERE t.status IN ('queued', 'revising')
                  AND (l.task_id IS NULL OR l.lease_expires_at <= ?)
                ORDER BY t.created_at ASC
                LIMIT 1
                """,
                (now_iso,),
            ).fetchone()
            if row is None:
                connection.commit()
                return None

            expires_at = (_utcnow() + timedelta(seconds=lease_seconds)).isoformat()
            connection.execute(
                """
                INSERT INTO task_leases (task_id, worker_id, lease_expires_at)
                VALUES (?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    worker_id = excluded.worker_id,
                    lease_expires_at = excluded.lease_expires_at
                """,
                (row["task_id"], worker_id, expires_at),
            )
            connection.commit()
        return self.get_task(row["task_id"])

    def renew_lease(self, task_id: str, worker_id: str, lease_seconds: int) -> None:
        expires_at = (_utcnow() + timedelta(seconds=lease_seconds)).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE task_leases
                SET lease_expires_at = ?
                WHERE task_id = ? AND worker_id = ?
                """,
                (expires_at, task_id, worker_id),
            )

    def requeue_stale_tasks(self, recovery_grace_seconds: int = 0) -> int:
        stale_before = (_utcnow() - timedelta(seconds=recovery_grace_seconds)).isoformat()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT t.task_json
                FROM video_tasks AS t
                LEFT JOIN task_leases AS l ON l.task_id = t.task_id
                WHERE t.status = 'running'
                  AND (l.task_id IS NULL OR l.lease_expires_at <= ?)
                """,
                (stale_before,),
            ).fetchall()

        count = 0
        for row in rows:
            task = VideoTask.model_validate_json(row["task_json"])
            task.status = TaskStatus.QUEUED
            task.phase = TaskPhase.QUEUED
            self.update_task(task)
            count += 1
        return count

    def release_lease(self, task_id: str, worker_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM task_leases WHERE task_id = ? AND worker_id = ?",
                (task_id, worker_id),
            )

    def record_worker_heartbeat(self, worker_id: str, details: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO worker_heartbeats (worker_id, last_seen_at, details_json)
                VALUES (?, ?, ?)
                ON CONFLICT(worker_id) DO UPDATE SET
                    last_seen_at = excluded.last_seen_at,
                    details_json = excluded.details_json
                """,
                (worker_id, _utcnow_iso(), json.dumps(details)),
            )

    def list_cleanup_candidates(self, statuses: list[str], older_than_iso: str, limit: int) -> list[dict[str, Any]]:
        placeholders = ", ".join("?" for _ in statuses)
        query = (
            f"SELECT task_id, status, phase, created_at, updated_at FROM video_tasks "
            f"WHERE status IN ({placeholders}) AND updated_at <= ? ORDER BY updated_at ASC LIMIT ?"
        )
        params = [*statuses, older_than_iso, limit]
        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [
            {
                "task_id": row["task_id"],
                "status": row["status"],
                "phase": row["phase"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def delete_task(self, task_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM task_events WHERE task_id = ?", (task_id,))
            connection.execute("DELETE FROM task_artifacts WHERE task_id = ?", (task_id,))
            connection.execute("DELETE FROM task_validations WHERE task_id = ?", (task_id,))
            connection.execute("DELETE FROM task_leases WHERE task_id = ?", (task_id,))
            connection.execute("DELETE FROM video_tasks WHERE task_id = ?", (task_id,))

    def list_worker_heartbeats(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT worker_id, last_seen_at, details_json FROM worker_heartbeats ORDER BY worker_id ASC"
            ).fetchall()
        return [
            {
                "worker_id": row["worker_id"],
                "last_seen_at": row["last_seen_at"],
                "details": json.loads(row["details_json"]),
            }
            for row in rows
        ]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_column(self, connection: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
        rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        if any(row["name"] == column_name for row in rows):
            return
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")
