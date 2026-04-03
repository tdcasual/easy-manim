from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class VideoThread(BaseModel):
    thread_id: str
    owner_agent_id: str
    title: str
    status: str = "active"
    current_iteration_id: str | None = None
    selected_result_id: str | None = None
    origin_prompt: str
    origin_context_summary: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    archived_at: datetime | None = None


class VideoIteration(BaseModel):
    iteration_id: str
    thread_id: str
    parent_iteration_id: str | None = None
    goal: str
    requested_action: str | None = None
    preserve_working_parts: bool | None = None
    status: str = "active"
    resolution_state: str = "open"
    focus_summary: str | None = None
    selected_result_id: str | None = None
    source_result_id: str | None = None
    initiated_by_turn_id: str | None = None
    responsible_role: str | None = None
    responsible_agent_id: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    closed_at: datetime | None = None


class VideoTurn(BaseModel):
    turn_id: str
    thread_id: str
    iteration_id: str
    turn_type: str
    intent_type: str | None = None
    speaker_type: Literal["owner", "agent", "system"]
    speaker_agent_id: str | None = None
    speaker_role: str | None = None
    title: str
    summary: str = ""
    visibility: Literal["product_safe", "operator_safe", "private"] = "product_safe"
    reply_to_turn_id: str | None = None
    related_result_id: str | None = None
    addressed_participant_id: str | None = None
    addressed_agent_id: str | None = None
    source_run_id: str | None = None
    source_task_id: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class VideoResult(BaseModel):
    result_id: str
    thread_id: str
    iteration_id: str
    source_task_id: str | None = None
    status: str = "pending"
    video_resource: str | None = None
    preview_resources: list[str] = Field(default_factory=list)
    script_resource: str | None = None
    validation_report_resource: str | None = None
    result_summary: str = ""
    quality_summary: str | None = None
    selected: bool = False
    created_at: datetime = Field(default_factory=_utcnow)


class VideoAgentRun(BaseModel):
    run_id: str
    thread_id: str
    iteration_id: str
    task_id: str | None = None
    agent_id: str
    role: str
    status: str = "pending"
    phase: str | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class VideoThreadParticipant(BaseModel):
    thread_id: str
    participant_id: str
    participant_type: Literal["owner", "agent"]
    agent_id: str | None = None
    role: str
    display_name: str
    capabilities: list[str] = Field(default_factory=list)
    joined_at: datetime = Field(default_factory=_utcnow)
    left_at: datetime | None = None


class VideoThreadParticipantManagement(BaseModel):
    can_manage: bool = False
    can_invite: bool = False
    can_remove: bool = False
    invite_label: str = "Invite participant"
    invite_placeholder: str = "Agent id"
    default_role: str = "reviewer"
    default_capabilities: list[str] = Field(default_factory=lambda: ["review_bundle:read"])
    remove_label: str = "Remove participant"
    removable_participant_ids: list[str] = Field(default_factory=list)
    disabled_reason: str = ""
    context_hint: str = ""


class VideoThreadHeader(BaseModel):
    thread_id: str
    title: str
    status: str
    current_iteration_id: str | None = None
    selected_result_id: str | None = None


class VideoThreadCurrentFocus(BaseModel):
    current_iteration_id: str | None = None
    current_iteration_goal: str | None = None
    current_result_id: str | None = None
    current_result_summary: str | None = None
    current_result_author_display_name: str | None = None
    current_result_author_role: str | None = None
    current_result_selection_reason: str | None = None


class VideoThreadSelectionSummary(BaseModel):
    title: str = "Why this version is selected"
    summary: str = ""
    selected_result_id: str | None = None
    author_display_name: str | None = None
    author_role: str | None = None


class VideoThreadLatestExplanation(BaseModel):
    title: str = "Latest visible explanation"
    summary: str = ""
    turn_id: str | None = None
    speaker_display_name: str | None = None
    speaker_role: str | None = None


