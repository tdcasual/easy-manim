from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from video_agent.adapters.storage.artifact_store import ArtifactStore
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.errors import AdmissionControlError
from video_agent.application.repair_state import build_repair_state_snapshot
from video_agent.application.revision_service import RevisionService
from video_agent.config import Settings
from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.domain.models import VideoTask


class CreateVideoTaskResult(BaseModel):
    task_id: str
    status: TaskStatus
    poll_after_ms: int
    resource_refs: list[str] = Field(default_factory=list)


class VideoTaskSnapshot(BaseModel):
    task_id: str
    status: TaskStatus
    phase: TaskPhase
    attempt_count: int
    parent_task_id: Optional[str] = None
    root_task_id: Optional[str] = None
    inherited_from_task_id: Optional[str] = None
    latest_validation_summary: dict[str, Any] = Field(default_factory=dict)
    artifact_summary: dict[str, Any] = Field(default_factory=dict)
    repair_state: dict[str, Any] = Field(default_factory=dict)
    auto_repair_summary: dict[str, Any] = Field(default_factory=dict)


class VideoResult(BaseModel):
    task_id: str
    status: TaskStatus
    ready: bool
    video_resource: Optional[str] = None
    preview_frame_resources: list[str] = Field(default_factory=list)
    script_resource: Optional[str] = None
    validation_report_resource: Optional[str] = None
    summary: Optional[str] = None


