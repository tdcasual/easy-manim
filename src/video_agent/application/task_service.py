from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from video_agent.adapters.storage.artifact_store import ArtifactStore
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.agent_authorization_service import AgentAuthorizationService
from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.application.agent_learning_service import AgentLearningService
from video_agent.application.errors import AdmissionControlError
from video_agent.application.persistent_memory_service import PersistentMemoryContext, PersistentMemoryService
from video_agent.application.preference_resolver import (
    build_system_default_request_config,
    compute_profile_digest,
    resolve_effective_request_config,
)
from video_agent.application.repair_state import build_repair_state_snapshot
from video_agent.application.revision_service import RevisionService
from video_agent.application.session_memory_service import SessionMemoryService
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.domain.models import VideoTask


_DISPLAY_TITLE_SPLIT_REGEX = re.compile(r"[\n\r，,.;:：；？！!?]+")
_DISPLAY_TITLE_MAX_LENGTH = 20
_TITLE_PREFIXES_TO_STRIP = (
    "请帮我做一个",
    "请帮我生成一个",
    "帮我做一个",
    "帮我生成一个",
    "请制作一个",
    "请创建一个",
    "请做一个",
    "制作一个",
    "生成一个",
    "创建一个",
    "设计一个",
    "做一个",
    "做个",
    "画一个",
    "画个",
)


class CreateVideoTaskResult(BaseModel):
    task_id: str
    status: TaskStatus
    poll_after_ms: int
    resource_refs: list[str] = Field(default_factory=list)
    display_title: Optional[str] = None
    title_source: Optional[str] = None


