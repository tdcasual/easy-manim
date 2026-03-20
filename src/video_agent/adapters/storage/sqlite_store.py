from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from video_agent.application.preference_resolver import resolve_effective_request_config
from video_agent.domain.agent_learning_models import AgentLearningEvent
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.domain.agent_profile_revision_models import AgentProfileRevision
from video_agent.domain.agent_profile_suggestion_models import AgentProfileSuggestion
from video_agent.domain.agent_session_models import AgentSession
from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.domain.models import VideoTask
from video_agent.domain.validation_models import ValidationReport



def _utcnow() -> datetime:
    return datetime.now(timezone.utc)



def _utcnow_iso() -> str:
    return _utcnow().isoformat()


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


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
            self._ensure_column(connection, "agent_profiles", "profile_version", "INTEGER NOT NULL DEFAULT 1")
            self._dedupe_agent_learning_events(connection)
            self._ensure_agent_learning_indexes(connection)

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
            existing = connection.execute(
                """
                SELECT name, status, profile_version, profile_json, policy_json, created_at, updated_at
                FROM agent_profiles
                WHERE agent_id = ?
                """,
                (profile.agent_id,),
            ).fetchone()
            profile_version = profile.profile_version
            created_at = profile.created_at
            if existing is not None:
                profile_changed = (
                    existing["name"] != profile.name
                    or existing["status"] != profile.status
                    or json.loads(existing["profile_json"]) != profile.profile_json
                    or json.loads(existing["policy_json"]) != profile.policy_json
                )
                profile_version = int(existing["profile_version"]) + 1 if profile_changed else int(existing["profile_version"])
                created_at = datetime.fromisoformat(existing["created_at"])
            profile.profile_version = profile_version
            profile.created_at = created_at
            connection.execute(
                """
                INSERT INTO agent_profiles (
                    agent_id, name, status, profile_version, profile_json, policy_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    name = excluded.name,
                    status = excluded.status,
                    profile_version = excluded.profile_version,
                    profile_json = excluded.profile_json,
                    policy_json = excluded.policy_json,
                    updated_at = excluded.updated_at
                """,
                (
                    profile.agent_id,
                    profile.name,
                    profile.status,
                    profile.profile_version,
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
                SELECT agent_id, name, status, profile_version, profile_json, policy_json, created_at, updated_at
                FROM agent_profiles
                WHERE agent_id = ?
                """,
                (agent_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_agent_profile(row)

    def apply_agent_profile_patch(
        self,
        agent_id: str,
        *,
        patch_json: dict[str, Any],
        source: str,
    ) -> tuple[AgentProfile, AgentProfileRevision]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            updated_profile, revision = self._apply_agent_profile_patch_in_connection(
                connection,
                agent_id=agent_id,
                patch_json=patch_json,
                source=source,
            )
            connection.commit()
        return updated_profile, revision

    def apply_agent_profile_suggestion(
        self,
        agent_id: str,
        *,
        suggestion_id: str,
        source: str,
    ) -> tuple[AgentProfile, AgentProfileRevision, AgentProfileSuggestion]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            suggestion_row = connection.execute(
                """
                SELECT suggestion_id, agent_id, patch_json, rationale_json, status, created_at, applied_at
                FROM agent_profile_suggestions
                WHERE suggestion_id = ?
                """,
                (suggestion_id,),
            ).fetchone()
            if suggestion_row is None:
                raise ValueError("profile suggestion not found")

            suggestion = self._row_to_agent_profile_suggestion(suggestion_row)
            if suggestion.agent_id != agent_id:
                raise PermissionError("agent_access_denied")
            if suggestion.status != "pending":
                raise RuntimeError("profile_suggestion_state_conflict")

            updated_profile, revision = self._apply_agent_profile_patch_in_connection(
                connection,
                agent_id=agent_id,
                patch_json=suggestion.patch_json,
                source=source,
            )
            result = connection.execute(
                """
                UPDATE agent_profile_suggestions
                SET status = ?, applied_at = COALESCE(applied_at, ?)
                WHERE suggestion_id = ? AND status = ?
                """,
                (
                    "applied",
                    updated_profile.updated_at.isoformat(),
                    suggestion_id,
                    "pending",
                ),
            )
            if result.rowcount == 0:
                raise RuntimeError("profile_suggestion_state_conflict")

            connection.commit()
        return (
            updated_profile,
            revision,
            suggestion.model_copy(
                update={
                    "status": "applied",
                    "applied_at": suggestion.applied_at or updated_profile.updated_at,
                }
            ),
        )

    def create_agent_profile_revision(self, revision: AgentProfileRevision) -> AgentProfileRevision:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_profile_revisions (
                    revision_id, agent_id, patch_json, source, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    revision.revision_id,
                    revision.agent_id,
                    json.dumps(revision.patch_json),
                    revision.source,
                    revision.created_at.isoformat(),
                ),
            )
        return revision

    def create_agent_learning_event(self, event: AgentLearningEvent) -> AgentLearningEvent:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_learning_events (
                    event_id, agent_id, task_id, session_id, status, issue_codes_json,
                    quality_score, profile_digest, memory_ids_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    agent_id = excluded.agent_id,
                    session_id = excluded.session_id,
                    status = excluded.status,
                    issue_codes_json = excluded.issue_codes_json,
                    quality_score = excluded.quality_score,
                    profile_digest = excluded.profile_digest,
                    memory_ids_json = excluded.memory_ids_json
                """,
                (
                    event.event_id,
                    event.agent_id,
                    event.task_id,
                    event.session_id,
                    event.status,
                    json.dumps(event.issue_codes),
                    event.quality_score,
                    event.profile_digest,
                    json.dumps(event.memory_ids),
                    event.created_at.isoformat(),
                ),
            )
            row = connection.execute(
                """
                SELECT
                    event_id, agent_id, task_id, session_id, status, issue_codes_json,
                    quality_score, profile_digest, memory_ids_json, created_at
                FROM agent_learning_events
                WHERE task_id = ?
                """,
                (event.task_id,),
            ).fetchone()
        if row is None:
            return event
        return self._row_to_agent_learning_event(row)

    def list_agent_learning_events(self, agent_id: str, limit: int = 200) -> list[AgentLearningEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    event_id, agent_id, task_id, session_id, status, issue_codes_json,
                    quality_score, profile_digest, memory_ids_json, created_at
                FROM agent_learning_events
                WHERE agent_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (agent_id, limit),
            ).fetchall()
        return [self._row_to_agent_learning_event(row) for row in rows]

    def create_agent_profile_suggestion(self, suggestion: AgentProfileSuggestion) -> AgentProfileSuggestion:
        patch_json = _canonical_json(suggestion.patch_json)
        rationale_json = _canonical_json(suggestion.rationale_json)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if suggestion.status == "pending":
                pending_rows = connection.execute(
                    """
                    SELECT suggestion_id, agent_id, patch_json, rationale_json, status, created_at, applied_at
                    FROM agent_profile_suggestions
                    WHERE agent_id = ? AND status = ?
                    ORDER BY created_at DESC
                    """,
                    (suggestion.agent_id, "pending"),
                ).fetchall()
                for row in pending_rows:
                    if (
                        _canonical_json(json.loads(row["patch_json"])) == patch_json
                        and _canonical_json(json.loads(row["rationale_json"])) == rationale_json
                    ):
                        return self._row_to_agent_profile_suggestion(row)

            connection.execute(
                """
                INSERT INTO agent_profile_suggestions (
                    suggestion_id, agent_id, patch_json, rationale_json, status, created_at, applied_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    suggestion.suggestion_id,
                    suggestion.agent_id,
                    patch_json,
                    rationale_json,
                    suggestion.status,
                    suggestion.created_at.isoformat(),
                    None if suggestion.applied_at is None else suggestion.applied_at.isoformat(),
                ),
            )
            connection.commit()
        return suggestion

    def get_agent_profile_suggestion(self, suggestion_id: str) -> Optional[AgentProfileSuggestion]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT suggestion_id, agent_id, patch_json, rationale_json, status, created_at, applied_at
                FROM agent_profile_suggestions
                WHERE suggestion_id = ?
                """,
                (suggestion_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_agent_profile_suggestion(row)

    def list_agent_profile_suggestions(self, agent_id: str, limit: int = 50) -> list[AgentProfileSuggestion]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT suggestion_id, agent_id, patch_json, rationale_json, status, created_at, applied_at
                FROM agent_profile_suggestions
                WHERE agent_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (agent_id, limit),
            ).fetchall()
        return [self._row_to_agent_profile_suggestion(row) for row in rows]

    def update_agent_profile_suggestion_status(
        self,
        suggestion_id: str,
        *,
        status: str,
        applied_at: datetime | None = None,
        expected_status: str | None = None,
    ) -> Optional[AgentProfileSuggestion]:
        with self._connect() as connection:
            if expected_status is None:
                result = connection.execute(
                    """
                    UPDATE agent_profile_suggestions
                    SET status = ?, applied_at = COALESCE(applied_at, ?)
                    WHERE suggestion_id = ?
                    """,
                    (
                        status,
                        None if applied_at is None else applied_at.isoformat(),
                        suggestion_id,
                    ),
                )
            else:
                result = connection.execute(
                    """
                    UPDATE agent_profile_suggestions
                    SET status = ?, applied_at = COALESCE(applied_at, ?)
                    WHERE suggestion_id = ? AND status = ?
                    """,
                    (
                        status,
                        None if applied_at is None else applied_at.isoformat(),
                        suggestion_id,
                        expected_status,
                    ),
                )
        if result.rowcount == 0:
            return None
        return self.get_agent_profile_suggestion(suggestion_id)

    def list_agent_profile_revisions(self, agent_id: str, limit: int = 50) -> list[AgentProfileRevision]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT revision_id, agent_id, patch_json, source, created_at
                FROM agent_profile_revisions
                WHERE agent_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (agent_id, limit),
            ).fetchall()
        return [
            AgentProfileRevision(
                revision_id=row["revision_id"],
                agent_id=row["agent_id"],
                patch_json=json.loads(row["patch_json"]),
                source=row["source"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

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

    def create_agent_session(self, session: AgentSession) -> AgentSession:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_sessions (
                    session_id, session_hash, agent_id, status, created_at, expires_at, last_seen_at, revoked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.session_hash,
                    session.agent_id,
                    session.status,
                    session.created_at.isoformat(),
                    session.expires_at.isoformat(),
                    session.last_seen_at.isoformat(),
                    None if session.revoked_at is None else session.revoked_at.isoformat(),
                ),
            )
        return session

    def get_agent_session(self, session_hash: str) -> Optional[AgentSession]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    session_id, session_hash, agent_id, status, created_at, expires_at, last_seen_at, revoked_at
                FROM agent_sessions
                WHERE session_hash = ?
                """,
                (session_hash,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_agent_session(row)

    def get_agent_session_by_id(self, session_id: str) -> Optional[AgentSession]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    session_id, session_hash, agent_id, status, created_at, expires_at, last_seen_at, revoked_at
                FROM agent_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_agent_session(row)

    def touch_agent_session(self, session_hash: str) -> Optional[AgentSession]:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE agent_sessions
                SET last_seen_at = ?
                WHERE session_hash = ?
                """,
                (_utcnow_iso(), session_hash),
            )
        return self.get_agent_session(session_hash)

    def revoke_agent_session(self, session_hash: str) -> bool:
        revoked_at = _utcnow_iso()
        with self._connect() as connection:
            result = connection.execute(
                """
                UPDATE agent_sessions
                SET status = ?, revoked_at = ?
                WHERE session_hash = ?
                """,
                ("revoked", revoked_at, session_hash),
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

    def _dedupe_agent_learning_events(self, connection: sqlite3.Connection) -> None:
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

    def _ensure_agent_learning_indexes(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_learning_events_task_id ON agent_learning_events (task_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_agent_learning_events_agent_created_at ON agent_learning_events (agent_id, created_at DESC)"
        )

    def _apply_agent_profile_patch_in_connection(
        self,
        connection: sqlite3.Connection,
        *,
        agent_id: str,
        patch_json: dict[str, Any],
        source: str,
    ) -> tuple[AgentProfile, AgentProfileRevision]:
        row = connection.execute(
            """
            SELECT agent_id, name, status, profile_version, profile_json, policy_json, created_at, updated_at
            FROM agent_profiles
            WHERE agent_id = ?
            """,
            (agent_id,),
        ).fetchone()
        if row is None:
            raise ValueError("agent profile not found")

        current_profile = self._row_to_agent_profile(row)
        if current_profile.status != "active":
            raise ValueError("inactive agent profile")
        updated_profile_json = resolve_effective_request_config(
            profile_json=current_profile.profile_json,
            request_overrides=patch_json,
        )
        updated_profile = current_profile.model_copy(
            update={
                "profile_json": updated_profile_json,
                "profile_version": (
                    current_profile.profile_version + 1
                    if updated_profile_json != current_profile.profile_json
                    else current_profile.profile_version
                ),
                "updated_at": _utcnow(),
            }
        )
        connection.execute(
            """
            UPDATE agent_profiles
            SET profile_version = ?, profile_json = ?, updated_at = ?
            WHERE agent_id = ?
            """,
            (
                updated_profile.profile_version,
                json.dumps(updated_profile.profile_json),
                updated_profile.updated_at.isoformat(),
                updated_profile.agent_id,
            ),
        )

        revision = AgentProfileRevision(
            agent_id=agent_id,
            patch_json=patch_json,
            source=source,
        )
        connection.execute(
            """
            INSERT INTO agent_profile_revisions (
                revision_id, agent_id, patch_json, source, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                revision.revision_id,
                revision.agent_id,
                json.dumps(revision.patch_json),
                revision.source,
                revision.created_at.isoformat(),
            ),
        )
        return updated_profile, revision

    @staticmethod
    def _row_to_agent_profile(row: sqlite3.Row) -> AgentProfile:
        return AgentProfile(
            agent_id=row["agent_id"],
            name=row["name"],
            status=row["status"],
            profile_version=int(row["profile_version"]),
            profile_json=json.loads(row["profile_json"]),
            policy_json=json.loads(row["policy_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _row_to_agent_learning_event(row: sqlite3.Row) -> AgentLearningEvent:
        return AgentLearningEvent(
            event_id=row["event_id"],
            agent_id=row["agent_id"],
            task_id=row["task_id"],
            session_id=row["session_id"],
            status=row["status"],
            issue_codes=json.loads(row["issue_codes_json"]),
            quality_score=float(row["quality_score"]),
            profile_digest=row["profile_digest"],
            memory_ids=json.loads(row["memory_ids_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_agent_profile_suggestion(row: sqlite3.Row) -> AgentProfileSuggestion:
        return AgentProfileSuggestion(
            suggestion_id=row["suggestion_id"],
            agent_id=row["agent_id"],
            patch_json=json.loads(row["patch_json"]),
            rationale_json=json.loads(row["rationale_json"]),
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            applied_at=None if row["applied_at"] is None else datetime.fromisoformat(row["applied_at"]),
        )

    @staticmethod
    def _row_to_agent_session(row: sqlite3.Row) -> AgentSession:
        return AgentSession(
            session_id=row["session_id"],
            session_hash=row["session_hash"],
            agent_id=row["agent_id"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]),
            last_seen_at=datetime.fromisoformat(row["last_seen_at"]),
            revoked_at=None if row["revoked_at"] is None else datetime.fromisoformat(row["revoked_at"]),
        )
