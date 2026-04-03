from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from video_agent.domain.agent_memory_models import AgentMemoryRetrievalHit


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
    case_memory: dict[str, Any] = Field(default_factory=dict)
    case_status: str | None = None
    active_task_id: str | None = None
    selected_task_id: str | None = None
    branch_candidates: list[dict[str, Any]] = Field(default_factory=list)
    branch_scoreboard: list[dict[str, Any]] = Field(default_factory=list)
    arbitration_summary: dict[str, Any] = Field(default_factory=dict)
    recent_agent_runs: list[dict[str, Any]] = Field(default_factory=list)
    video_resource: str | None = None
    preview_frame_resources: list[str] = Field(default_factory=list)
    script_resource: str | None = None
    validation_report_resource: str | None = None
    collaboration: CollaborationSections = Field(default_factory=CollaborationSections)
    collaboration_summary: WorkflowCollaborationSummary | None = None
    collaboration_memory_context: WorkflowCollaborationMemoryContext | None = None
    workflow_memory_recommendations: WorkflowMemoryRecommendations | None = None
    workflow_memory_action_contract: WorkflowMemoryActionContract | None = None
    workflow_review_controls: WorkflowReviewControls | None = None


class ReviewDecisionOutcome(BaseModel):
    task_id: str
    root_task_id: str | None = None
    action: str
    created_task_id: str | None = None
    reason: str
    workflow_memory_state: WorkflowMemoryState | None = None
    refresh_scope: Literal["panel_only", "task_and_panel", "navigate"] = "panel_only"
    refresh_task_id: str | None = None


class WorkflowParticipant(BaseModel):
    root_task_id: str
    agent_id: str
    role: Literal["planner", "reviewer", "repairer", "verifier"]
    capabilities: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    @model_validator(mode="after")
    def apply_default_capabilities(self) -> "WorkflowParticipant":
        if self.capabilities:
            return self

        defaults = {
            "planner": ["review_bundle:read"],
            "reviewer": ["review_bundle:read", "review_decision:write"],
            "repairer": ["review_bundle:read"],
            "verifier": ["review_bundle:read", "review_decision:write"],
        }
        self.capabilities = list(defaults[self.role])
        return self

    def has_capability(self, capability: str) -> bool:
        return capability in self.capabilities


class CollaborationEventRecord(BaseModel):
    root_task_id: str
    event_type: str
    created_at: datetime
    agent_id: str | None = None
    memory_id: str | None = None
    role: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    removed: bool = False


class CollaborationSummaryBase(BaseModel):
    participant_count: int = 0
    participants_by_role: dict[str, int] = Field(default_factory=dict)
    capability_counts: dict[str, int] = Field(default_factory=dict)
    recent_events: list[CollaborationEventRecord] = Field(default_factory=list)


class WorkflowCollaborationSummary(CollaborationSummaryBase):
    root_task_id: str
    participants: list[WorkflowParticipant] = Field(default_factory=list)


class RuntimeCollaborationSummary(CollaborationSummaryBase):
    workflow_count: int = 0


class CollaborationMemoryItem(BaseModel):
    source: Literal["persistent_memory", "task_context", "case_memory"]
    title: str
    summary: str
    memory_id: str | None = None
    score: float | None = None


class RoleCollaborationMemoryContext(BaseModel):
    role: Literal["planner", "reviewer", "repairer"]
    summary: str = ""
    item_count: int = 0
    items: list[CollaborationMemoryItem] = Field(default_factory=list)


class WorkflowCollaborationMemoryContext(BaseModel):
    root_task_id: str
    agent_id: str | None = None
    shared_memory_ids: list[str] = Field(default_factory=list)
    planner: RoleCollaborationMemoryContext = Field(
        default_factory=lambda: RoleCollaborationMemoryContext(role="planner")
    )
    reviewer: RoleCollaborationMemoryContext = Field(
        default_factory=lambda: RoleCollaborationMemoryContext(role="reviewer")
    )
    repairer: RoleCollaborationMemoryContext = Field(
        default_factory=lambda: RoleCollaborationMemoryContext(role="repairer")
    )


class WorkflowMemoryRecommendation(AgentMemoryRetrievalHit):
    pinned: bool = False


class WorkflowMemoryRecommendations(BaseModel):
    root_task_id: str
    query: str = ""
    pinned_memory_ids: list[str] = Field(default_factory=list)
    items: list[WorkflowMemoryRecommendation] = Field(default_factory=list)


class WorkflowMemoryState(BaseModel):
    root_task_id: str
    pinned_memory_ids: list[str] = Field(default_factory=list)
    persistent_memory_context_summary: str | None = None
    persistent_memory_context_digest: str | None = None


class WorkflowMemoryActionExample(BaseModel):
    name: Literal["pin", "unpin", "replace"]
    summary: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


class WorkflowMemoryActionContract(BaseModel):
    review_decision_field: str = "review_decision"
    pin_field: str = "pin_workflow_memory_ids"
    unpin_field: str = "unpin_workflow_memory_ids"
    response_state_field: str = "workflow_memory_state"
    supports_batch_updates: bool = True
    examples: list[WorkflowMemoryActionExample] = Field(default_factory=list)


