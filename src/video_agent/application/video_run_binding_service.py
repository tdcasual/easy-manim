from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.domain.models import VideoTask
from video_agent.domain.video_thread_models import VideoAgentRun, VideoThreadParticipant


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class VideoRunBindingService:
    def __init__(self, *, store: SQLiteTaskStore) -> None:
        self.store = store

    def attach_run(
        self,
        *,
        thread_id: str,
        iteration_id: str,
        agent_id: str,
        role: str,
        task_id: str | None = None,
    ) -> VideoAgentRun:
        self.store.upsert_video_thread_participant(
            VideoThreadParticipant(
                thread_id=thread_id,
                participant_id=agent_id,
                participant_type="agent",
                agent_id=agent_id,
                role=role,
                display_name=role.replace("_", " ").strip().title() or "Agent",
            )
        )
        run = VideoAgentRun(
            run_id=f"run-{uuid4()}",
            thread_id=thread_id,
            iteration_id=iteration_id,
            task_id=task_id,
            agent_id=agent_id,
            role=role,
        )
        return self.store.upsert_video_agent_run(run)

    def mark_run_status(
        self,
        run_id: str,
        *,
        status: str,
        phase: str | None = None,
        output_summary: str | None = None,
    ) -> VideoAgentRun:
        run = self.store.get_video_agent_run(run_id)
        if run is None:
            raise KeyError(f"Unknown run_id: {run_id}")
        run.status = status
        run.phase = phase
        run.output_summary = output_summary
        return self.store.upsert_video_agent_run(run)

    def sync_task_lifecycle_run(
        self,
        *,
        task: VideoTask,
        status: str,
        phase: str | None = None,
        summary: str | None = None,
    ) -> VideoAgentRun | None:
        if (
            task.thread_id is None
            or task.iteration_id is None
            or task.target_agent_role is None
            or (task.target_agent_id is None and task.target_participant_id is None)
        ):
            return None

        participant_id = task.target_participant_id or task.target_agent_id
        agent_id = task.target_agent_id or participant_id
        display_name = (
            task.target_agent_role.replace("_", " ").strip().title()
            if task.target_agent_role
            else agent_id or "Agent"
        )
        self.store.upsert_video_thread_participant(
            VideoThreadParticipant(
                thread_id=task.thread_id,
                participant_id=participant_id or agent_id or "agent",
                participant_type="agent",
                agent_id=agent_id,
                role=task.target_agent_role,
                display_name=display_name or "Agent",
            )
        )

        run_id = self._lifecycle_run_id(task.task_id)
        existing = self.store.get_video_agent_run(run_id)
        now = _utcnow()
        started_at = None if existing is None else existing.started_at
        ended_at = None if existing is None else existing.ended_at
        if status == "running":
            started_at = started_at or now
            ended_at = None
        elif status in {"completed", "failed", "cancelled"}:
            started_at = started_at or now
            ended_at = now
        elif status == "queued":
            ended_at = None

        run = VideoAgentRun(
            run_id=run_id,
            thread_id=task.thread_id,
            iteration_id=task.iteration_id,
            task_id=task.task_id,
            agent_id=agent_id or "agent",
            role=task.target_agent_role,
            status=status,
            phase=phase,
            output_summary=summary,
            started_at=started_at,
            ended_at=ended_at,
        )
        return self.store.upsert_video_agent_run(run)

    @staticmethod
    def _lifecycle_run_id(task_id: str) -> str:
        return f"thread-run:{task_id}"