class TaskService:
    def __init__(
        self,
        store: SQLiteTaskStore,
        artifact_store: ArtifactStore,
        settings: Settings,
        revision_service: Optional[RevisionService] = None,
    ) -> None:
        self.store = store
        self.artifact_store = artifact_store
        self.settings = settings
        self.revision_service = revision_service or RevisionService()

    def create_video_task(
        self,
        prompt: str,
        idempotency_key: Optional[str] = None,
        output_profile: Optional[dict[str, Any]] = None,
        style_hints: Optional[dict[str, Any]] = None,
        validation_profile: Optional[dict[str, Any]] = None,
        feedback: Optional[str] = None,
    ) -> CreateVideoTaskResult:
        self._enforce_queue_capacity()
        task = VideoTask(
            prompt=prompt,
            feedback=feedback,
            output_profile=output_profile or {},
            style_hints=style_hints or {},
            validation_profile=validation_profile or {},
        )
        persisted = self.store.create_task(task, idempotency_key=idempotency_key)
        self.artifact_store.ensure_task_dirs(persisted.task_id)
        self.artifact_store.write_task_snapshot(persisted)
        self.store.append_event(persisted.task_id, "task_created", {"status": persisted.status.value})
        return CreateVideoTaskResult(
            task_id=persisted.task_id,
            status=persisted.status,
            poll_after_ms=self.settings.default_poll_after_ms,
            resource_refs=[self._task_resource_ref(persisted.task_id)],
        )

    def get_video_task(self, task_id: str) -> VideoTaskSnapshot:
        task = self._require_task(task_id)
        latest_validation = self.store.get_latest_validation(task_id)
        root_task_id = task.root_task_id or task.task_id
        root_task = self._require_task(root_task_id)
        repair_children = max(0, self.store.count_lineage_tasks(root_task_id) - 1)
        artifact_summary = {
            "script_count": len(self.store.list_artifacts(task_id, "current_script")),
            "video_count": len(self.store.list_artifacts(task_id, "final_video")),
            "preview_count": len(self.store.list_artifacts(task_id, "preview_frame")),
            "repair_children": repair_children,
        }
        validation_summary = latest_validation.model_dump(mode="json") if latest_validation else {}
        repair_state = build_repair_state_snapshot(root_task, repair_children)
        return VideoTaskSnapshot(
            task_id=task.task_id,
            status=task.status,
            phase=task.phase,
            attempt_count=task.attempt_count,
            parent_task_id=task.parent_task_id,
            root_task_id=task.root_task_id,
            inherited_from_task_id=task.inherited_from_task_id,
            latest_validation_summary=validation_summary,
            artifact_summary=artifact_summary,
            repair_state=repair_state.model_dump(mode="json"),
            auto_repair_summary=self._build_auto_repair_summary(root_task_id, repair_children),
        )

    def get_video_result(self, task_id: str) -> VideoResult:
        task = self._require_task(task_id)
        latest_validation = self.store.get_latest_validation(task_id)
        if task.status is not TaskStatus.COMPLETED:
            return VideoResult(task_id=task.task_id, status=task.status, ready=False)

        video_artifacts = self.store.list_artifacts(task_id, "final_video")
        preview_artifacts = self.store.list_artifacts(task_id, "preview_frame")
        script_artifacts = self.store.list_artifacts(task_id, "current_script")
        validation_artifacts = self.store.list_artifacts(task_id, "validation_report")

        return VideoResult(
            task_id=task.task_id,
            status=task.status,
            ready=True,
            video_resource=self._resource_ref(task_id, Path(video_artifacts[-1]["path"])),
            preview_frame_resources=[self._resource_ref(task_id, Path(item["path"])) for item in preview_artifacts],
            script_resource=self._resource_ref(task_id, Path(script_artifacts[-1]["path"])),
            validation_report_resource=self._resource_ref(task_id, Path(validation_artifacts[-1]["path"])),
            summary=(latest_validation.summary if latest_validation else None),
        )

    def revise_video_task(
        self,
        base_task_id: str,
        feedback: str,
        preserve_working_parts: bool = True,
    ) -> CreateVideoTaskResult:
        base_task = self._require_task(base_task_id)
        metadata = self.revision_service.build_metadata(
            base_task,
            revision_mode="preserve_context_revision" if preserve_working_parts else "full_regeneration",
            preserve_working_parts=preserve_working_parts,
        )
        child_task = self.revision_service.create_revision(
            base_task=base_task,
            feedback=feedback,
            preserve_working_parts=preserve_working_parts,
        )
        return self._persist_child_task(
            base_task=base_task,
            child_task=child_task,
            event_type="revision_created",
            event_payload={"parent_task_id": base_task.task_id, "feedback": feedback, **metadata},
        )

    def retry_video_task(self, task_id: str) -> CreateVideoTaskResult:
        base_task = self._require_task(task_id)
        if base_task.status is not TaskStatus.FAILED:
            raise ValueError("retry_video_task requires a failed parent task")
        self._enforce_attempt_limit(base_task.root_task_id)

        metadata = self.revision_service.build_metadata(
            base_task,
            revision_mode="full_regeneration",
            preserve_working_parts=True,
        )
        child_task = self.revision_service.create_retry(base_task)
        return self._persist_child_task(
            base_task=base_task,
            child_task=child_task,
            event_type="retry_created",
            event_payload={"parent_task_id": base_task.task_id, **metadata},
        )

    def create_auto_repair_task(self, task_id: str, feedback: str) -> CreateVideoTaskResult:
        base_task = self._require_task(task_id)
        if base_task.status is not TaskStatus.FAILED:
            raise ValueError("create_auto_repair_task requires a failed parent task")
        self._enforce_attempt_limit(base_task.root_task_id)

        metadata = self.revision_service.build_metadata(
            base_task,
            revision_mode="targeted_repair",
            preserve_working_parts=True,
        )
        child_task = self.revision_service.create_auto_repair(base_task, feedback=feedback)
        return self._persist_child_task(
            base_task=base_task,
            child_task=child_task,
            event_type="auto_repair_created",
            event_payload={"parent_task_id": base_task.task_id, "feedback": feedback, **metadata},
        )

    def cancel_video_task(self, task_id: str) -> None:
        task = self._require_task(task_id)
        task.status = TaskStatus.CANCELLED
        task.phase = TaskPhase.CANCELLED
        self.store.update_task(task)
        self.artifact_store.write_task_snapshot(task)
        self.store.append_event(task.task_id, "task_cancelled", {"status": task.status.value})

    def list_video_tasks(self, limit: int = 50, status: Optional[str] = None) -> list[dict[str, Any]]:
        return self.store.list_tasks(limit=limit, status=status)

    def get_task_events(self, task_id: str, limit: int = 200) -> list[dict[str, Any]]:
        self._require_task(task_id)
        return self.store.list_events(task_id, limit=limit)

    def _enforce_queue_capacity(self) -> None:
        active_count = self.store.count_tasks([TaskStatus.QUEUED.value, TaskStatus.RUNNING.value, TaskStatus.REVISING.value])
        if active_count >= self.settings.max_queued_tasks:
            raise AdmissionControlError(
                code="queue_full",
                message=f"Queue is full: {active_count} active tasks, limit is {self.settings.max_queued_tasks}",
            )

    def _enforce_attempt_limit(self, root_task_id: str) -> None:
        lineage_count = self.store.count_lineage_tasks(root_task_id)
        if lineage_count >= self.settings.max_attempts_per_root_task:
            raise AdmissionControlError(
                code="attempt_limit_reached",
                message=(
                    f"Retry limit reached for root task {root_task_id}: "
                    f"{lineage_count} tasks, limit is {self.settings.max_attempts_per_root_task}"
                ),
            )

    def _require_task(self, task_id: str) -> VideoTask:
        task = self.store.get_task(task_id)
        if task is None:
            raise KeyError(f"Unknown task_id: {task_id}")
        return task

    @staticmethod
    def _task_resource_ref(task_id: str) -> str:
        return f"video-task://{task_id}/task.json"

    def _resource_ref(self, task_id: str, file_path: Path) -> str:
        return self.artifact_store.resource_uri(task_id, file_path)

    def _build_auto_repair_summary(self, root_task_id: str, repair_children: int) -> dict[str, Any]:
        root_task = self._require_task(root_task_id)
        latest_decision = self._latest_auto_repair_decision(root_task_id)
        remaining_budget = max(0, self.settings.auto_repair_max_children_per_root - repair_children)
        latest_child_task_id = None
        if latest_decision is not None:
            latest_child_task_id = latest_decision.get("child_task_id")

        return {
            "enabled": self.settings.auto_repair_enabled,
            "repair_children": repair_children,
            "remaining_budget": remaining_budget,
            "stopped_reason": root_task.repair_stop_reason,
            "latest_child_task_id": latest_child_task_id,
        }

    def _latest_auto_repair_decision(self, root_task_id: str) -> dict[str, Any] | None:
        for event in reversed(self.store.list_events(root_task_id, limit=200)):
            if event["event_type"] == "auto_repair_decision":
                return event["payload"]
        return None

    def _persist_child_task(
        self,
        base_task: VideoTask,
        child_task: VideoTask,
        event_type: str,
        event_payload: dict[str, Any],
    ) -> CreateVideoTaskResult:
        persisted = self.store.create_task(child_task)
        self.artifact_store.ensure_task_dirs(persisted.task_id)
        self.artifact_store.write_task_snapshot(persisted)
        self.store.append_event(persisted.task_id, event_type, event_payload)
        return CreateVideoTaskResult(
            task_id=persisted.task_id,
            status=persisted.status,
            poll_after_ms=self.settings.default_poll_after_ms,
            resource_refs=[self._task_resource_ref(persisted.task_id)],
        )
