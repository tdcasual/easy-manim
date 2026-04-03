from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from video_agent.adapters.storage.artifact_store import ArtifactStore
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.agent_authorization_service import AgentAuthorizationService
from video_agent.application.case_memory_service import CaseMemoryService
from video_agent.application.delivery_case_service import DeliveryCaseService
from video_agent.application.branch_arbitration import build_arbitration_summary, build_branch_scoreboard
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
from video_agent.domain.strategy_models import StrategyProfile


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
    thread_id: str | None = None
    iteration_id: str | None = None
    agent_id: Optional[str] = None
    target_participant_id: str | None = None
    target_agent_id: str | None = None
    target_agent_role: str | None = None
    strategy_profile_id: Optional[str] = None
    display_title: Optional[str] = None
    title_source: Optional[str] = None
    risk_level: Optional[str] = None
    generation_mode: Optional[str] = None
    quality_gate_status: Optional[str] = None
    accepted_as_best: bool = False
    accepted_version_rank: Optional[int] = None
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
    delivery_status: str | None = None
    resolved_task_id: str | None = None
    completion_mode: str | None = None
    delivery_tier: str | None = None
    delivery_stop_reason: str | None = None


class VideoResult(BaseModel):
    task_id: str
    status: TaskStatus
    ready: bool
    video_resource: Optional[str] = None
    preview_frame_resources: list[str] = Field(default_factory=list)
    script_resource: Optional[str] = None
    validation_report_resource: Optional[str] = None
    summary: Optional[str] = None
    delivery_status: str | None = None
    resolved_task_id: str | None = None
    completion_mode: str | None = None
    delivery_tier: str | None = None
    delivery_stop_reason: str | None = None


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
        delivery_case_service: DeliveryCaseService | None = None,
        case_memory_service: CaseMemoryService | None = None,
    ) -> None:
        self.store = store
        self.artifact_store = artifact_store
        self.settings = settings
        self.revision_service = revision_service or RevisionService()
        self.authorization_service = authorization_service or AgentAuthorizationService()
        self.agent_learning_service = agent_learning_service
        self.session_memory_service = session_memory_service
        self.persistent_memory_service = persistent_memory_service
        self.delivery_case_service = delivery_case_service
        self.case_memory_service = case_memory_service

    def create_video_task(
        self,
        prompt: str,
        idempotency_key: Optional[str] = None,
        output_profile: Optional[dict[str, Any]] = None,
        style_hints: Optional[dict[str, Any]] = None,
        validation_profile: Optional[dict[str, Any]] = None,
        strategy_prompt_cluster: str | None = None,
        feedback: Optional[str] = None,
        session_id: Optional[str] = None,
        memory_ids: list[str] | None = None,
        thread_id: str | None = None,
        iteration_id: str | None = None,
        result_id: str | None = None,
        execution_kind: str | None = None,
        target_participant_id: str | None = None,
        target_agent_id: str | None = None,
        target_agent_role: str | None = None,
        agent_principal: AgentPrincipal | None = None,
    ) -> CreateVideoTaskResult:
        self._enforce_queue_capacity()
        principal = self._resolve_agent_principal(agent_principal)
        self._authorize_action(principal, "task:create")
        persistent_memory = self.resolve_persistent_memory_context_for_agent(principal.agent_id, memory_ids)
        active_strategy = self._resolve_active_strategy_profile(
            strategy_prompt_cluster=strategy_prompt_cluster,
            prompt=prompt,
        )
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
            strategy_profile_json=None if active_strategy is None else self._strategy_request_profile(active_strategy),
            request_overrides=self._build_request_overrides(
                output_profile=output_profile,
                style_hints=style_hints,
                validation_profile=validation_profile,
            ),
        )
        display_title, title_source = self._derive_display_title(prompt)
        task = VideoTask(
            thread_id=thread_id,
            iteration_id=iteration_id,
            result_id=result_id,
            execution_kind=execution_kind,
            target_participant_id=target_participant_id,
            target_agent_id=target_agent_id,
            target_agent_role=target_agent_role,
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
            strategy_profile_id=None if active_strategy is None else active_strategy.strategy_id,
            delivery_status="pending",
        )
        persisted = self.store.create_task(task, idempotency_key=idempotency_key)
        self.artifact_store.ensure_task_dirs(persisted.task_id)
        self.artifact_store.write_task_snapshot(persisted)
        self.store.append_event(persisted.task_id, "task_created", {"status": persisted.status.value})
        if self.delivery_case_service is not None:
            _, created_case = self.delivery_case_service.ensure_case_for_task(persisted)
            if created_case:
                self.delivery_case_service.record_case_created(persisted)
            self.delivery_case_service.queue_generator_run(task=persisted)
            self.delivery_case_service.sync_case_for_root(persisted.root_task_id or persisted.task_id)
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

    def get_scene_spec(self, task_id: str) -> dict[str, Any] | None:
        self._require_task(task_id)
        return self.artifact_store.read_scene_spec(task_id)

    def get_scene_spec_for_agent(self, task_id: str, agent_id: str) -> dict[str, Any] | None:
        self.require_task_access(task_id, agent_id)
        return self.artifact_store.read_scene_spec(task_id)

    def get_recovery_plan(self, task_id: str) -> dict[str, Any] | None:
        self._require_task(task_id)
        return self.artifact_store.read_recovery_plan(task_id)

    def get_recovery_plan_for_agent(self, task_id: str, agent_id: str) -> dict[str, Any] | None:
        self.require_task_access(task_id, agent_id)
        return self.artifact_store.read_recovery_plan(task_id)

    def get_quality_score(self, task_id: str) -> dict[str, Any] | None:
        self._require_task(task_id)
        scorecard = self.store.get_task_quality_score(task_id)
        if scorecard is not None:
            return scorecard.model_dump(mode="json")
        return self.artifact_store.read_quality_score(task_id)

    def get_quality_score_for_agent(self, task_id: str, agent_id: str) -> dict[str, Any] | None:
        self.require_task_access(task_id, agent_id)
        return self.get_quality_score(task_id)

    def accept_best_version(
        self,
        task_id: str,
        agent_principal: AgentPrincipal | None = None,
    ) -> VideoTaskSnapshot:
        principal = self._resolve_agent_principal(agent_principal)
        self._authorize_action(principal, "task:mutate")
        accepted_task = self._require_authorized_task(task_id, principal)
        return self.accept_authorized_task(accepted_task)

    def accept_authorized_task(self, accepted_task: VideoTask) -> VideoTaskSnapshot:
        if accepted_task.status is not TaskStatus.COMPLETED:
            raise ValueError("accept_best_requires_completed_task")

        root_task_id = accepted_task.root_task_id or accepted_task.task_id
        lineage = self.store.list_lineage_tasks(root_task_id)
        root_task = self._require_task(root_task_id)
        delivery_case = self.store.get_delivery_case(root_task_id)
        previous_selected_task_id = root_task.resolved_task_id
        arbitration_summary = build_arbitration_summary(
            branch_scoreboard=build_branch_scoreboard(
                lineage_tasks=lineage,
                scorecards_by_task_id={
                    candidate.task_id: self.get_quality_score(candidate.task_id)
                    for candidate in lineage
                },
                selected_task_id=previous_selected_task_id,
                active_task_id=delivery_case.active_task_id if delivery_case is not None else accepted_task.task_id,
            ),
            selected_task_id=previous_selected_task_id,
            active_task_id=delivery_case.active_task_id if delivery_case is not None else accepted_task.task_id,
        )
        accepted_rank = 1
        for index, candidate in enumerate(lineage, start=1):
            is_selected = candidate.task_id == accepted_task.task_id
            candidate.accepted_as_best = is_selected
            candidate.accepted_version_rank = index if is_selected else None
            if is_selected:
                accepted_rank = index
            self.store.update_task(candidate)
            self.artifact_store.write_task_snapshot(candidate)

        root_task.status = TaskStatus.COMPLETED
        root_task.phase = TaskPhase.COMPLETED
        root_task.delivery_status = "delivered"
        root_task.resolved_task_id = accepted_task.task_id
        root_task.completion_mode = accepted_task.completion_mode
        root_task.delivery_tier = accepted_task.delivery_tier
        root_task.delivery_stop_reason = None
        root_task.accepted_as_best = accepted_task.task_id == root_task.task_id
        root_task.accepted_version_rank = accepted_rank if root_task.accepted_as_best else None
        self.store.update_task(root_task)
        self.artifact_store.write_task_snapshot(root_task)

        self.store.append_event(
            accepted_task.task_id,
            "task_accepted_as_best",
            {
                "root_task_id": root_task_id,
                "accepted_version_rank": accepted_rank,
                "previous_selected_task_id": previous_selected_task_id,
                "arbitration_summary": arbitration_summary,
            },
        )
        if self.delivery_case_service is not None:
            self.delivery_case_service.sync_case_for_root(root_task_id)
            self.delivery_case_service.record_winner_selected(
                selected_task=accepted_task,
                previous_selected_task_id=previous_selected_task_id,
                arbitration_summary=arbitration_summary,
            )
        self._record_case_memory_branch_state(
            root_task_id=root_task_id,
            branch_scoreboard=build_branch_scoreboard(
                lineage_tasks=self.store.list_lineage_tasks(root_task_id),
                scorecards_by_task_id={
                    candidate.task_id: self.get_quality_score(candidate.task_id)
                    for candidate in self.store.list_lineage_tasks(root_task_id)
                },
                selected_task_id=accepted_task.task_id,
                active_task_id=accepted_task.task_id,
            ),
            arbitration_summary=arbitration_summary,
        )
        self._record_case_memory_decision(
            root_task_id=root_task_id,
            action="winner_selected",
            task_id=accepted_task.task_id,
            details={
                "previous_selected_task_id": previous_selected_task_id,
                "recommended_action": arbitration_summary.get("recommended_action"),
                "recommended_task_id": arbitration_summary.get("recommended_task_id"),
            },
        )
        return self.get_video_task(accepted_task.task_id)

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
            thread_id=task.thread_id,
            iteration_id=task.iteration_id,
            agent_id=task.agent_id,
            target_participant_id=task.target_participant_id,
            target_agent_id=task.target_agent_id,
            target_agent_role=task.target_agent_role,
            strategy_profile_id=task.strategy_profile_id,
            display_title=task.display_title,
            title_source=task.title_source,
            risk_level=task.risk_level,
            generation_mode=task.generation_mode,
            quality_gate_status=task.quality_gate_status,
            accepted_as_best=task.accepted_as_best,
            accepted_version_rank=task.accepted_version_rank,
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
            delivery_status=task.delivery_status,
            resolved_task_id=task.resolved_task_id,
            completion_mode=task.completion_mode,
            delivery_tier=task.delivery_tier,
            delivery_stop_reason=task.delivery_stop_reason,
        )

    def get_video_result(self, task_id: str) -> VideoResult:
        task = self._require_task(task_id)
        latest_validation = self.store.get_latest_validation(task_id)
        resolved_task = self._resolved_result_task(task)
        result_task_id = task.task_id if resolved_task is None else resolved_task.task_id
        result_validation = latest_validation if result_task_id == task.task_id else self.store.get_latest_validation(result_task_id)

        video_resource = self._latest_artifact_resource(
            result_task_id,
            "final_video",
            fallback_paths=[self.artifact_store.final_video_path(result_task_id)],
        )
        preview_frame_resources = self._artifact_resources(
            result_task_id,
            "preview_frame",
            fallback_paths=sorted(
                path
                for path in self.artifact_store.previews_dir(result_task_id).glob("*.png")
                if path.is_file()
            ),
        )
        script_resource = self._latest_artifact_resource(
            result_task_id,
            "current_script",
            fallback_paths=[self.artifact_store.script_path(result_task_id)],
        )
        validation_report_resource = self._latest_artifact_resource(
            result_task_id,
            "validation_report",
            fallback_paths=sorted(
                path
                for path in self.artifact_store.task_dir(result_task_id).glob("validations/validation_report_v*.json")
                if path.is_file()
            ),
        )

        return VideoResult(
            task_id=task.task_id,
            status=task.status if resolved_task is None else resolved_task.status,
            ready=resolved_task is not None,
            video_resource=video_resource,
            preview_frame_resources=preview_frame_resources,
            script_resource=script_resource,
            validation_report_resource=validation_report_resource,
            summary=(result_validation.summary if result_validation else latest_validation.summary if latest_validation else None),
            delivery_status=task.delivery_status,
            resolved_task_id=task.resolved_task_id,
            completion_mode=task.completion_mode,
            delivery_tier=task.delivery_tier,
            delivery_stop_reason=task.delivery_stop_reason,
        )

    def revise_video_task(
        self,
        base_task_id: str,
        feedback: str,
        preserve_working_parts: bool = True,
        session_id: Optional[str] = None,
        memory_ids: list[str] | None = None,
        thread_id: str | None = None,
        iteration_id: str | None = None,
        execution_kind: str | None = None,
        target_participant_id: str | None = None,
        target_agent_id: str | None = None,
        target_agent_role: str | None = None,
        agent_principal: AgentPrincipal | None = None,
    ) -> CreateVideoTaskResult:
        principal = self._resolve_agent_principal(agent_principal)
        self._authorize_action(principal, "task:mutate")
        base_task = self._require_authorized_task(base_task_id, principal)
        persistent_memory = (
            self._resolve_owner_revision_persistent_memory(
                base_task=base_task,
                agent_id=principal.agent_id,
            )
            if memory_ids is None
            else self.resolve_persistent_memory_context_for_agent(principal.agent_id, memory_ids)
        )
        return self.revise_authorized_task(
            base_task=base_task,
            feedback=feedback,
            preserve_working_parts=preserve_working_parts,
            session_id=session_id,
            persistent_memory=persistent_memory,
            thread_id=thread_id,
            iteration_id=iteration_id,
            execution_kind=execution_kind,
            target_participant_id=target_participant_id,
            target_agent_id=target_agent_id,
            target_agent_role=target_agent_role,
        )

    def revise_authorized_task(
        self,
        *,
        base_task: VideoTask,
        feedback: str,
        preserve_working_parts: bool,
        session_id: Optional[str],
        persistent_memory: PersistentMemoryContext | None,
        thread_id: str | None = None,
        iteration_id: str | None = None,
        execution_kind: str | None = None,
        target_participant_id: str | None = None,
        target_agent_id: str | None = None,
        target_agent_role: str | None = None,
    ) -> CreateVideoTaskResult:
        if self._is_completed_delivery_candidate(base_task):
            return self._create_challenger_child_task(
                base_task=base_task,
                feedback=feedback,
                session_id=session_id,
                persistent_memory=persistent_memory,
            )
        effective_feedback = self._augment_feedback_with_case_memory(base_task, feedback)
        metadata = self.revision_service.build_metadata(
            base_task,
            revision_mode="preserve_context_revision" if preserve_working_parts else "full_regeneration",
            preserve_working_parts=preserve_working_parts,
        )
        child_task = self.revision_service.create_revision(
            base_task=base_task,
            feedback=effective_feedback,
            preserve_working_parts=preserve_working_parts,
        )
        return self._persist_child_task(
            base_task=base_task,
            child_task=child_task,
            attempt_kind="revise",
            session_id=session_id,
            event_type="revision_created",
            event_payload={
                "parent_task_id": base_task.task_id,
                "feedback": feedback,
                "effective_feedback": effective_feedback,
                **metadata,
            },
            persistent_memory=persistent_memory,
            thread_id=thread_id,
            iteration_id=iteration_id,
            execution_kind=execution_kind,
            target_participant_id=target_participant_id,
            target_agent_id=target_agent_id,
            target_agent_role=target_agent_role,
        )

    def create_challenger_task(
        self,
        task_id: str,
        *,
        feedback: str,
        session_id: Optional[str] = None,
    ) -> CreateVideoTaskResult:
        base_task = self._require_task(task_id)
        return self._create_challenger_child_task(
            base_task=base_task,
            feedback=feedback,
            session_id=session_id,
            persistent_memory=self.inherit_persistent_memory_context(base_task),
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
        return self.retry_authorized_task(
            base_task=base_task,
            session_id=session_id,
        )

    def retry_authorized_task(
        self,
        *,
        base_task: VideoTask,
        session_id: Optional[str],
    ) -> CreateVideoTaskResult:
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
        effective_feedback = self._augment_feedback_with_case_memory(base_task, feedback)

        metadata = self.revision_service.build_metadata(
            base_task,
            revision_mode="targeted_repair",
            preserve_working_parts=True,
        )
        child_task = self.revision_service.create_auto_repair(base_task, feedback=effective_feedback)
        child_task.completion_mode = "repaired"
        child_task.delivery_status = "pending"
        return self._persist_child_task(
            base_task=base_task,
            child_task=child_task,
            attempt_kind="auto_repair",
            session_id=session_id,
            event_type="auto_repair_created",
            event_payload={
                "parent_task_id": base_task.task_id,
                "feedback": feedback,
                "effective_feedback": effective_feedback,
                **metadata,
            },
        )

    def create_degraded_delivery_task(
        self,
        task_id: str,
        *,
        feedback: str,
        generation_mode: str | None = None,
        style_hints: dict[str, Any] | None = None,
        output_profile: dict[str, Any] | None = None,
        validation_profile: dict[str, Any] | None = None,
        session_id: Optional[str] = None,
    ) -> CreateVideoTaskResult:
        base_task = self._require_task(task_id)
        if base_task.status is not TaskStatus.FAILED:
            raise ValueError("create_degraded_delivery_task requires a failed parent task")
        self._enforce_attempt_limit(base_task.root_task_id)
        effective_feedback = self._augment_feedback_with_case_memory(base_task, feedback)

        metadata = self.revision_service.build_metadata(
            base_task,
            revision_mode="delivery_degrade",
            preserve_working_parts=False,
        )
        child_task = self.revision_service.create_revision(
            base_task,
            feedback=effective_feedback,
            preserve_working_parts=False,
        )
        child_task.completion_mode = "degraded"
        child_task.delivery_status = "pending"
        if generation_mode is not None:
            child_task.generation_mode = generation_mode
            child_task.delivery_tier = generation_mode
        if style_hints:
            child_task.style_hints = {**child_task.style_hints, **style_hints}
        if output_profile:
            child_task.output_profile = {**child_task.output_profile, **output_profile}
        if validation_profile:
            child_task.validation_profile = {**child_task.validation_profile, **validation_profile}
        return self._persist_child_task(
            base_task=base_task,
            child_task=child_task,
            attempt_kind="delivery_degrade",
            session_id=session_id,
            event_type="delivery_degraded_created",
            event_payload={
                "parent_task_id": base_task.task_id,
                "feedback": feedback,
                "effective_feedback": effective_feedback,
                "generation_mode": generation_mode,
                "style_hints": style_hints or {},
                "output_profile": output_profile or {},
                **metadata,
            },
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

    def list_recent_videos_for_agent(self, agent_id: str, limit: int = 12) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        rows = self.store.list_tasks(
            limit=None,
            status=TaskStatus.COMPLETED.value,
            agent_id=agent_id,
            order_by="updated_at",
        )
        for row in rows:
            task_id = row["task_id"]
            task_dir = self.artifact_store.task_dir(task_id)
            final_video_path = task_dir / "artifacts" / "final_video.mp4"
            if not final_video_path.exists():
                continue
            preview_dir = task_dir / "artifacts" / "previews"
            preview_path: Path | None = None
            if preview_dir.exists():
                frames = sorted(p for p in preview_dir.glob("*.png") if p.is_file())
                if frames:
                    preview_path = frames[-1]
            latest_validation = self.store.get_latest_validation(task_id)
            summary = latest_validation.summary if latest_validation else None
            candidates.append(
                {
                    "task_id": task_id,
                    "thread_id": row.get("thread_id"),
                    "display_title": row.get("display_title"),
                    "title_source": row.get("title_source"),
                    "status": row["status"],
                    "updated_at": row["updated_at"],
                    "latest_summary": summary,
                    "video_path": final_video_path,
                    "preview_path": preview_path,
                }
            )
            if len(candidates) >= limit:
                break
        return candidates

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

    def require_owner_task(self, task_id: str, agent_principal: AgentPrincipal | None, *, action: str) -> VideoTask:
        principal = self._resolve_agent_principal(agent_principal)
        self._authorize_action(principal, action)
        return self._require_authorized_task(task_id, principal)

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

    @staticmethod
    def _strategy_request_profile(strategy: StrategyProfile) -> dict[str, Any]:
        overrides: dict[str, Any] = {}
        for key in ("output_profile", "style_hints", "validation_profile"):
            value = strategy.params.get(key)
            if isinstance(value, dict) and value:
                overrides[key] = value
        return overrides

    @staticmethod
    def _strategy_routing_keywords(strategy: StrategyProfile) -> list[str]:
        routing = strategy.params.get("routing")
        if not isinstance(routing, dict):
            return []
        keywords = routing.get("keywords")
        if not isinstance(keywords, list):
            return []
        normalized: list[str] = []
        for item in keywords:
            text = str(item).strip().casefold()
            if text and text not in normalized:
                normalized.append(text)
        return normalized

    def _route_active_strategy_profile(self, prompt: str) -> StrategyProfile | None:
        normalized_prompt = prompt.casefold()
        candidates: list[tuple[int, int, str, StrategyProfile]] = []
        for strategy in self.store.list_strategy_profiles(status="active"):
            if strategy.scope != "global" or strategy.prompt_cluster is None:
                continue
            matched_keywords = [
                keyword for keyword in self._strategy_routing_keywords(strategy) if keyword in normalized_prompt
            ]
            if not matched_keywords:
                continue
            candidates.append(
                (
                    len(matched_keywords),
                    max(len(keyword) for keyword in matched_keywords),
                    strategy.strategy_id,
                    strategy,
                )
            )
        if not candidates:
            return None
        candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
        return candidates[0][3]

    def _resolve_active_strategy_profile(self, strategy_prompt_cluster: str | None, *, prompt: str) -> StrategyProfile | None:
        normalized_cluster = (strategy_prompt_cluster or "").strip() or None
        if normalized_cluster is not None:
            strategy = self.store.get_active_strategy_profile(scope="global", prompt_cluster=normalized_cluster)
            if strategy is not None:
                return strategy
            return self.store.get_active_strategy_profile(scope="global", prompt_cluster=None)
        routed = self._route_active_strategy_profile(prompt)
        if routed is not None:
            return routed
        return self.store.get_active_strategy_profile(scope="global", prompt_cluster=None)

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

    def _enforce_workflow_child_budget(self, root_task_id: str) -> None:
        child_count = max(0, self.store.count_lineage_tasks(root_task_id) - 1)
        if child_count >= self.settings.multi_agent_workflow_max_child_attempts:
            raise AdmissionControlError(
                code="workflow_budget_exhausted",
                message=(
                    f"Workflow child budget exhausted for root task {root_task_id}: "
                    f"{child_count} children, limit is {self.settings.multi_agent_workflow_max_child_attempts}"
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

    def _latest_artifact_resource(
        self,
        task_id: str,
        artifact_kind: str,
        *,
        fallback_paths: list[Path] | None = None,
    ) -> str | None:
        resources = self._artifact_resources(task_id, artifact_kind, fallback_paths=fallback_paths)
        if not resources:
            return None
        return resources[-1]

    def _artifact_resources(
        self,
        task_id: str,
        artifact_kind: str,
        *,
        fallback_paths: list[Path] | None = None,
    ) -> list[str]:
        resources: list[str] = []
        seen_paths: set[str] = set()

        for artifact in self.store.list_artifacts(task_id, artifact_kind):
            path = Path(artifact["path"])
            if not path.exists():
                continue
            path_key = str(path.resolve())
            if path_key in seen_paths:
                continue
            resources.append(self._resource_ref(task_id, path))
            seen_paths.add(path_key)

        for fallback_path in fallback_paths or []:
            path = Path(fallback_path)
            if not path.exists():
                continue
            path_key = str(path.resolve())
            if path_key in seen_paths:
                continue
            resources.append(self._resource_ref(task_id, path))
            seen_paths.add(path_key)

        return resources

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

    def _resolved_result_task(self, task: VideoTask) -> VideoTask | None:
        if task.delivery_status == "delivered":
            resolved_task_id = task.resolved_task_id or task.task_id
            resolved_task = self._require_task(resolved_task_id)
            if self._task_has_valid_final_video(resolved_task_id):
                return resolved_task
            return None
        if task.status is TaskStatus.COMPLETED:
            if self._task_has_valid_final_video(task.task_id):
                return task
            return None
        return None

    def _task_has_valid_final_video(self, task_id: str) -> bool:
        artifacts = self.store.list_artifacts(task_id, "final_video")
        for artifact in reversed(artifacts):
            if Path(artifact["path"]).exists():
                return True
        return self.artifact_store.final_video_path(task_id).exists()

    @staticmethod
    def _is_completed_delivery_candidate(task: VideoTask) -> bool:
        return task.status is TaskStatus.COMPLETED and task.delivery_status == "delivered"

    @staticmethod
    def inherit_persistent_memory_context(base_task: VideoTask) -> PersistentMemoryContext | None:
        if not (
            base_task.selected_memory_ids
            or base_task.persistent_memory_context_summary
            or base_task.persistent_memory_context_digest
        ):
            return None
        return PersistentMemoryContext(
            memory_ids=list(base_task.selected_memory_ids),
            summary_text=base_task.persistent_memory_context_summary,
            summary_digest=base_task.persistent_memory_context_digest,
        )

    def _resolve_owner_revision_persistent_memory(
        self,
        *,
        base_task: VideoTask,
        agent_id: str,
    ) -> PersistentMemoryContext | None:
        root_task = self._require_task(base_task.root_task_id or base_task.task_id)
        workflow_memory_ids = list(root_task.selected_memory_ids)
        if workflow_memory_ids:
            return self.resolve_persistent_memory_context_for_agent(agent_id, workflow_memory_ids)
        return None

    def _create_challenger_child_task(
        self,
        *,
        base_task: VideoTask,
        feedback: str,
        session_id: Optional[str],
        persistent_memory: PersistentMemoryContext | None,
    ) -> CreateVideoTaskResult:
        if not self._is_completed_delivery_candidate(base_task):
            raise ValueError("create_challenger_task requires a completed delivered parent task")
        root_task_id = base_task.root_task_id or base_task.task_id
        self._enforce_attempt_limit(root_task_id)
        self._enforce_workflow_child_budget(root_task_id)
        effective_feedback = self._augment_feedback_with_case_memory(base_task, feedback)
        metadata = self.revision_service.build_metadata(
            base_task,
            revision_mode="quality_challenger",
            preserve_working_parts=True,
        )
        child_task = self.revision_service.create_revision(
            base_task=base_task,
            feedback=effective_feedback,
            preserve_working_parts=True,
        )
        child_task.branch_kind = "challenger"
        child_task.delivery_status = "pending"
        child_task.resolved_task_id = None
        child_task.completion_mode = None
        child_task.delivery_tier = None
        child_task.delivery_stop_reason = None
        return self._persist_child_task(
            base_task=base_task,
            child_task=child_task,
            attempt_kind="challenger",
            session_id=session_id,
            event_type="challenger_created",
            event_payload={
                "parent_task_id": base_task.task_id,
                "feedback": feedback,
                "effective_feedback": effective_feedback,
                **metadata,
            },
            persistent_memory=persistent_memory,
        )

    def _persist_child_task(
        self,
        base_task: VideoTask,
        child_task: VideoTask,
        attempt_kind: str,
        session_id: Optional[str],
        event_type: str,
        event_payload: dict[str, Any],
        persistent_memory: PersistentMemoryContext | None = None,
        thread_id: str | None = None,
        iteration_id: str | None = None,
        execution_kind: str | None = None,
        target_participant_id: str | None = None,
        target_agent_id: str | None = None,
        target_agent_role: str | None = None,
    ) -> CreateVideoTaskResult:
        effective_session_id = child_task.session_id or base_task.session_id or session_id
        if effective_session_id is not None:
            child_task.session_id = effective_session_id
        child_task.thread_id = thread_id or child_task.thread_id or base_task.thread_id
        child_task.iteration_id = iteration_id or child_task.iteration_id
        child_task.execution_kind = execution_kind or child_task.execution_kind
        child_task.target_participant_id = (
            target_participant_id or child_task.target_participant_id or base_task.target_participant_id
        )
        child_task.target_agent_id = target_agent_id or child_task.target_agent_id or base_task.target_agent_id
        child_task.target_agent_role = (
            target_agent_role or child_task.target_agent_role or base_task.target_agent_role
        )
        child_task.result_id = None

        self._apply_memory_context(session_id=effective_session_id, child_task=child_task)
        self._apply_persistent_memory_context(child_task=child_task, persistent_memory=persistent_memory)
        persisted = self.store.create_task(child_task)
        self.artifact_store.ensure_task_dirs(persisted.task_id)
        self.artifact_store.write_task_snapshot(persisted)
        self.store.append_event(persisted.task_id, event_type, event_payload)
        if self.delivery_case_service is not None:
            self.delivery_case_service.ensure_case_for_task(persisted)
            self.delivery_case_service.queue_generator_run(task=persisted)
            self.delivery_case_service.sync_case_for_root(persisted.root_task_id or persisted.task_id)
            if base_task.status is TaskStatus.COMPLETED and base_task.delivery_status == "delivered":
                self.delivery_case_service.record_branch_spawned(
                    incumbent_task=base_task,
                    challenger_task=persisted,
                )
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

    def _augment_feedback_with_case_memory(self, base_task: VideoTask, feedback: str) -> str:
        if self.case_memory_service is None:
            return feedback
        root_task_id = base_task.root_task_id or base_task.task_id
        return self.case_memory_service.augment_feedback(root_task_id, feedback)

    def _record_case_memory_branch_state(
        self,
        *,
        root_task_id: str,
        branch_scoreboard: list[dict[str, Any]],
        arbitration_summary: dict[str, Any],
    ) -> None:
        if self.case_memory_service is None:
            return
        self.case_memory_service.record_branch_state(
            root_task_id,
            branch_scoreboard=branch_scoreboard,
            arbitration_summary=arbitration_summary,
        )

    def _record_case_memory_decision(
        self,
        *,
        root_task_id: str,
        action: str,
        task_id: str | None,
        details: dict[str, Any] | None = None,
    ) -> None:
        if self.case_memory_service is None:
            return
        self.case_memory_service.record_decision(
            root_task_id,
            action=action,
            task_id=task_id,
            details=details,
        )

    def resolve_persistent_memory_context_for_agent(
        self,
        agent_id: str,
        memory_ids: list[str] | None,
    ) -> PersistentMemoryContext:
        if self.persistent_memory_service is None:
            return PersistentMemoryContext(memory_ids=list(memory_ids or []))
        return self.persistent_memory_service.resolve_memory_context(agent_id, memory_ids)
