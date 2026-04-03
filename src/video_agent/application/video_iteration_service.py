from __future__ import annotations

from uuid import uuid4

from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.domain.video_thread_models import VideoIteration, VideoResult


class VideoIterationService:
    def __init__(self, *, store: SQLiteTaskStore) -> None:
        self.store = store

    def create_iteration(
        self,
        *,
        thread_id: str,
        goal: str,
        parent_iteration_id: str | None = None,
        requested_action: str | None = None,
        source_result_id: str | None = None,
        preserve_working_parts: bool | None = None,
    ) -> VideoIteration:
        iteration = VideoIteration(
            iteration_id=f"iter-{uuid4()}",
            thread_id=thread_id,
            parent_iteration_id=parent_iteration_id,
            goal=goal,
            requested_action=requested_action,
            source_result_id=source_result_id,
            preserve_working_parts=preserve_working_parts,
        )
        return self.store.upsert_video_iteration(iteration)

    def assign_responsibility(
        self,
        iteration_id: str,
        *,
        responsible_role: str,
        responsible_agent_id: str | None = None,
    ) -> VideoIteration:
        iteration = self.load_iteration(iteration_id)
        iteration.responsible_role = responsible_role
        iteration.responsible_agent_id = responsible_agent_id
        return self.store.upsert_video_iteration(iteration)

    def register_result(
        self,
        *,
        thread_id: str,
        iteration_id: str,
        source_task_id: str | None,
        status: str,
        result_summary: str,
    ) -> VideoResult:
        result = VideoResult(
            result_id=f"result-{uuid4()}",
            thread_id=thread_id,
            iteration_id=iteration_id,
            source_task_id=source_task_id,
            status=status,
            result_summary=result_summary,
        )
        return self.store.upsert_video_result(result)

    def close_iteration(
        self,
        iteration_id: str,
        *,
        resolution_state: str,
        status: str,
        selected_result_id: str | None = None,
    ) -> VideoIteration:
        iteration = self.load_iteration(iteration_id)
        iteration.resolution_state = resolution_state
        iteration.status = status
        iteration.selected_result_id = selected_result_id
        return self.store.upsert_video_iteration(iteration)

    def load_iteration(self, iteration_id: str) -> VideoIteration:
        iteration = self.store.get_video_iteration(iteration_id)
        if iteration is None:
            raise KeyError(f"Unknown iteration_id: {iteration_id}")
        return iteration

    def load_result(self, result_id: str) -> VideoResult:
        result = self.store.get_video_result(result_id)
        if result is None:
            raise KeyError(f"Unknown result_id: {result_id}")
        return result