class VideoThreadDecisionNote(BaseModel):
    note_id: str
    note_kind: Literal["selection_rationale", "agent_explanation", "iteration_goal"]
    title: str
    summary: str = ""
    emphasis: Literal["primary", "supporting", "context"] = "supporting"
    source_iteration_id: str | None = None
    source_turn_id: str | None = None
    source_result_id: str | None = None
    actor_display_name: str | None = None
    actor_role: str | None = None


class VideoThreadDecisionNotes(BaseModel):
    title: str = "Decision Notes"
    items: list[VideoThreadDecisionNote] = Field(default_factory=list)


class VideoThreadAuthorship(BaseModel):
    title: str = "Who shaped this version"
    summary: str = ""
    primary_agent_display_name: str | None = None
    primary_agent_role: str | None = None
    source_iteration_id: str | None = None
    source_run_id: str | None = None
    source_turn_id: str | None = None


class VideoThreadDiscussionReply(BaseModel):
    turn_id: str
    title: str
    summary: str = ""
    speaker_display_name: str | None = None
    speaker_role: str | None = None
    intent_type: str | None = None
    related_result_id: str | None = None


class VideoThreadDiscussionGroup(BaseModel):
    group_id: str
    iteration_id: str | None = None
    prompt_turn_id: str
    prompt_title: str
    prompt_summary: str = ""
    prompt_intent_type: str | None = None
    prompt_actor_display_name: str | None = None
    prompt_actor_role: str | None = None
    related_result_id: str | None = None
    status: Literal["open", "answered"] = "open"
    replies: list[VideoThreadDiscussionReply] = Field(default_factory=list)


class VideoThreadDiscussionGroups(BaseModel):
    groups: list[VideoThreadDiscussionGroup] = Field(default_factory=list)


class VideoThreadDiscussionRuntime(BaseModel):
    title: str = "Discussion Runtime"
    summary: str = ""
    active_iteration_id: str | None = None
    active_discussion_group_id: str | None = None
    continuity_scope: Literal["iteration", "result", "thread"] = "iteration"
    reply_policy: Literal["continue_thread", "start_new_thread", "agent_choice"] = (
        "continue_thread"
    )
    default_intent_type: str | None = None
    default_reply_to_turn_id: str | None = None
    default_related_result_id: str | None = None
    addressed_participant_id: str | None = None
    addressed_agent_id: str | None = None
    addressed_display_name: str | None = None
    suggested_follow_up_modes: list[str] = Field(default_factory=list)
    active_thread_title: str | None = None
    active_thread_summary: str = ""
    latest_owner_turn_id: str | None = None
    latest_agent_turn_id: str | None = None
    latest_agent_summary: str = ""


class VideoThreadParticipantRuntimeContributor(BaseModel):
    participant_id: str | None = None
    agent_id: str | None = None
    display_name: str
    role: str | None = None
    contribution_kind: Literal["expected_responder", "recent_run", "recent_reply"] = (
        "recent_reply"
    )
    summary: str = ""


class VideoThreadParticipantRuntime(BaseModel):
    title: str = "Participant Runtime"
    summary: str = ""
    active_iteration_id: str | None = None
    expected_participant_id: str | None = None
    expected_agent_id: str | None = None
    expected_display_name: str | None = None
    expected_role: str | None = None
    continuity_mode: Literal[
        "keep_current_participant",
        "invite_new_participant",
        "agent_choice",
    ] = "agent_choice"
    follow_up_target_locked: bool = False
    recent_contributors: list[VideoThreadParticipantRuntimeContributor] = Field(
        default_factory=list
    )


class VideoThreadNextRecommendedMove(BaseModel):
    title: str = "Recommended next move"
    summary: str = ""
    recommended_action_id: str | None = None
    recommended_action_label: str | None = None
    owner_action_required: str | None = None
    tone: Literal["neutral", "active", "attention"] = "neutral"


class VideoThreadResponsibility(BaseModel):
    owner_action_required: str | None = None
    expected_agent_role: str | None = None
    expected_agent_id: str | None = None


