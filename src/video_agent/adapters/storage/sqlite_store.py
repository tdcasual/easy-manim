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
from video_agent.domain.delivery_case_models import AgentRun, DeliveryCase
from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.domain.models import VideoTask
from video_agent.domain.quality_models import QualityScorecard
from video_agent.domain.review_workflow_models import WorkflowParticipant
from video_agent.domain.session_memory_models import SessionMemorySnapshot
from video_agent.domain.strategy_models import StrategyProfile
from video_agent.domain.strategy_models import StrategyPromotionDecision
from video_agent.domain.validation_models import ValidationReport
from video_agent.domain.video_thread_models import (
    VideoAgentRun as ThreadVideoAgentRun,
    VideoIteration,
    VideoResult as ThreadVideoResult,
    VideoThread,
    VideoThreadParticipant,
    VideoTurn,
)



def _utcnow() -> datetime:
    return datetime.now(timezone.utc)



def _utcnow_iso() -> str:
    return _utcnow().isoformat()


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


class SQLiteTaskStore:
    STRATEGY_DECISION_TIMELINE_LIMIT = 5

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)

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
                    memory_context_summary, memory_context_digest, idempotency_key,
                    current_script_artifact_id, best_result_artifact_id, display_title, title_source,
                    risk_level, generation_mode, strategy_profile_id, scene_spec_id, quality_gate_status,
                    accepted_as_best, accepted_version_rank, task_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    feedback = ?, memory_context_summary = ?, memory_context_digest = ?, current_script_artifact_id = ?,
                    best_result_artifact_id = ?, display_title = ?, title_source = ?, risk_level = ?,
                    generation_mode = ?, strategy_profile_id = ?, scene_spec_id = ?, quality_gate_status = ?,
                    accepted_as_best = ?, accepted_version_rank = ?, task_json = ?, updated_at = ?
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

    def upsert_video_thread(self, thread: VideoThread) -> VideoThread:
        thread.updated_at = _utcnow()
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT created_at FROM video_threads WHERE thread_id = ?",
                (thread.thread_id,),
            ).fetchone()
            if existing is not None:
                thread.created_at = datetime.fromisoformat(existing["created_at"])
            connection.execute(
                """
                INSERT INTO video_threads (
                    thread_id, owner_agent_id, title, status, current_iteration_id, selected_result_id,
                    origin_prompt, origin_context_summary, thread_json, created_at, updated_at, archived_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(thread_id) DO UPDATE SET
                    owner_agent_id = excluded.owner_agent_id,
                    title = excluded.title,
                    status = excluded.status,
                    current_iteration_id = excluded.current_iteration_id,
                    selected_result_id = excluded.selected_result_id,
                    origin_prompt = excluded.origin_prompt,
                    origin_context_summary = excluded.origin_context_summary,
                    thread_json = excluded.thread_json,
                    updated_at = excluded.updated_at,
                    archived_at = excluded.archived_at
                """,
                (
                    thread.thread_id,
                    thread.owner_agent_id,
                    thread.title,
                    thread.status,
                    thread.current_iteration_id,
                    thread.selected_result_id,
                    thread.origin_prompt,
                    thread.origin_context_summary,
                    thread.model_dump_json(),
                    thread.created_at.isoformat(),
                    thread.updated_at.isoformat(),
                    None if thread.archived_at is None else thread.archived_at.isoformat(),
                ),
            )
        return thread

    def upsert_video_thread_json(
        self,
        *,
        thread_id: str,
        owner_agent_id: str,
        title: str,
        origin_prompt: str,
        origin_context_summary: str | None = None,
        status: str = "active",
        current_iteration_id: str | None = None,
        selected_result_id: str | None = None,
    ) -> VideoThread:
        return self.upsert_video_thread(
            VideoThread(
                thread_id=thread_id,
                owner_agent_id=owner_agent_id,
                title=title,
                status=status,
                current_iteration_id=current_iteration_id,
                selected_result_id=selected_result_id,
                origin_prompt=origin_prompt,
                origin_context_summary=origin_context_summary,
            )
        )

    def get_video_thread(self, thread_id: str) -> VideoThread | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT thread_json FROM video_threads WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
        if row is None:
            return None
        return VideoThread.model_validate_json(row["thread_json"])

    def upsert_video_iteration(self, iteration: VideoIteration) -> VideoIteration:
        iteration.updated_at = _utcnow()
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT created_at FROM video_iterations WHERE iteration_id = ?",
                (iteration.iteration_id,),
            ).fetchone()
            if existing is not None:
                iteration.created_at = datetime.fromisoformat(existing["created_at"])
            connection.execute(
                """
                INSERT INTO video_iterations (
                    iteration_id, thread_id, parent_iteration_id, goal, requested_action,
                    preserve_working_parts, status, resolution_state, focus_summary, selected_result_id,
                    source_result_id, initiated_by_turn_id, responsible_role, responsible_agent_id,
                    iteration_json, created_at, updated_at, closed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(iteration_id) DO UPDATE SET
                    thread_id = excluded.thread_id,
                    parent_iteration_id = excluded.parent_iteration_id,
                    goal = excluded.goal,
                    requested_action = excluded.requested_action,
                    preserve_working_parts = excluded.preserve_working_parts,
                    status = excluded.status,
                    resolution_state = excluded.resolution_state,
                    focus_summary = excluded.focus_summary,
                    selected_result_id = excluded.selected_result_id,
                    source_result_id = excluded.source_result_id,
                    initiated_by_turn_id = excluded.initiated_by_turn_id,
                    responsible_role = excluded.responsible_role,
                    responsible_agent_id = excluded.responsible_agent_id,
                    iteration_json = excluded.iteration_json,
                    updated_at = excluded.updated_at,
                    closed_at = excluded.closed_at
                """,
                (
                    iteration.iteration_id,
                    iteration.thread_id,
                    iteration.parent_iteration_id,
                    iteration.goal,
                    iteration.requested_action,
                    None if iteration.preserve_working_parts is None else int(iteration.preserve_working_parts),
                    iteration.status,
                    iteration.resolution_state,
                    iteration.focus_summary,
                    iteration.selected_result_id,
                    iteration.source_result_id,
                    iteration.initiated_by_turn_id,
                    iteration.responsible_role,
                    iteration.responsible_agent_id,
                    iteration.model_dump_json(),
                    iteration.created_at.isoformat(),
                    iteration.updated_at.isoformat(),
                    None if iteration.closed_at is None else iteration.closed_at.isoformat(),
                ),
            )
        return iteration

    def get_video_iteration(self, iteration_id: str) -> VideoIteration | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT iteration_json FROM video_iterations WHERE iteration_id = ?",
                (iteration_id,),
            ).fetchone()
        if row is None:
            return None
        return VideoIteration.model_validate_json(row["iteration_json"])

    def list_video_iterations(self, thread_id: str) -> list[VideoIteration]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT iteration_json
                FROM video_iterations
                WHERE thread_id = ?
                ORDER BY created_at ASC, iteration_id ASC
                """,
                (thread_id,),
            ).fetchall()
        return [VideoIteration.model_validate_json(row["iteration_json"]) for row in rows]

    def upsert_video_turn(self, turn: VideoTurn) -> VideoTurn:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO video_turns (
                    turn_id, thread_id, iteration_id, turn_type, speaker_type, speaker_agent_id, speaker_role,
                    title, summary, visibility, source_run_id, source_task_id, turn_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(turn_id) DO UPDATE SET
                    thread_id = excluded.thread_id,
                    iteration_id = excluded.iteration_id,
                    turn_type = excluded.turn_type,
                    speaker_type = excluded.speaker_type,
                    speaker_agent_id = excluded.speaker_agent_id,
                    speaker_role = excluded.speaker_role,
                    title = excluded.title,
                    summary = excluded.summary,
                    visibility = excluded.visibility,
                    source_run_id = excluded.source_run_id,
                    source_task_id = excluded.source_task_id,
                    turn_json = excluded.turn_json,
                    created_at = excluded.created_at
                """,
                (
                    turn.turn_id,
                    turn.thread_id,
                    turn.iteration_id,
                    turn.turn_type,
                    turn.speaker_type,
                    turn.speaker_agent_id,
                    turn.speaker_role,
                    turn.title,
                    turn.summary,
                    turn.visibility,
                    turn.source_run_id,
                    turn.source_task_id,
                    turn.model_dump_json(),
                    turn.created_at.isoformat(),
                ),
            )
        return turn

    def get_video_turn(self, turn_id: str) -> VideoTurn | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT turn_json FROM video_turns WHERE turn_id = ?",
                (turn_id,),
            ).fetchone()
        if row is None:
            return None
        return VideoTurn.model_validate_json(row["turn_json"])

    def list_video_turns(self, thread_id: str) -> list[VideoTurn]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT turn_json
                FROM video_turns
                WHERE thread_id = ?
                ORDER BY created_at ASC, turn_id ASC
                """,
                (thread_id,),
            ).fetchall()
        return [VideoTurn.model_validate_json(row["turn_json"]) for row in rows]

    def upsert_video_result(self, result: ThreadVideoResult) -> ThreadVideoResult:
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT created_at FROM video_results WHERE result_id = ?",
                (result.result_id,),
            ).fetchone()
            if existing is not None:
                result.created_at = datetime.fromisoformat(existing["created_at"])
            connection.execute(
                """
                INSERT INTO video_results (
                    result_id, thread_id, iteration_id, source_task_id, status, video_resource,
                    preview_resources_json, script_resource, validation_report_resource, result_summary,
                    quality_summary, selected, result_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(result_id) DO UPDATE SET
                    thread_id = excluded.thread_id,
                    iteration_id = excluded.iteration_id,
                    source_task_id = excluded.source_task_id,
                    status = excluded.status,
                    video_resource = excluded.video_resource,
                    preview_resources_json = excluded.preview_resources_json,
                    script_resource = excluded.script_resource,
                    validation_report_resource = excluded.validation_report_resource,
                    result_summary = excluded.result_summary,
                    quality_summary = excluded.quality_summary,
                    selected = excluded.selected,
                    result_json = excluded.result_json
                """,
                (
                    result.result_id,
                    result.thread_id,
                    result.iteration_id,
                    result.source_task_id,
                    result.status,
                    result.video_resource,
                    json.dumps(result.preview_resources),
                    result.script_resource,
                    result.validation_report_resource,
                    result.result_summary,
                    result.quality_summary,
                    int(result.selected),
                    result.model_dump_json(),
                    result.created_at.isoformat(),
                ),
            )
        return result

    def get_video_result(self, result_id: str) -> ThreadVideoResult | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT result_json FROM video_results WHERE result_id = ?",
                (result_id,),
            ).fetchone()
        if row is None:
            return None
        return ThreadVideoResult.model_validate_json(row["result_json"])

    def list_video_results(self, thread_id: str) -> list[ThreadVideoResult]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT result_json
                FROM video_results
                WHERE thread_id = ?
                ORDER BY created_at ASC, result_id ASC
                """,
                (thread_id,),
            ).fetchall()
        return [ThreadVideoResult.model_validate_json(row["result_json"]) for row in rows]

    def upsert_video_thread_participant(
        self,
        participant: VideoThreadParticipant,
    ) -> VideoThreadParticipant:
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT joined_at
                FROM video_thread_participants
                WHERE thread_id = ? AND participant_id = ?
                """,
                (participant.thread_id, participant.participant_id),
            ).fetchone()
            if existing is not None:
                participant.joined_at = datetime.fromisoformat(existing["joined_at"])
            connection.execute(
                """
                INSERT INTO video_thread_participants (
                    thread_id, participant_id, participant_type, agent_id, role, display_name,
                    capabilities_json, participant_json, joined_at, left_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(thread_id, participant_id) DO UPDATE SET
                    participant_type = excluded.participant_type,
                    agent_id = excluded.agent_id,
                    role = excluded.role,
                    display_name = excluded.display_name,
                    capabilities_json = excluded.capabilities_json,
                    participant_json = excluded.participant_json,
                    left_at = excluded.left_at
                """,
                (
                    participant.thread_id,
                    participant.participant_id,
                    participant.participant_type,
                    participant.agent_id,
                    participant.role,
                    participant.display_name,
                    json.dumps(participant.capabilities),
                    participant.model_dump_json(),
                    participant.joined_at.isoformat(),
                    None if participant.left_at is None else participant.left_at.isoformat(),
                ),
            )
        return participant

    def get_video_thread_participant(
        self,
        thread_id: str,
        participant_id: str,
    ) -> VideoThreadParticipant | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT participant_json
                FROM video_thread_participants
                WHERE thread_id = ? AND participant_id = ?
                """,
                (thread_id, participant_id),
            ).fetchone()
        if row is None:
            return None
        return VideoThreadParticipant.model_validate_json(row["participant_json"])

    def list_video_thread_participants(self, thread_id: str) -> list[VideoThreadParticipant]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT participant_json
                FROM video_thread_participants
                WHERE thread_id = ?
                ORDER BY joined_at ASC, participant_id ASC
                """,
                (thread_id,),
            ).fetchall()
        return [
            VideoThreadParticipant.model_validate_json(row["participant_json"])
            for row in rows
        ]

    def delete_video_thread_participant(self, thread_id: str, participant_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM video_thread_participants
                WHERE thread_id = ? AND participant_id = ?
                """,
                (thread_id, participant_id),
            )
        return cursor.rowcount > 0

    def upsert_video_agent_run(self, run: ThreadVideoAgentRun) -> ThreadVideoAgentRun:
        run.updated_at = _utcnow()
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT created_at
                FROM video_agent_runs
                WHERE run_id = ?
                """,
                (run.run_id,),
            ).fetchone()
            if existing is not None:
                run.created_at = datetime.fromisoformat(existing["created_at"])
            connection.execute(
                """
                INSERT INTO video_agent_runs (
                    run_id, thread_id, iteration_id, task_id, agent_id, role, status, phase,
                    input_summary, output_summary, run_json, started_at, ended_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    thread_id = excluded.thread_id,
                    iteration_id = excluded.iteration_id,
                    task_id = excluded.task_id,
                    agent_id = excluded.agent_id,
                    role = excluded.role,
                    status = excluded.status,
                    phase = excluded.phase,
                    input_summary = excluded.input_summary,
                    output_summary = excluded.output_summary,
                    run_json = excluded.run_json,
                    started_at = excluded.started_at,
                    ended_at = excluded.ended_at,
                    updated_at = excluded.updated_at
                """,
                (
                    run.run_id,
                    run.thread_id,
                    run.iteration_id,
                    run.task_id,
                    run.agent_id,
                    run.role,
                    run.status,
                    run.phase,
                    run.input_summary,
                    run.output_summary,
                    run.model_dump_json(),
                    None if run.started_at is None else run.started_at.isoformat(),
                    None if run.ended_at is None else run.ended_at.isoformat(),
                    run.created_at.isoformat(),
                    run.updated_at.isoformat(),
                ),
            )
        return run

    def get_video_agent_run(self, run_id: str) -> ThreadVideoAgentRun | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT run_json FROM video_agent_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return ThreadVideoAgentRun.model_validate_json(row["run_json"])

    def list_video_agent_runs(self, thread_id: str) -> list[ThreadVideoAgentRun]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT run_json
                FROM video_agent_runs
                WHERE thread_id = ?
                ORDER BY created_at ASC, run_id ASC
                """,
                (thread_id,),
            ).fetchall()
        return [ThreadVideoAgentRun.model_validate_json(row["run_json"]) for row in rows]

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
                    event_id, agent_id, task_id, session_id, status, quality_passed, issue_codes_json,
                    quality_score, profile_digest, memory_ids_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    agent_id = excluded.agent_id,
                    session_id = excluded.session_id,
                    status = excluded.status,
                    quality_passed = excluded.quality_passed,
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
                    None if event.quality_passed is None else int(event.quality_passed),
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
                    event_id, agent_id, task_id, session_id, status, quality_passed, issue_codes_json,
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
                    event_id, agent_id, task_id, session_id, status, quality_passed, issue_codes_json,
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
                    session_id, session_hash, agent_id, token_hash, status, created_at, expires_at, last_seen_at, revoked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.session_hash,
                    session.agent_id,
                    session.token_hash,
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
                    session_id, session_hash, agent_id, token_hash, status, created_at, expires_at, last_seen_at, revoked_at
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
                    session_id, session_hash, agent_id, token_hash, status, created_at, expires_at, last_seen_at, revoked_at
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

    def upsert_session_memory_snapshot(self, snapshot: SessionMemorySnapshot) -> SessionMemorySnapshot:
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT created_at FROM session_memory_snapshots WHERE session_id = ?",
                (snapshot.session_id,),
            ).fetchone()
            created_at = existing["created_at"] if existing is not None else _utcnow_iso()
            updated_at = _utcnow_iso()
            connection.execute(
                """
                INSERT INTO session_memory_snapshots (
                    session_id, agent_id, snapshot_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    agent_id = excluded.agent_id,
                    snapshot_json = excluded.snapshot_json,
                    updated_at = excluded.updated_at
                """,
                (
                    snapshot.session_id,
                    snapshot.agent_id,
                    snapshot.model_dump_json(),
                    created_at,
                    updated_at,
                ),
            )
        return snapshot

    def get_session_memory_snapshot(self, session_id: str) -> SessionMemorySnapshot | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT snapshot_json
                FROM session_memory_snapshots
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return SessionMemorySnapshot.model_validate_json(row["snapshot_json"])

    def list_session_memory_snapshots(self, agent_id: str | None = None) -> list[SessionMemorySnapshot]:
        query = """
            SELECT snapshot_json
            FROM session_memory_snapshots
        """
        params: list[Any] = []
        if agent_id is not None:
            query += " WHERE agent_id = ?"
            params.append(agent_id)
        query += " ORDER BY updated_at ASC, created_at ASC, session_id ASC"
        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [SessionMemorySnapshot.model_validate_json(row["snapshot_json"]) for row in rows]

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

    @staticmethod
    def _row_to_strategy_profile(row: sqlite3.Row) -> StrategyProfile:
        return StrategyProfile(
            strategy_id=row["strategy_id"],
            scope=row["scope"],
            prompt_cluster=row["prompt_cluster"],
            status=row["status"],
            params=json.loads(row["params_json"]),
            metrics=json.loads(row["metrics_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _upsert_strategy_profile_in_connection(
        self,
        connection: sqlite3.Connection,
        profile: StrategyProfile,
    ) -> StrategyProfile:
        existing = connection.execute(
            """
            SELECT strategy_id, scope, prompt_cluster, status, params_json, metrics_json, created_at, updated_at
            FROM strategy_profiles
            WHERE strategy_id = ?
            """,
            (profile.strategy_id,),
        ).fetchone()
        profile.updated_at = _utcnow()
        if existing is not None:
            profile.created_at = datetime.fromisoformat(existing["created_at"])
        connection.execute(
            """
            INSERT INTO strategy_profiles (
                strategy_id, scope, prompt_cluster, status, params_json, metrics_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(strategy_id) DO UPDATE SET
                scope = excluded.scope,
                prompt_cluster = excluded.prompt_cluster,
                status = excluded.status,
                params_json = excluded.params_json,
                metrics_json = excluded.metrics_json,
                updated_at = excluded.updated_at
            """,
            (
                profile.strategy_id,
                profile.scope,
                profile.prompt_cluster,
                profile.status,
                json.dumps(profile.params),
                json.dumps(profile.metrics),
                profile.created_at.isoformat(),
                profile.updated_at.isoformat(),
            ),
        )
        return profile

    def create_strategy_profile(self, profile: StrategyProfile) -> StrategyProfile:
        with self._connect() as connection:
            return self._upsert_strategy_profile_in_connection(connection, profile)

    def get_strategy_profile(self, strategy_id: str) -> Optional[StrategyProfile]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT strategy_id, scope, prompt_cluster, status, params_json, metrics_json, created_at, updated_at
                FROM strategy_profiles
                WHERE strategy_id = ?
                """,
                (strategy_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_strategy_profile(row)

    def list_strategy_profiles(self, status: str | None = None) -> list[StrategyProfile]:
        query = """
            SELECT strategy_id, scope, prompt_cluster, status, params_json, metrics_json, created_at, updated_at
            FROM strategy_profiles
        """
        params: list[Any] = []
        if status is not None:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at ASC"
        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [self._row_to_strategy_profile(row) for row in rows]

    def get_active_strategy_profile(
        self,
        *,
        scope: str,
        prompt_cluster: str | None,
        exclude_strategy_id: str | None = None,
    ) -> Optional[StrategyProfile]:
        candidates = self.list_strategy_profiles(status="active")
        for profile in candidates:
            if profile.scope != scope or profile.prompt_cluster != prompt_cluster:
                continue
            if exclude_strategy_id is not None and profile.strategy_id == exclude_strategy_id:
                continue
            return profile
        return None

    def activate_strategy_profile(
        self,
        strategy_id: str,
        *,
        applied_at: str | None = None,
    ) -> tuple[StrategyProfile, StrategyProfile | None]:
        target = self.get_strategy_profile(strategy_id)
        if target is None:
            raise ValueError(f"Unknown strategy profile: {strategy_id}")
        timestamp = applied_at or _utcnow_iso()
        previous_active = self.get_active_strategy_profile(
            scope=target.scope,
            prompt_cluster=target.prompt_cluster,
            exclude_strategy_id=target.strategy_id,
        )
        target_guarded = (
            dict(target.metrics.get("guarded_rollout", {}))
            if isinstance(target.metrics.get("guarded_rollout"), dict)
            else {}
        )
        target_guarded.update(
            {
                "last_applied_at": timestamp,
                "rollback_target_strategy_id": None if previous_active is None else previous_active.strategy_id,
                "rollback_armed": previous_active is not None,
            }
        )
        target.metrics = {
            **target.metrics,
            "guarded_rollout": target_guarded,
        }
        target.status = "active"

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if previous_active is not None:
                previous_guarded = (
                    dict(previous_active.metrics.get("guarded_rollout", {}))
                    if isinstance(previous_active.metrics.get("guarded_rollout"), dict)
                    else {}
                )
                previous_guarded.update(
                    {
                        "superseded_at": timestamp,
                        "superseded_by_strategy_id": target.strategy_id,
                    }
                )
                previous_active.metrics = {
                    **previous_active.metrics,
                    "guarded_rollout": previous_guarded,
                }
                previous_active.status = "superseded"
                self._upsert_strategy_profile_in_connection(connection, previous_active)
            self._upsert_strategy_profile_in_connection(connection, target)
        return target, previous_active

    def rollback_strategy_profile(
        self,
        strategy_id: str,
        *,
        rolled_back_at: str | None = None,
    ) -> tuple[StrategyProfile, StrategyProfile]:
        target = self.get_strategy_profile(strategy_id)
        if target is None:
            raise ValueError(f"Unknown strategy profile: {strategy_id}")
        target_guarded = (
            dict(target.metrics.get("guarded_rollout", {}))
            if isinstance(target.metrics.get("guarded_rollout"), dict)
            else {}
        )
        rollback_target_strategy_id = target_guarded.get("rollback_target_strategy_id")
        if not rollback_target_strategy_id:
            raise ValueError(f"No guarded rollback target for strategy profile: {strategy_id}")
        rollback_target = self.get_strategy_profile(str(rollback_target_strategy_id))
        if rollback_target is None:
            raise ValueError(f"Unknown rollback strategy profile: {rollback_target_strategy_id}")

        timestamp = rolled_back_at or _utcnow_iso()
        target_guarded.update(
            {
                "rollback_armed": False,
                "consecutive_shadow_passes": 0,
                "last_rolled_back_at": timestamp,
            }
        )
        target.metrics = {
            **target.metrics,
            "guarded_rollout": target_guarded,
        }
        target.status = "rolled_back"

        rollback_guarded = (
            dict(rollback_target.metrics.get("guarded_rollout", {}))
            if isinstance(rollback_target.metrics.get("guarded_rollout"), dict)
            else {}
        )
        rollback_guarded.update(
            {
                "restored_at": timestamp,
                "restored_from_strategy_id": target.strategy_id,
            }
        )
        rollback_target.metrics = {
            **rollback_target.metrics,
            "guarded_rollout": rollback_guarded,
        }
        rollback_target.status = "active"

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._upsert_strategy_profile_in_connection(connection, target)
            self._upsert_strategy_profile_in_connection(connection, rollback_target)
        return target, rollback_target

    def record_strategy_eval_run(
        self,
        strategy_id: str,
        *,
        baseline_summary: dict[str, Any],
        challenger_summary: dict[str, Any],
        promotion_recommended: bool,
        promotion_decision: StrategyPromotionDecision | dict[str, Any] | None = None,
    ) -> StrategyProfile:
        profile = self.get_strategy_profile(strategy_id)
        if profile is None:
            raise ValueError(f"Unknown strategy profile: {strategy_id}")
        recorded_at = _utcnow_iso()
        if promotion_decision is None:
            decision_payload = StrategyPromotionDecision(
                approved=promotion_recommended,
                reasons=[],
                deltas={},
                mode="shadow",
                applied=False,
                recorded_at=recorded_at,
            ).model_dump(mode="json")
        elif isinstance(promotion_decision, StrategyPromotionDecision):
            decision_payload = promotion_decision.model_dump(mode="json")
        else:
            decision_payload = StrategyPromotionDecision.model_validate(
                {
                    "approved": promotion_recommended,
                    "reasons": [],
                    "deltas": {},
                    "mode": "shadow",
                    "applied": False,
                    "recorded_at": recorded_at,
                    **dict(promotion_decision),
                }
            ).model_dump(mode="json")

        decision_payload["recorded_at"] = str(decision_payload.get("recorded_at") or recorded_at)
        guarded_rollout = (
            dict(profile.metrics.get("guarded_rollout", {}))
            if isinstance(profile.metrics.get("guarded_rollout"), dict)
            else {}
        )
        consecutive_shadow_passes = int(guarded_rollout.get("consecutive_shadow_passes", 0) or 0)
        consecutive_shadow_passes = consecutive_shadow_passes + 1 if promotion_recommended else 0
        guarded_rollout["consecutive_shadow_passes"] = consecutive_shadow_passes
        if promotion_recommended:
            guarded_rollout["last_shadow_pass_at"] = decision_payload["recorded_at"]
        else:
            guarded_rollout["last_shadow_failure_at"] = decision_payload["recorded_at"]

        timeline_kind = "strategy_promotion_shadow"
        if bool(decision_payload.get("applied")) and bool(decision_payload.get("approved")):
            timeline_kind = "strategy_promotion_applied"
        elif bool(decision_payload.get("applied")) and not bool(decision_payload.get("approved")):
            timeline_kind = "strategy_promotion_rollback"
        timeline = [
            {
                "kind": timeline_kind,
                "recorded_at": decision_payload["recorded_at"],
                "strategy_id": strategy_id,
                "baseline_run_id": baseline_summary["run_id"],
                "challenger_run_id": challenger_summary["run_id"],
                "promotion_recommended": promotion_recommended,
                "promotion_decision": decision_payload,
            },
            *[
                item
                for item in profile.metrics.get("decision_timeline", [])
                if isinstance(item, dict)
            ],
        ]
        timeline = sorted(
            timeline,
            key=lambda item: str(item.get("recorded_at") or ""),
            reverse=True,
        )[: self.STRATEGY_DECISION_TIMELINE_LIMIT]

        profile.metrics = {
            **profile.metrics,
            "last_eval_run": {
                "baseline_run_id": baseline_summary["run_id"],
                "challenger_run_id": challenger_summary["run_id"],
                "baseline_success_rate": baseline_summary.get("report", {}).get("success_rate", 0.0),
                "challenger_success_rate": challenger_summary.get("report", {}).get("success_rate", 0.0),
                "baseline_accepted_quality_rate": baseline_summary.get("report", {}).get("quality", {}).get("pass_rate", 0.0),
                "challenger_accepted_quality_rate": challenger_summary.get("report", {}).get("quality", {}).get("pass_rate", 0.0),
                "promotion_mode": str(decision_payload.get("mode") or "shadow"),
                "promotion_recommended": promotion_recommended,
                "promotion_decision": decision_payload,
            },
            "decision_timeline": timeline,
            "guarded_rollout": guarded_rollout,
        }
        return self.create_strategy_profile(profile)

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
            quality_passed=None if row["quality_passed"] is None else bool(row["quality_passed"]),
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
            token_hash=row["token_hash"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]),
            last_seen_at=datetime.fromisoformat(row["last_seen_at"]),
            revoked_at=None if row["revoked_at"] is None else datetime.fromisoformat(row["revoked_at"]),
        )