class WorkflowSuggestedAction(BaseModel):
    action_id: str
    title: str
    summary: str = ""
    blocked: bool = False
    reasons: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)


class WorkflowSuggestedNextActions(BaseModel):
    primary: WorkflowSuggestedAction | None = None
    alternatives: list[WorkflowSuggestedAction] = Field(default_factory=list)


class WorkflowAvailableActionMemoryChange(BaseModel):
    pin_memory_ids: list[str] = Field(default_factory=list)
    unpin_memory_ids: list[str] = Field(default_factory=list)
    pin_count: int = 0
    unpin_count: int = 0


class WorkflowAvailableActionIntent(BaseModel):
    review_decision: Literal["accept", "revise", "retry", "repair", "escalate"] | None = None
    mutates_workflow_memory: bool = False
    workflow_memory_change: WorkflowAvailableActionMemoryChange | None = None


class WorkflowAvailableActionCard(BaseModel):
    action_id: str
    title: str
    button_label: str
    action_family: Literal["review_decision", "workflow_memory", "combined"] = "review_decision"
    summary: str = ""
    blocked: bool = False
    reasons: list[str] = Field(default_factory=list)
    is_primary: bool = False
    intent: WorkflowAvailableActionIntent = Field(default_factory=WorkflowAvailableActionIntent)
    payload: dict[str, Any] = Field(default_factory=dict)


class WorkflowAvailableActions(BaseModel):
    items: list[WorkflowAvailableActionCard] = Field(default_factory=list)


class WorkflowAvailableActionSection(BaseModel):
    section_id: Literal["recommended", "available", "blocked"]
    title: str
    summary: str = ""
    items: list[WorkflowAvailableActionCard] = Field(default_factory=list)


class WorkflowAvailableActionSections(BaseModel):
    items: list[WorkflowAvailableActionSection] = Field(default_factory=list)


class WorkflowReviewPanelBadge(BaseModel):
    badge_id: str
    label: str
    value: str
    tone: Literal["neutral", "ready", "attention", "blocked"] = "neutral"


class WorkflowReviewPanelEvent(BaseModel):
    event_type: str
    title: str
    summary: str = ""
    memory_id: str | None = None
    created_at: datetime


class WorkflowReviewPanelHeader(BaseModel):
    title: str = "Workflow review controls"
    tone: Literal["ready", "attention", "blocked"] = "attention"
    summary: str = ""
    badges: list[WorkflowReviewPanelBadge] = Field(default_factory=list)
    highlighted_event: WorkflowReviewPanelEvent | None = None


class WorkflowAppliedActionFeedback(BaseModel):
    event_type: str
    tone: Literal["info", "success"] = "info"
    title: str
    summary: str = ""
    memory_id: str | None = None
    created_at: datetime
    follow_up_action_id: str | None = None


class WorkflowReviewStatusSummary(BaseModel):
    recommended_action_id: str | None = None
    acceptance_ready: bool = False
    acceptance_blockers: list[str] = Field(default_factory=list)
    pinned_memory_count: int = 0
    pending_memory_recommendation_count: int = 0
    has_pending_memory_updates: bool = False
    latest_workflow_memory_event_type: str | None = None
    latest_workflow_memory_event_at: datetime | None = None


class WorkflowReviewRenderContract(BaseModel):
    badge_order: list[str] = Field(default_factory=list)
    panel_tone: Literal["ready", "attention", "blocked"] = "attention"
    display_priority: Literal["normal", "high"] = "normal"
    section_order: list[Literal["recommended", "available", "blocked"]] = Field(default_factory=list)
    default_focus_section_id: Literal["recommended", "available", "blocked"] | None = None
    default_expanded_section_ids: list[Literal["recommended", "available", "blocked"]] = Field(default_factory=list)
    section_presentations: list[WorkflowReviewSectionPresentation] = Field(default_factory=list)
    sticky_primary_action_id: str | None = None
    sticky_primary_action_emphasis: Literal["normal", "strong"] = "normal"
    applied_feedback_dismissible: bool = False


class WorkflowReviewSectionPresentation(BaseModel):
    section_id: Literal["recommended", "available", "blocked"]
    tone: Literal["accent", "neutral", "muted"] = "neutral"
    collapsible: bool = True


class WorkflowReviewControls(BaseModel):
    can_manage_workflow_memory: bool = False
    workflow_memory_state: WorkflowMemoryState | None = None
    recent_memory_events: list[CollaborationEventRecord] = Field(default_factory=list)
    workflow_memory_recommendations: WorkflowMemoryRecommendations | None = None
    workflow_memory_action_contract: WorkflowMemoryActionContract | None = None
    suggested_next_actions: WorkflowSuggestedNextActions | None = None
    available_actions: WorkflowAvailableActions | None = None
    action_sections: WorkflowAvailableActionSections | None = None
    panel_header: WorkflowReviewPanelHeader | None = None
    applied_action_feedback: WorkflowAppliedActionFeedback | None = None
    status_summary: WorkflowReviewStatusSummary | None = None
    render_contract: WorkflowReviewRenderContract | None = None


class WorkflowMemoryPinState(WorkflowMemoryState):
    root_task_id: str
    memory_id: str
