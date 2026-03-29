from __future__ import annotations

from typing import Any
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ReviewIssue(BaseModel):
    code: str
    severity: Literal["low", "medium", "high"]
    evidence: str
    action: str


class CollaborationSection(BaseModel):
    role: Literal["planner", "reviewer", "repairer"]
    summary: str = ""
    decision: Literal["accept", "revise", "retry", "repair", "escalate"] | None = None
    execution_hint: str | None = None


class CollaborationSections(BaseModel):
    planner_recommendation: CollaborationSection = Field(
        default_factory=lambda: CollaborationSection(role="planner")
    )
    reviewer_decision: CollaborationSection = Field(
        default_factory=lambda: CollaborationSection(role="reviewer")
    )
    repairer_execution_hint: CollaborationSection = Field(
        default_factory=lambda: CollaborationSection(role="repairer")
    )


class ReviewDecision(BaseModel):
    decision: Literal["accept", "revise", "retry", "repair", "escalate"]
    summary: str
    decision_role: Literal["orchestrator", "reviewer"] | None = None
    preserve_working_parts: bool = True
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    issues: list[ReviewIssue] = Field(default_factory=list)
    feedback: str | None = None
    stop_reason: str | None = None
    collaboration: CollaborationSections | None = None

    def resolved_decision(self) -> Literal["accept", "revise", "retry", "repair", "escalate"]:
        if self.collaboration and self.collaboration.reviewer_decision.decision:
            return self.collaboration.reviewer_decision.decision
        return self.decision

    def resolved_feedback(self) -> str:
        if (self.feedback or "").strip():
            return self.feedback or ""
        if self.collaboration is None:
            return ""
        return (self.collaboration.repairer_execution_hint.execution_hint or "").strip()

    @model_validator(mode="after")
    def require_feedback_for_revise_or_repair(self) -> "ReviewDecision":
        if self.resolved_decision() in {"revise", "repair"} and not self.resolved_feedback():
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
    scene_spec: dict[str, Any] | None = None
    recovery_plan: dict[str, Any] | None = None
    quality_scorecard: dict[str, Any] | None = None
    quality_gate_status: str | None = None
    must_fix_issue_codes: list[str] = Field(default_factory=list)
    acceptance_blockers: list[str] = Field(default_factory=list)
    decision_trace: dict[str, Any] = Field(default_factory=dict)
    task_events: list[dict[str, Any]] = Field(default_factory=list)
    session_memory_summary: str = ""
    video_resource: str | None = None
    preview_frame_resources: list[str] = Field(default_factory=list)
    script_resource: str | None = None
    validation_report_resource: str | None = None
    collaboration: CollaborationSections = Field(default_factory=CollaborationSections)


class ReviewDecisionOutcome(BaseModel):
    task_id: str
    root_task_id: str | None = None
    action: str
    created_task_id: str | None = None
    reason: str
