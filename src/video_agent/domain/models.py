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
    status: TaskStatus = TaskStatus.QUEUED
    phase: TaskPhase = TaskPhase.QUEUED
    prompt: str
    feedback: Optional[str] = None
    output_profile: dict[str, Any] = Field(default_factory=dict)
    style_hints: dict[str, Any] = Field(default_factory=dict)
    validation_profile: dict[str, Any] = Field(default_factory=dict)
    attempt_count: int = 0
    repair_attempted: bool = False
    repair_child_count: int = 0
    repair_last_issue_code: Optional[str] = None
    repair_stop_reason: Optional[str] = None
    current_script_artifact_id: Optional[str] = None
    best_result_artifact_id: Optional[str] = None
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
            prompt=parent.prompt,
            feedback=feedback,
            output_profile=parent.output_profile,
            style_hints=parent.style_hints,
            validation_profile=parent.validation_profile,
            current_script_artifact_id=parent.current_script_artifact_id if preserve_working_parts else None,
            best_result_artifact_id=parent.best_result_artifact_id if preserve_working_parts else None,
        )
