from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from video_agent.adapters.storage.sqlite_agent_runtime_definition_store import SQLiteAgentRuntimeDefinitionStoreMixin
from video_agent.adapters.storage.sqlite_agent_profile_store import SQLiteAgentProfileStoreMixin
from video_agent.adapters.storage.sqlite_agent_runtime_store import SQLiteAgentRuntimeStoreMixin
from video_agent.adapters.storage.sqlite_strategy_store import SQLiteStrategyStoreMixin
from video_agent.adapters.storage.sqlite_video_thread_store import SQLiteVideoThreadStoreMixin
from video_agent.domain.delivery_case_models import AgentRun, DeliveryCase
from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.domain.models import VideoTask
from video_agent.domain.quality_models import QualityScorecard
from video_agent.domain.review_workflow_models import WorkflowParticipant
from video_agent.domain.validation_models import ValidationReport



def _utcnow() -> datetime:
    return datetime.now(timezone.utc)



def _utcnow_iso() -> str:
    return _utcnow().isoformat()


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


class SQLiteTaskStore(
    SQLiteVideoThreadStoreMixin,
    SQLiteAgentRuntimeDefinitionStoreMixin,
    SQLiteAgentProfileStoreMixin,
    SQLiteAgentRuntimeStoreMixin,
    SQLiteStrategyStoreMixin,
):
    STRATEGY_DECISION_TIMELINE_LIMIT = 5

    def __init__(
        self,
        database_path: Path,
        *,
        agent_runtime_root: Path | None = None,
        default_agent_runtime_tools_allow: list[str] | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.agent_runtime_root = Path("data/agents") if agent_runtime_root is None else Path(agent_runtime_root)
        self.default_agent_runtime_tools_allow = list(
            default_agent_runtime_tools_allow
            or ["read", "exec", "message", "sessions_history", "sessions_list"]
        )

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
                    task_id, root_task_id, parent_task_id, thread_id, iteration_id, result_id, execution_kind,
                    agent_id, session_id, status, phase, prompt, feedback,
                    memory_context_summary, memory_context_digest,
                    task_memory_context_json, selected_memory_ids_json,
                    persistent_memory_context_summary, persistent_memory_context_digest,
                    idempotency_key,
                    current_script_artifact_id, best_result_artifact_id, display_title, title_source,
                    risk_level, generation_mode, strategy_profile_id, scene_spec_id, quality_gate_status,
                    accepted_as_best, accepted_version_rank, task_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.task_id,
                    task.root_task_id,
                    task.parent_task_id,
                    task.thread_id,
                    task.iteration_id,
                    task.result_id,
                    task.execution_kind,
                    task.agent_id,
                    task.session_id,
                    task.status.value,
                    task.phase.value,
                    task.prompt,
                    task.feedback,
                    task.memory_context_summary,
                    task.memory_context_digest,
                    _canonical_json(task.task_memory_context),
                    _canonical_json(task.selected_memory_ids),
                    task.persistent_memory_context_summary,
                    task.persistent_memory_context_digest,
                    idempotency_key,
                    task.current_script_artifact_id,
                    task.best_result_artifact_id,
                    task.display_title,
                    task.title_source,
                    task.risk_level,
                    task.generation_mode,
                    task.strategy_profile_id,
                    task.scene_spec_id,
                    task.quality_gate_status,
                    int(task.accepted_as_best),
                    task.accepted_version_rank,
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
                SET root_task_id = ?, parent_task_id = ?, thread_id = ?, iteration_id = ?, result_id = ?,
                    execution_kind = ?, agent_id = ?, session_id = ?, status = ?, phase = ?, prompt = ?,
                    feedback = ?, memory_context_summary = ?, memory_context_digest = ?,
                    task_memory_context_json = ?, selected_memory_ids_json = ?,
                    persistent_memory_context_summary = ?, persistent_memory_context_digest = ?,
                    current_script_artifact_id = ?, best_result_artifact_id = ?, display_title = ?,
                    title_source = ?, risk_level = ?, generation_mode = ?, strategy_profile_id = ?,
                    scene_spec_id = ?, quality_gate_status = ?, accepted_as_best = ?,
                    accepted_version_rank = ?, task_json = ?, updated_at = ?
                WHERE task_id = ?
                """,
                (
                    task.root_task_id,
                    task.parent_task_id,
                    task.thread_id,
                    task.iteration_id,
                    task.result_id,
                    task.execution_kind,
                    task.agent_id,
                    task.session_id,
                    task.status.value,
                    task.phase.value,
                    task.prompt,
                    task.feedback,
                    task.memory_context_summary,
                    task.memory_context_digest,
                    _canonical_json(task.task_memory_context),
                    _canonical_json(task.selected_memory_ids),
                    task.persistent_memory_context_summary,
                    task.persistent_memory_context_digest,
                    task.current_script_artifact_id,
                    task.best_result_artifact_id,
                    task.display_title,
                    task.title_source,
                    task.risk_level,
                    task.generation_mode,
                    task.strategy_profile_id,
                    task.scene_spec_id,
                    task.quality_gate_status,
                    int(task.accepted_as_best),
                    task.accepted_version_rank,
                    task.model_dump_json(),
                    task.updated_at.isoformat(),
                    task.task_id,
                ),
            )

    def upsert_delivery_case(self, delivery_case: DeliveryCase) -> DeliveryCase:
        delivery_case.updated_at = _utcnow()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO delivery_cases (
                    case_id, root_task_id, active_task_id, selected_task_id, selected_branch_id,
                    status, delivery_status, completion_mode, stop_reason, case_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(case_id) DO UPDATE SET
                    root_task_id = excluded.root_task_id,
                    active_task_id = excluded.active_task_id,
                    selected_task_id = excluded.selected_task_id,
                    selected_branch_id = excluded.selected_branch_id,
                    status = excluded.status,
                    delivery_status = excluded.delivery_status,
                    completion_mode = excluded.completion_mode,
                    stop_reason = excluded.stop_reason,
                    case_json = excluded.case_json,
                    updated_at = excluded.updated_at
                """,
                (
                    delivery_case.case_id,
                    delivery_case.root_task_id,
                    delivery_case.active_task_id,
                    delivery_case.selected_task_id,
                    delivery_case.selected_branch_id,
                    delivery_case.status,
                    delivery_case.delivery_status,
                    delivery_case.completion_mode,
                    delivery_case.stop_reason,
                    delivery_case.model_dump_json(),
                    delivery_case.created_at.isoformat(),
                    delivery_case.updated_at.isoformat(),
                ),
            )
        return delivery_case

    def get_delivery_case(self, case_id: str) -> DeliveryCase | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT case_json FROM delivery_cases WHERE case_id = ?",
                (case_id,),
            ).fetchone()
        if row is None:
            return None
        return DeliveryCase.model_validate_json(row["case_json"])

    def get_delivery_case_by_root_task_id(self, root_task_id: str) -> DeliveryCase | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT case_json FROM delivery_cases WHERE root_task_id = ? ORDER BY created_at ASC LIMIT 1",
                (root_task_id,),
            ).fetchone()
        if row is None:
            return None
        return DeliveryCase.model_validate_json(row["case_json"])

    def create_agent_run(self, agent_run: AgentRun) -> AgentRun:
        return self.upsert_agent_run(agent_run)

    def upsert_agent_run(self, agent_run: AgentRun) -> AgentRun:
        agent_run.updated_at = _utcnow()
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT created_at FROM agent_runs WHERE run_id = ?",
                (agent_run.run_id,),
            ).fetchone()
            if existing is not None:
                agent_run.created_at = datetime.fromisoformat(existing["created_at"])
            connection.execute(
                """
                INSERT INTO agent_runs (
                    run_id, case_id, root_task_id, task_id, role, status, phase, summary,
                    run_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    case_id = excluded.case_id,
                    root_task_id = excluded.root_task_id,
                    task_id = excluded.task_id,
                    role = excluded.role,
                    status = excluded.status,
                    phase = excluded.phase,
                    summary = excluded.summary,
                    run_json = excluded.run_json,
                    updated_at = excluded.updated_at
                """,
                (
                    agent_run.run_id,
                    agent_run.case_id,
                    agent_run.root_task_id,
                    agent_run.task_id,
                    agent_run.role,
                    agent_run.status,
                    agent_run.phase,
                    agent_run.summary,
                    agent_run.model_dump_json(),
                    agent_run.created_at.isoformat(),
                    agent_run.updated_at.isoformat(),
                ),
            )
        return agent_run

    def list_agent_runs(
        self,
        case_id: str,
        *,
        role: str | None = None,
        task_id: str | None = None,
    ) -> list[AgentRun]:
        query = "SELECT run_json FROM agent_runs WHERE case_id = ?"
        params: list[Any] = [case_id]
        if role is not None:
            query += " AND role = ?"
            params.append(role)
        if task_id is not None:
            query += " AND task_id = ?"
            params.append(task_id)
        query += " ORDER BY updated_at ASC, created_at ASC, run_id ASC"
        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [AgentRun.model_validate_json(row["run_json"]) for row in rows]

    def upsert_workflow_participant(self, participant: WorkflowParticipant) -> WorkflowParticipant:
        participant.updated_at = _utcnow()
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT created_at
                FROM workflow_participants
                WHERE root_task_id = ? AND agent_id = ?
                """,
                (participant.root_task_id, participant.agent_id),
            ).fetchone()
            if existing is not None:
                participant.created_at = datetime.fromisoformat(existing["created_at"])
            connection.execute(
                """
                INSERT INTO workflow_participants (
                    root_task_id, agent_id, role, capabilities_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(root_task_id, agent_id) DO UPDATE SET
                    role = excluded.role,
                    capabilities_json = excluded.capabilities_json,
                    updated_at = excluded.updated_at
                """,
                (
                    participant.root_task_id,
                    participant.agent_id,
                    participant.role,
                    json.dumps(participant.capabilities),
                    participant.created_at.isoformat(),
                    participant.updated_at.isoformat(),
                ),
            )
        return participant

    def get_workflow_participant(self, root_task_id: str, agent_id: str) -> WorkflowParticipant | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT root_task_id, agent_id, role, capabilities_json, created_at, updated_at
                FROM workflow_participants
                WHERE root_task_id = ? AND agent_id = ?
                """,
                (root_task_id, agent_id),
            ).fetchone()
        if row is None:
            return None
        return WorkflowParticipant(
            root_task_id=row["root_task_id"],
            agent_id=row["agent_id"],
            role=row["role"],
            capabilities=json.loads(row["capabilities_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def list_workflow_participants(self, root_task_id: str) -> list[WorkflowParticipant]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT root_task_id, agent_id, role, capabilities_json, created_at, updated_at
                FROM workflow_participants
                WHERE root_task_id = ?
                ORDER BY created_at ASC, agent_id ASC
                """,
                (root_task_id,),
            ).fetchall()
        return [
            WorkflowParticipant(
                root_task_id=row["root_task_id"],
                agent_id=row["agent_id"],
                role=row["role"],
                capabilities=json.loads(row["capabilities_json"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in rows
        ]

    def delete_workflow_participant(self, root_task_id: str, agent_id: str) -> bool:
        with self._connect() as connection:
            result = connection.execute(
                """
                DELETE FROM workflow_participants
                WHERE root_task_id = ? AND agent_id = ?
                """,
                (root_task_id, agent_id),
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
        limit: Optional[int] = 50,
        status: Optional[str] = None,
        agent_id: Optional[str] = None,
        order_by: str = "created_at",
    ) -> list[dict[str, Any]]:
        if order_by not in {"created_at", "updated_at"}:
            raise ValueError(f"unsupported_task_order:{order_by}")
        query = (
            "SELECT task_id, thread_id, iteration_id, display_title, title_source, "
            "status, phase, prompt, created_at, updated_at FROM video_tasks"
        )
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
        query += f" ORDER BY {order_by} DESC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [
            {
                "task_id": row["task_id"],
                "thread_id": row["thread_id"],
                "iteration_id": row["iteration_id"],
                "display_title": row["display_title"],
                "title_source": row["title_source"],
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

    def list_lineage_tasks(self, root_task_id: str) -> list[VideoTask]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT task_json
                FROM video_tasks
                WHERE root_task_id = ?
                ORDER BY created_at ASC, task_id ASC
                """,
                (root_task_id,),
            ).fetchall()
        return [VideoTask.model_validate_json(row["task_json"]) for row in rows]

    def list_thread_tasks(self, thread_id: str) -> list[VideoTask]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT task_json
                FROM video_tasks
                WHERE thread_id = ?
                ORDER BY updated_at DESC, created_at DESC, task_id DESC
                """,
                (thread_id,),
            ).fetchall()
        return [VideoTask.model_validate_json(row["task_json"]) for row in rows]

    def list_thread_bound_tasks(self) -> list[VideoTask]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT task_json
                FROM video_tasks
                WHERE thread_id IS NOT NULL
                ORDER BY updated_at DESC, created_at DESC, task_id DESC
                """
            ).fetchall()
        return [VideoTask.model_validate_json(row["task_json"]) for row in rows]

    def list_events(
        self,
        task_id: str,
        limit: int | None = 200,
        *,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        params: list[Any] = [task_id]
        query = """
            SELECT event_type, payload_json, created_at
            FROM task_events
            WHERE task_id = ?
        """
        if event_type is not None:
            query += " AND event_type = ?"
            params.append(event_type)
        query += " ORDER BY id ASC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [
            {
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def upsert_task_quality_score(self, task_id: str, scorecard: QualityScorecard) -> QualityScorecard:
        payload = scorecard.model_copy(update={"task_id": task_id})
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO task_quality_scores (task_id, scorecard_json, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    scorecard_json = excluded.scorecard_json,
                    created_at = excluded.created_at
                """,
                (
                    task_id,
                    payload.model_dump_json(),
                    _utcnow_iso(),
                ),
            )
        return payload

    def get_task_quality_score(self, task_id: str) -> Optional[QualityScorecard]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT scorecard_json FROM task_quality_scores WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        return QualityScorecard.model_validate_json(row["scorecard_json"])

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
            connection.execute("DELETE FROM agent_runs WHERE task_id = ? OR root_task_id = ?", (task_id, task_id))
            connection.execute("DELETE FROM delivery_cases WHERE case_id = ? OR root_task_id = ?", (task_id, task_id))
            connection.execute("DELETE FROM workflow_participants WHERE root_task_id = ?", (task_id,))
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
