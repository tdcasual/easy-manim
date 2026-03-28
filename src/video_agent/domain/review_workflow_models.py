from __future__ import annotations

from typing import Any
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ReviewIssue(BaseModel):
    code: str
    severity: Literal["low", "medium", "high"]
    evidence: str
    action: str


class ReviewDecision(BaseModel):
    decision: Literal["accept", "revise", "retry", "repair", "escalate"]
    summary: str
    preserve_working_parts: bool = True
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    issues: list[ReviewIssue] = Field(default_factory=list)
    feedback: str | None = None
    stop_reason: str | None = None

    @model_validator(mode="after")
    def require_feedback_for_revise_or_repair(self) -> "ReviewDecision":
        if self.decision in {"revise", "repair"} and not (self.feedback or "").strip():
            raise ValueError("feedback is required for revise and repair decisions")
        return self


class ReviewBundle(BaseModel):
    task_id: str
    root_task_id: str | None = None
    attempt_count: int = 0
    child_attempt_count: int = 0
    prompt: str = ""
    feedback: str | None = None
    display_title: str | None = None
    status: str
    phase: str
    latest_validation_summary: dict[str, Any] = Field(default_factory=dict)
    failure_contract: dict[str, Any] | None = None
    task_events: list[dict[str, Any]] = Field(default_factory=list)
    session_memory_summary: str = ""
    video_resource: str | None = None
    preview_frame_resources: list[str] = Field(default_factory=list)
    script_resource: str | None = None
    validation_report_resource: str | None = None


class ReviewDecisionOutcome(BaseModel):
    task_id: str
    root_task_id: str | None = None
    action: str
    created_task_id: str | None = None
    reason: str