class VideoThreadIterationCard(BaseModel):
    iteration_id: str
    title: str
    goal: str
    status: str
    resolution_state: str
    requested_action: str | None = None
    result_summary: str | None = None
    responsible_role: str | None = None
    responsible_agent_id: str | None = None


class VideoThreadIterationWorkbench(BaseModel):
    iterations: list[VideoThreadIterationCard] = Field(default_factory=list)
    selected_iteration_id: str | None = None
    latest_iteration_id: str | None = None


class VideoThreadIterationDetailSummary(BaseModel):
    title: str = "Iteration Detail"
    summary: str = ""
    selected_iteration_id: str | None = None
    resource_uri: str | None = None
    turn_count: int = 0
    run_count: int = 0
    result_count: int = 0
    execution_summary: VideoThreadIterationExecutionSummary = Field(
        default_factory=lambda: VideoThreadIterationExecutionSummary(
            summary="No iteration is selected yet.",
        )
    )


class VideoThreadIterationExecutionSummary(BaseModel):
    title: str = "Execution Summary"
    summary: str = "No tracked execution is attached to this iteration yet."
    task_id: str | None = None
    run_id: str | None = None
    status: str = "pending"
    phase: str | None = None
    agent_id: str | None = None
    agent_display_name: str | None = None
    agent_role: str | None = None
    result_id: str | None = None
    discussion_group_id: str | None = None
    reply_to_turn_id: str | None = None
    latest_owner_turn_id: str | None = None
    latest_agent_turn_id: str | None = None
    is_active: bool = False


class VideoThreadIterationDetailTurn(BaseModel):
    turn_id: str
    turn_type: str
    title: str
    summary: str = ""
    intent_type: str | None = None
    reply_to_turn_id: str | None = None
    related_result_id: str | None = None
    addressed_participant_id: str | None = None
    addressed_agent_id: str | None = None
    addressed_display_name: str | None = None
    speaker_display_name: str | None = None
    speaker_role: str | None = None
    created_at: datetime | None = None


class VideoThreadIterationDetailRun(BaseModel):
    run_id: str
    agent_id: str | None = None
    agent_display_name: str | None = None
    role: str
    status: str
    phase: str | None = None
    output_summary: str | None = None
    task_id: str | None = None
    created_at: datetime | None = None


class VideoThreadIterationDetailResult(BaseModel):
    result_id: str
    status: str
    result_summary: str = ""
    selected: bool = False
    video_resource: str | None = None
    created_at: datetime | None = None


class VideoThreadComposerTarget(BaseModel):
    iteration_id: str | None = None
    result_id: str | None = None
    addressed_participant_id: str | None = None
    addressed_agent_id: str | None = None
    addressed_display_name: str | None = None
    agent_role: str | None = None
    agent_display_name: str | None = None
    summary: str = ""


class VideoThreadIterationDetail(BaseModel):
    thread_id: str
    iteration_id: str
    title: str = "Iteration Detail"
    summary: str = ""
    execution_summary: VideoThreadIterationExecutionSummary = Field(
        default_factory=VideoThreadIterationExecutionSummary
    )
    composer_target: VideoThreadComposerTarget = Field(default_factory=VideoThreadComposerTarget)
    iteration: VideoIteration
    turns: list[VideoThreadIterationDetailTurn] = Field(default_factory=list)
    runs: list[VideoThreadIterationDetailRun] = Field(default_factory=list)
    results: list[VideoThreadIterationDetailResult] = Field(default_factory=list)


class VideoThreadConversationTurn(BaseModel):
    turn_id: str
    iteration_id: str
    title: str
    summary: str = ""
    intent_type: str | None = None
    reply_to_turn_id: str | None = None
    related_result_id: str | None = None
    addressed_participant_id: str | None = None
    addressed_agent_id: str | None = None
    speaker_type: str
    speaker_role: str | None = None


class VideoThreadConversation(BaseModel):
    turns: list[VideoThreadConversationTurn] = Field(default_factory=list)


