from __future__ import annotations

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.application.session_memory_service import SessionMemoryService
from video_agent.application.task_service import TaskService
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.domain.review_workflow_models import ReviewBundle


class ReviewBundleBuilder:
    def __init__(
        self,
        *,
        task_service: TaskService,
        store: SQLiteTaskStore,
        session_memory_service: SessionMemoryService | None,
    ) -> None:
        self.task_service = task_service
        self.store = store
        self.session_memory_service = session_memory_service

    def build(self, task_id: str, agent_principal: AgentPrincipal | None = None) -> ReviewBundle:
        if agent_principal is None:
            snapshot = self.task_service.get_video_task(task_id)
            result = self.task_service.get_video_result(task_id)
            events = self.task_service.get_task_events(task_id)
            task = self.store.get_task(task_id)
        else:
            snapshot = self.task_service.get_video_task_for_agent(task_id, agent_principal.agent_id)
            result = self.task_service.get_video_result_for_agent(task_id, agent_principal.agent_id)
            events = self.task_service.get_task_events_for_agent(task_id, agent_principal.agent_id)
            task = self.task_service.require_task_access(task_id, agent_principal.agent_id)
        session_memory_summary = ""
        if (
            task is not None
            and task.session_id is not None
            and self.session_memory_service is not None
        ):
            session_memory_summary = self.session_memory_service.summarize_session_memory(task.session_id).summary_text

        child_attempt_count = 0
        if snapshot.root_task_id is not None:
            child_attempt_count = max(0, self.store.count_lineage_tasks(snapshot.root_task_id) - 1)

        return ReviewBundle(
            task_id=snapshot.task_id,
            root_task_id=snapshot.root_task_id,
            attempt_count=snapshot.attempt_count,
            child_attempt_count=child_attempt_count,
            prompt="" if task is None else task.prompt,
            feedback=None if task is None else task.feedback,
            display_title=snapshot.display_title,
            status=snapshot.status.value,
            phase=snapshot.phase.value,
            latest_validation_summary=snapshot.latest_validation_summary,
            failure_contract=snapshot.failure_contract,
            task_events=events,
            session_memory_summary=session_memory_summary or "",
            video_resource=result.video_resource,
            preview_frame_resources=result.preview_frame_resources,
            script_resource=result.script_resource,
            validation_report_resource=result.validation_report_resource,
        )