class VideoTaskSnapshot(BaseModel):
    task_id: str
    agent_id: Optional[str] = None
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
    failure_contract: dict[str, Any] | None = None


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
        authorization_service: AgentAuthorizationService | None = None,
        agent_learning_service: AgentLearningService | None = None,
        session_memory_service: SessionMemoryService | None = None,
        persistent_memory_service: PersistentMemoryService | None = None,
    ) -> None:
        self.store = store
        self.artifact_store = artifact_store
        self.settings = settings
        self.revision_service = revision_service or RevisionService()
        self.authorization_service = authorization_service or AgentAuthorizationService()
        self.agent_learning_service = agent_learning_service
        self.session_memory_service = session_memory_service
        self.persistent_memory_service = persistent_memory_service

    def create_video_task(
        self,
        prompt: str,
        idempotency_key: Optional[str] = None,
        output_profile: Optional[dict[str, Any]] = None,
        style_hints: Optional[dict[str, Any]] = None,
        validation_profile: Optional[dict[str, Any]] = None,
        feedback: Optional[str] = None,
        session_id: Optional[str] = None,
        memory_ids: list[str] | None = None,
        agent_principal: AgentPrincipal | None = None,
    ) -> CreateVideoTaskResult:
        self._enforce_queue_capacity()
        principal = self._resolve_agent_principal(agent_principal)
        self._authorize_action(principal, "task:create")
        persistent_memory = self._resolve_persistent_memory_context(principal.agent_id, memory_ids)
        system_defaults = build_system_default_request_config(
            default_quality_preset=self.settings.default_quality_preset,
            default_frame_rate=self.settings.default_frame_rate,
            default_pixel_width=self.settings.default_pixel_width,
            default_pixel_height=self.settings.default_pixel_height,
        )
        effective_request_profile = resolve_effective_request_config(
            system_defaults=system_defaults,
            profile_json=principal.profile.profile_json,
            token_override_json=principal.token.override_json,
            request_overrides=self._build_request_overrides(
                output_profile=output_profile,
                style_hints=style_hints,
                validation_profile=validation_profile,
            ),
        )
        display_title, title_source = self._derive_display_title(prompt)
        task = VideoTask(
            agent_id=principal.agent_id,
            session_id=session_id,
            prompt=prompt,
            feedback=feedback,
            selected_memory_ids=persistent_memory.memory_ids,
            persistent_memory_context_summary=persistent_memory.summary_text,
            persistent_memory_context_digest=persistent_memory.summary_digest,
            profile_version=principal.profile.profile_version,
            output_profile=effective_request_profile.get("output_profile", output_profile or {}),
            style_hints=effective_request_profile.get("style_hints", style_hints or {}),
            validation_profile=effective_request_profile.get("validation_profile", validation_profile or {}),
            effective_request_profile=effective_request_profile,
            effective_profile_digest=compute_profile_digest(effective_request_profile),
            effective_policy_flags=dict(principal.profile.policy_json),
            display_title=display_title,
            title_source=title_source,
        )
        persisted = self.store.create_task(task, idempotency_key=idempotency_key)
        self.artifact_store.ensure_task_dirs(persisted.task_id)
        self.artifact_store.write_task_snapshot(persisted)
        self.store.append_event(persisted.task_id, "task_created", {"status": persisted.status.value})
        if self.session_memory_service is not None:
            self.session_memory_service.record_task_created(persisted, attempt_kind="create")
        return CreateVideoTaskResult(
            task_id=persisted.task_id,
            status=persisted.status,
            poll_after_ms=self.settings.default_poll_after_ms,
            resource_refs=[self._task_resource_ref(persisted.task_id)],
            display_title=persisted.display_title,
            title_source=persisted.title_source,
        )

    def get_video_task(self, task_id: str) -> VideoTaskSnapshot:
        task = self._require_task(task_id)
        return self._build_video_task_snapshot(task)

    def get_video_task_for_agent(self, task_id: str, agent_id: str) -> VideoTaskSnapshot:
        task = self.require_task_access(task_id, agent_id)
        return self._build_video_task_snapshot(task)

    def get_video_result_for_agent(self, task_id: str, agent_id: str) -> VideoResult:
        self.require_task_access(task_id, agent_id)
        return self.get_video_result(task_id)

    def list_video_tasks_for_agent(self, agent_id: str, limit: int = 50, status: Optional[str] = None) -> list[dict[str, Any]]:
        return self.store.list_tasks(limit=limit, status=status, agent_id=agent_id)

    def get_task_events_for_agent(self, task_id: str, agent_id: str, limit: int = 200) -> list[dict[str, Any]]:
        self.require_task_access(task_id, agent_id)
        return self.store.list_events(task_id, limit=limit)

    def get_failure_contract_for_agent(self, task_id: str, agent_id: str) -> dict[str, Any] | None:
        self.require_task_access(task_id, agent_id)
        return self.artifact_store.read_failure_contract(task_id)

    def require_task_access(self, task_id: str, agent_id: str) -> VideoTask:
        task = self._require_task(task_id)
        if task.agent_id != agent_id:
            raise PermissionError(f"Task {task_id} is not owned by agent {agent_id}")
        return task

    def _build_video_task_snapshot(self, task: VideoTask) -> VideoTaskSnapshot:
        task_id = task.task_id
        latest_validation = self.store.get_latest_validation(task_id)
        root_task_id = task.root_task_id or task.task_id
        root_task = self._require_task(root_task_id)
        repair_children = max(0, self.store.count_lineage_tasks(root_task_id) - 1)
        failure_contract = self.get_failure_contract(task_id) if task.status is TaskStatus.FAILED else None
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
            agent_id=task.agent_id,
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
            failure_contract=failure_contract,
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
        session_id: Optional[str] = None,
        memory_ids: list[str] | None = None,
        agent_principal: AgentPrincipal | None = None,
    ) -> CreateVideoTaskResult:
        principal = self._resolve_agent_principal(agent_principal)
        self._authorize_action(principal, "task:mutate")
        base_task = self._require_authorized_task(base_task_id, principal)
        persistent_memory = self._resolve_persistent_memory_context(principal.agent_id, memory_ids)
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
            attempt_kind="revise",
            session_id=session_id,
            event_type="revision_created",
            event_payload={"parent_task_id": base_task.task_id, "feedback": feedback, **metadata},
            persistent_memory=persistent_memory,
        )

    def retry_video_task(
        self,
        task_id: str,
        session_id: Optional[str] = None,
        agent_principal: AgentPrincipal | None = None,
    ) -> CreateVideoTaskResult:
        principal = self._resolve_agent_principal(agent_principal)
        self._authorize_action(principal, "task:mutate")
        base_task = self._require_authorized_task(task_id, principal)
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
            attempt_kind="retry",
            session_id=session_id,
            event_type="retry_created",
            event_payload={"parent_task_id": base_task.task_id, **metadata},
        )

    def create_auto_repair_task(self, task_id: str, feedback: str, session_id: Optional[str] = None) -> CreateVideoTaskResult:
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
            attempt_kind="auto_repair",
            session_id=session_id,
            event_type="auto_repair_created",
            event_payload={"parent_task_id": base_task.task_id, "feedback": feedback, **metadata},
        )

    def cancel_video_task(self, task_id: str, agent_principal: AgentPrincipal | None = None) -> None:
        principal = self._resolve_agent_principal(agent_principal)
        self._authorize_action(principal, "task:mutate")
        task = self._require_authorized_task(task_id, principal)
        task.status = TaskStatus.CANCELLED
        task.phase = TaskPhase.CANCELLED
        self.store.update_task(task)
        self.artifact_store.write_task_snapshot(task)
        self.store.append_event(task.task_id, "task_cancelled", {"status": task.status.value})

    def list_video_tasks(self, limit: int = 50, status: Optional[str] = None) -> list[dict[str, Any]]:
        return self.store.list_tasks(limit=limit, status=status)

    def _derive_display_title(self, prompt: str) -> tuple[str, str]:
        fragment = re.sub(r"\s+", " ", prompt or "").strip()
        if not fragment:
            return fragment, "prompt"

        fragment = _DISPLAY_TITLE_SPLIT_REGEX.split(fragment)[0].strip()
        for prefix in _TITLE_PREFIXES_TO_STRIP:
            if fragment.startswith(prefix):
                fragment = fragment[len(prefix):].strip()
                break

        fragment = fragment.strip("。.,;:，；！？!? '\"“”‘’")
        if not fragment:
            fragment = re.sub(r"\s+", " ", prompt or "").strip()

        if len(fragment) > _DISPLAY_TITLE_MAX_LENGTH:
            fragment = fragment[:_DISPLAY_TITLE_MAX_LENGTH].rstrip("。.,;:，；！？!? '\"“”‘’")

        fragment = fragment.strip()
        if not fragment:
            fragment = re.sub(r"\s+", " ", prompt or "").strip()

        return fragment, "prompt"

    def get_task_events(self, task_id: str, limit: int = 200) -> list[dict[str, Any]]:
        self._require_task(task_id)
        return self.store.list_events(task_id, limit=limit)

    def get_failure_contract(self, task_id: str) -> dict[str, Any] | None:
        self._require_task(task_id)
        return self.artifact_store.read_failure_contract(task_id)

    def _resolve_agent_principal(self, agent_principal: AgentPrincipal | None) -> AgentPrincipal:
        if agent_principal is not None:
            return agent_principal
        if self.settings.auth_mode == "required":
            raise AdmissionControlError(
                code="agent_not_authenticated",
                message="Agent authentication is required for this operation",
            )

        anonymous_agent_id = self.settings.anonymous_agent_id
        return AgentPrincipal(
            agent_id=anonymous_agent_id,
            profile=AgentProfile(agent_id=anonymous_agent_id, name="Local Anonymous"),
            token=AgentToken(token_hash="anonymous", agent_id=anonymous_agent_id),
        )

    def _require_authorized_task(self, task_id: str, principal: AgentPrincipal) -> VideoTask:
        if self.settings.auth_mode != "required":
            return self._require_task(task_id)
        return self.require_task_access(task_id, principal.agent_id)

    def _authorize_action(self, principal: AgentPrincipal, action: str) -> None:
        self.authorization_service.require_allowed(principal.profile, principal.token, action)

    @staticmethod
    def _build_request_overrides(
        *,
        output_profile: dict[str, Any] | None,
        style_hints: dict[str, Any] | None,
        validation_profile: dict[str, Any] | None,
    ) -> dict[str, Any]:
        overrides: dict[str, Any] = {}
        if output_profile:
            overrides["output_profile"] = output_profile
        if style_hints:
            overrides["style_hints"] = style_hints
        if validation_profile:
            overrides["validation_profile"] = validation_profile
        return overrides

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
        attempt_kind: str,
        session_id: Optional[str],
        event_type: str,
        event_payload: dict[str, Any],
        persistent_memory: PersistentMemoryContext | None = None,
    ) -> CreateVideoTaskResult:
        effective_session_id = child_task.session_id or base_task.session_id or session_id
        if effective_session_id is not None:
            child_task.session_id = effective_session_id

        self._apply_memory_context(session_id=effective_session_id, child_task=child_task)
        self._apply_persistent_memory_context(child_task=child_task, persistent_memory=persistent_memory)
        persisted = self.store.create_task(child_task)
        self.artifact_store.ensure_task_dirs(persisted.task_id)
        self.artifact_store.write_task_snapshot(persisted)
        self.store.append_event(persisted.task_id, event_type, event_payload)
        if self.session_memory_service is not None:
            self.session_memory_service.record_task_created(persisted, attempt_kind=attempt_kind)
        return CreateVideoTaskResult(
            task_id=persisted.task_id,
            status=persisted.status,
            poll_after_ms=self.settings.default_poll_after_ms,
            resource_refs=[self._task_resource_ref(persisted.task_id)],
            display_title=persisted.display_title,
            title_source=persisted.title_source,
        )

    def _apply_memory_context(self, session_id: str | None, child_task: VideoTask) -> None:
        if self.session_memory_service is None or session_id is None:
            return

        summary = self.session_memory_service.summarize_session_memory(session_id)
        if not summary.summary_text:
            return

        child_task.memory_context_summary = summary.summary_text
        child_task.memory_context_digest = summary.summary_digest

    def _apply_persistent_memory_context(
        self,
        *,
        child_task: VideoTask,
        persistent_memory: PersistentMemoryContext | None,
    ) -> None:
        if persistent_memory is None:
            return

        child_task.selected_memory_ids = list(persistent_memory.memory_ids)
        child_task.persistent_memory_context_summary = persistent_memory.summary_text
        child_task.persistent_memory_context_digest = persistent_memory.summary_digest

    def _resolve_persistent_memory_context(
        self,
        agent_id: str,
        memory_ids: list[str] | None,
    ) -> PersistentMemoryContext:
        if self.persistent_memory_service is None:
            return PersistentMemoryContext(memory_ids=list(memory_ids or []))
        return self.persistent_memory_service.resolve_memory_context(agent_id, memory_ids)