class VideoThreadHistoryCard(BaseModel):
    card_id: str
    card_type: Literal["result_selection", "agent_explanation", "process_update", "owner_request"]
    title: str
    summary: str = ""
    iteration_id: str | None = None
    intent_type: str | None = None
    reply_to_turn_id: str | None = None
    related_result_id: str | None = None
    actor_display_name: str | None = None
    actor_role: str | None = None
    emphasis: Literal["primary", "supporting", "context"] = "supporting"


class VideoThreadHistory(BaseModel):
    cards: list[VideoThreadHistoryCard] = Field(default_factory=list)


class VideoThreadArtifactLineageItem(BaseModel):
    lineage_id: str
    iteration_id: str | None = None
    from_result_id: str | None = None
    to_result_id: str | None = None
    change_summary: str = ""
    change_reason: str = ""
    trigger_turn_id: str | None = None
    trigger_label: str | None = None
    actor_display_name: str | None = None
    actor_role: str | None = None
    emphasis: Literal["primary", "supporting", "context"] = "supporting"
    status: Literal["selected", "active", "superseded", "origin"] = "superseded"


class VideoThreadArtifactLineage(BaseModel):
    title: str = "Artifact Lineage"
    summary: str = ""
    selected_result_id: str | None = None
    items: list[VideoThreadArtifactLineageItem] = Field(default_factory=list)


class VideoThreadRationaleSnapshot(BaseModel):
    snapshot_id: str
    iteration_id: str | None = None
    snapshot_kind: Literal["owner_goal", "agent_explanation", "selection_rationale"]
    title: str
    summary: str = ""
    source_turn_id: str | None = None
    source_result_id: str | None = None
    actor_display_name: str | None = None
    actor_role: str | None = None
    emphasis: Literal["primary", "supporting", "context"] = "supporting"
    status: Literal["current", "archived"] = "archived"


class VideoThreadRationaleSnapshots(BaseModel):
    title: str = "Rationale Snapshots"
    summary: str = ""
    current_iteration_id: str | None = None
    items: list[VideoThreadRationaleSnapshot] = Field(default_factory=list)


class VideoThreadIterationCompare(BaseModel):
    title: str = "Iteration Compare"
    summary: str = ""
    previous_iteration_id: str | None = None
    current_iteration_id: str | None = None
    previous_result_id: str | None = None
    current_result_id: str | None = None
    change_summary: str = ""
    rationale_shift_summary: str = ""
    continuity_status: Literal["new", "preserved", "changed", "unknown"] = "unknown"
    continuity_summary: str = ""


class VideoThreadProductionJournalEntry(BaseModel):
    entry_id: str
    entry_kind: Literal["iteration", "run", "result"]
    title: str
    summary: str = ""
    stage: str = ""
    status: str = ""
    iteration_id: str | None = None
    task_id: str | None = None
    run_id: str | None = None
    result_id: str | None = None
    actor_display_name: str | None = None
    actor_role: str | None = None
    resource_refs: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


class VideoThreadProductionJournal(BaseModel):
    title: str = "Production Journal"
    summary: str = ""
    entries: list[VideoThreadProductionJournalEntry] = Field(default_factory=list)


class VideoThreadProcessRun(BaseModel):
    run_id: str
    iteration_id: str
    task_id: str | None = None
    role: str
    status: str
    phase: str | None = None
    output_summary: str | None = None


class VideoThreadProcess(BaseModel):
    runs: list[VideoThreadProcessRun] = Field(default_factory=list)


class VideoThreadParticipantsSection(BaseModel):
    items: list[VideoThreadParticipant] = Field(default_factory=list)
    management: VideoThreadParticipantManagement = Field(default_factory=VideoThreadParticipantManagement)


class VideoThreadAction(BaseModel):
    action_id: str
    label: str
    description: str = ""
    tone: Literal["strong", "neutral", "muted"] = "neutral"
    disabled: bool = False
    disabled_reason: str = ""


class VideoThreadActions(BaseModel):
    items: list[VideoThreadAction] = Field(default_factory=list)


