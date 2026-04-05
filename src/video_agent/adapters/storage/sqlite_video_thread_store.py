from __future__ import annotations

import json
from datetime import datetime, timezone

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


class SQLiteVideoThreadStoreMixin:
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
