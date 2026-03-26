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
    inherited_from_task_id: Optional[str] = None
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
            inherited_from_task_id=parent.task_id,
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
        )