class VideoThreadComposer(BaseModel):
    placeholder: str = "Ask why this version was made or request the next change."
    submit_label: str = "Send"
    disabled: bool = False
    disabled_reason: str = ""
    context_hint: str = ""
    target: VideoThreadComposerTarget = Field(default_factory=VideoThreadComposerTarget)


class VideoThreadPanelPresentation(BaseModel):
    panel_id: str
    tone: Literal["accent", "neutral", "attention", "subtle"] = "neutral"
    emphasis: Literal["primary", "supporting", "context"] = "supporting"
    default_open: bool = False
    collapsible: bool = True


class VideoThreadRenderContract(BaseModel):
    default_focus_panel: str = "current_focus"
    panel_tone: Literal["neutral", "active", "attention", "resolved"] = "neutral"
    display_priority: Literal["normal", "high"] = "normal"
    badge_order: list[str] = Field(default_factory=list)
    panel_order: list[str] = Field(
        default_factory=lambda: [
            "thread_header",
            "current_focus",
            "selection_summary",
            "latest_explanation",
            "decision_notes",
            "artifact_lineage",
            "rationale_snapshots",
            "iteration_compare",
            "authorship",
            "next_recommended_move",
            "production_journal",
            "discussion_runtime",
            "participant_runtime",
            "discussion_groups",
            "history",
            "iteration_workbench",
            "iteration_detail",
            "conversation",
            "participants",
            "process",
            "actions",
            "composer",
        ]
    )
    default_expanded_panels: list[str] = Field(
        default_factory=lambda: ["current_focus", "history", "actions", "composer"]
    )
    sticky_primary_action_id: str | None = None
    sticky_primary_action_emphasis: Literal["strong", "normal", "subtle"] = "normal"
    panel_presentations: list[VideoThreadPanelPresentation] = Field(default_factory=list)


class VideoThreadSurface(BaseModel):
    thread_header: VideoThreadHeader
    thread_summary: str
    current_focus: VideoThreadCurrentFocus
    selection_summary: VideoThreadSelectionSummary = Field(default_factory=VideoThreadSelectionSummary)
    latest_explanation: VideoThreadLatestExplanation = Field(default_factory=VideoThreadLatestExplanation)
    decision_notes: VideoThreadDecisionNotes = Field(default_factory=VideoThreadDecisionNotes)
    artifact_lineage: VideoThreadArtifactLineage = Field(default_factory=VideoThreadArtifactLineage)
    rationale_snapshots: VideoThreadRationaleSnapshots = Field(default_factory=VideoThreadRationaleSnapshots)
    iteration_compare: VideoThreadIterationCompare = Field(default_factory=VideoThreadIterationCompare)
    authorship: VideoThreadAuthorship = Field(default_factory=VideoThreadAuthorship)
    next_recommended_move: VideoThreadNextRecommendedMove = Field(default_factory=VideoThreadNextRecommendedMove)
    responsibility: VideoThreadResponsibility
    iteration_workbench: VideoThreadIterationWorkbench
    iteration_detail: VideoThreadIterationDetailSummary = Field(default_factory=VideoThreadIterationDetailSummary)
    conversation: VideoThreadConversation
    history: VideoThreadHistory = Field(default_factory=VideoThreadHistory)
    production_journal: VideoThreadProductionJournal = Field(default_factory=VideoThreadProductionJournal)
    discussion_groups: VideoThreadDiscussionGroups = Field(default_factory=VideoThreadDiscussionGroups)
    discussion_runtime: VideoThreadDiscussionRuntime = Field(default_factory=VideoThreadDiscussionRuntime)
    participant_runtime: VideoThreadParticipantRuntime = Field(default_factory=VideoThreadParticipantRuntime)
    process: VideoThreadProcess
    participants: VideoThreadParticipantsSection = Field(default_factory=VideoThreadParticipantsSection)
    actions: VideoThreadActions = Field(default_factory=VideoThreadActions)
    composer: VideoThreadComposer = Field(default_factory=VideoThreadComposer)
    render_contract: VideoThreadRenderContract = Field(default_factory=VideoThreadRenderContract)
