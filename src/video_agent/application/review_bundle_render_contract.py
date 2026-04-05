from __future__ import annotations

from typing import Any

from video_agent.domain.review_workflow_models import (
    WorkflowAppliedActionFeedback,
    WorkflowAvailableActionSections,
    WorkflowReviewPanelHeader,
    WorkflowReviewRenderContract,
    WorkflowReviewSectionPresentation,
    WorkflowReviewStatusSummary,
)


def build_applied_action_feedback(
    *,
    recent_memory_events: list[Any],
    status_summary: WorkflowReviewStatusSummary | None,
) -> WorkflowAppliedActionFeedback | None:
    latest_event = recent_memory_events[-1] if recent_memory_events else None
    if latest_event is None:
        return None

    return WorkflowAppliedActionFeedback(
        event_type=latest_event.event_type,
        tone="success" if latest_event.event_type == "workflow_memory_pinned" else "info",
        title=applied_feedback_title(latest_event.event_type),
        summary=applied_feedback_summary(
            event_type=latest_event.event_type,
            follow_up_action_id=None if status_summary is None else status_summary.recommended_action_id,
        ),
        memory_id=latest_event.memory_id,
        created_at=latest_event.created_at,
        follow_up_action_id=None if status_summary is None else status_summary.recommended_action_id,
    )


def applied_feedback_title(event_type: str) -> str:
    return {
        "workflow_memory_pinned": "Workflow memory update applied",
        "workflow_memory_unpinned": "Workflow memory removed",
    }.get(event_type, "Workflow memory updated")


def applied_feedback_summary(
    *,
    event_type: str,
    follow_up_action_id: str | None,
) -> str:
    if event_type == "workflow_memory_pinned":
        if follow_up_action_id:
            return f"Shared workflow memory was pinned. Continue with `{follow_up_action_id}` next."
        return "Shared workflow memory was pinned for upcoming revisions."
    if event_type == "workflow_memory_unpinned":
        if follow_up_action_id:
            return f"Shared workflow memory was removed. Continue with `{follow_up_action_id}` next."
        return "Shared workflow memory was removed from the workflow set."
    return "Workflow memory changed recently."


def build_render_contract(
    *,
    panel_header: WorkflowReviewPanelHeader | None,
    action_sections: WorkflowAvailableActionSections | None,
    status_summary: WorkflowReviewStatusSummary | None,
    applied_action_feedback: WorkflowAppliedActionFeedback | None,
) -> WorkflowReviewRenderContract | None:
    if panel_header is None and action_sections is None and status_summary is None:
        return None

    section_order = [
        section.section_id
        for section in (action_sections.items if action_sections is not None else [])
    ]
    default_focus_section_id = section_order[0] if section_order else None
    default_expanded_section_ids: list[str] = []
    if "recommended" in section_order:
        default_expanded_section_ids.append("recommended")
    if "blocked" in section_order:
        default_expanded_section_ids.append("blocked")
    if not default_expanded_section_ids and default_focus_section_id is not None:
        default_expanded_section_ids.append(default_focus_section_id)

    panel_tone = "attention" if panel_header is None else panel_header.tone
    return WorkflowReviewRenderContract(
        badge_order=[] if panel_header is None else [badge.badge_id for badge in panel_header.badges],
        panel_tone=panel_tone,
        display_priority=render_display_priority(panel_tone),
        section_order=section_order,
        default_focus_section_id=default_focus_section_id,
        default_expanded_section_ids=default_expanded_section_ids,
        section_presentations=[
            WorkflowReviewSectionPresentation(
                section_id=section_id,
                tone=section_tone(section_id),
                collapsible=section_id != "recommended",
            )
            for section_id in section_order
        ],
        sticky_primary_action_id=None if status_summary is None else status_summary.recommended_action_id,
        sticky_primary_action_emphasis=sticky_primary_action_emphasis(panel_tone),
        applied_feedback_dismissible=applied_action_feedback is not None,
    )


def render_display_priority(panel_tone: str) -> str:
    if panel_tone == "ready":
        return "normal"
    return "high"


def sticky_primary_action_emphasis(panel_tone: str) -> str:
    if panel_tone == "ready":
        return "normal"
    return "strong"


def section_tone(section_id: str) -> str:
    return {
        "recommended": "accent",
        "available": "neutral",
        "blocked": "muted",
    }.get(section_id, "neutral")
