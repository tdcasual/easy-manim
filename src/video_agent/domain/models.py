from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from video_agent.domain.enums import TaskPhase, TaskStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class VideoTask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    root_task_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    thread_id: Optional[str] = None
    iteration_id: Optional[str] = None
    result_id: Optional[str] = None
    execution_kind: Optional[str] = None
    target_participant_id: Optional[str] = None
    target_agent_id: Optional[str] = None
    target_agent_role: Optional[str] = None
    inherited_from_task_id: Optional[str] = None
    branch_kind: Optional[str] = None
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    status: TaskStatus = TaskStatus.QUEUED
    phase: TaskPhase = TaskPhase.QUEUED
    prompt: str
    feedback: Optional[str] = None
    memory_context_summary: Optional[str] = None
    memory_context_digest: Optional[str] = None
    selected_memory_ids: list[str] = Field(default_factory=list)
    persistent_memory_context_summary: Optional[str] = None
    persistent_memory_context_digest: Optional[str] = None
    profile_version: int | None = None
    output_profile: dict[str, Any] = Field(default_factory=dict)
    style_hints: dict[str, Any] = Field(default_factory=dict)
    validation_profile: dict[str, Any] = Field(default_factory=dict)
    effective_request_profile: dict[str, Any] = Field(default_factory=dict)
    effective_profile_digest: Optional[str] = None
    effective_policy_flags: dict[str, Any] = Field(default_factory=dict)
    attempt_count: int = 0
    repair_attempted: bool = False
    repair_child_count: int = 0
    repair_last_issue_code: Optional[str] = None
    repair_stop_reason: Optional[str] = None
    current_script_artifact_id: Optional[str] = None
    best_result_artifact_id: Optional[str] = None
    display_title: Optional[str] = None
    title_source: Optional[str] = None
    risk_level: Optional[str] = None
    generation_mode: Optional[str] = None
    strategy_profile_id: Optional[str] = None
    scene_spec_id: Optional[str] = None
    quality_gate_status: Optional[str] = None
    accepted_as_best: bool = False
    accepted_version_rank: Optional[int] = None
    delivery_status: Optional[str] = None
    resolved_task_id: Optional[str] = None
    completion_mode: Optional[str] = None
    delivery_tier: Optional[str] = None
    delivery_stop_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    @model_validator(mode="after")
    def set_root_task_id(self) -> "VideoTask":
        if self.root_task_id is None:
            self.root_task_id = self.task_id
        return self

    @classmethod
    def from_revision(
        cls,
        parent: "VideoTask",
        feedback: str,
        preserve_working_parts: bool = True,
    ) -> "VideoTask":
        return cls(
            root_task_id=parent.root_task_id,
            parent_task_id=parent.task_id,
            thread_id=parent.thread_id,
            iteration_id=parent.iteration_id,
            result_id=parent.result_id,
            execution_kind=parent.execution_kind,
            target_participant_id=parent.target_participant_id,
            target_agent_id=parent.target_agent_id,
            target_agent_role=parent.target_agent_role,
            inherited_from_task_id=parent.task_id,
            branch_kind=None,
            agent_id=parent.agent_id,
            session_id=parent.session_id,
            prompt=parent.prompt,
            feedback=feedback,
            memory_context_summary=None,
            memory_context_digest=None,
            selected_memory_ids=[],
            persistent_memory_context_summary=None,
            persistent_memory_context_digest=None,
            profile_version=parent.profile_version,
            output_profile=parent.output_profile,
            style_hints=parent.style_hints,
            validation_profile=parent.validation_profile,
            effective_request_profile=parent.effective_request_profile,
            effective_profile_digest=parent.effective_profile_digest,
            effective_policy_flags=parent.effective_policy_flags,
            current_script_artifact_id=parent.current_script_artifact_id if preserve_working_parts else None,
            best_result_artifact_id=parent.best_result_artifact_id if preserve_working_parts else None,
            display_title=parent.display_title,
            title_source=parent.title_source,
            risk_level=parent.risk_level,
            generation_mode=parent.generation_mode,
            strategy_profile_id=parent.strategy_profile_id,
            scene_spec_id=parent.scene_spec_id,
            quality_gate_status=parent.quality_gate_status,
            delivery_status="pending",
            resolved_task_id=None,
            completion_mode=None,
            delivery_tier=None,
            delivery_stop_reason=None,
        )
