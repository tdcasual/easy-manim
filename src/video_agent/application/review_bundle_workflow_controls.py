from __future__ import annotations

from typing import Any

from video_agent.domain.review_workflow_models import (
    WorkflowAvailableActionCard,
    WorkflowAvailableActionIntent,
    WorkflowAvailableActionMemoryChange,
    WorkflowAvailableActions,
    WorkflowAvailableActionSection,
    WorkflowAvailableActionSections,
    WorkflowMemoryActionContract,
    WorkflowMemoryActionExample,
    WorkflowMemoryRecommendations,
    WorkflowReviewPanelBadge,
    WorkflowReviewPanelEvent,
    WorkflowReviewPanelHeader,
    WorkflowReviewStatusSummary,
    WorkflowSuggestedAction,
    WorkflowSuggestedNextActions,
)


def build_workflow_memory_action_contract(
    recommendations: WorkflowMemoryRecommendations | None,
) -> WorkflowMemoryActionContract | None:
    if recommendations is None:
        return None

    pinned_ids = list(recommendations.pinned_memory_ids)
    candidate_pin_ids: list[str] = []
    for item in recommendations.items:
        if item.pinned or not item.memory_id:
            continue
        if item.memory_id not in candidate_pin_ids:
            candidate_pin_ids.append(item.memory_id)

    examples: list[WorkflowMemoryActionExample] = []
    if candidate_pin_ids:
        examples.append(
            WorkflowMemoryActionExample(
                name="pin",
                summary="Pin one or more recommended workflow memories before the next revision.",
                payload=workflow_memory_action_payload(
                    summary="Pin recommended workflow memory before revising",
                    feedback="Use the refreshed workflow memory in the next revision.",
                    pin_ids=candidate_pin_ids[:2],
                ),
            )
        )
    if pinned_ids:
        examples.append(
            WorkflowMemoryActionExample(
                name="unpin",
                summary="Remove outdated workflow memories while keeping the review decision flow unchanged.",
                payload=workflow_memory_action_payload(
                    summary="Remove outdated workflow memory before revising",
                    feedback="Continue with the current revision goals after dropping stale shared memory.",
                    unpin_ids=pinned_ids[:2],
                ),
            )
        )
    if candidate_pin_ids and pinned_ids:
        examples.append(
            WorkflowMemoryActionExample(
                name="replace",
                summary="Swap pinned workflow memory in a single review-decision request.",
                payload=workflow_memory_action_payload(
                    summary="Replace workflow memory set before revising",
                    feedback="Use the refreshed shared memory set for the next revision.",
                    pin_ids=candidate_pin_ids[:2],
                    unpin_ids=pinned_ids[:2],
                ),
            )
        )
    return WorkflowMemoryActionContract(examples=examples)


def build_suggested_next_actions(
    *,
    status: str,
    acceptance_blockers: list[str],
    workflow_memory_recommendations: WorkflowMemoryRecommendations | None,
    workflow_memory_action_contract: WorkflowMemoryActionContract | None,
) -> WorkflowSuggestedNextActions:
    examples_by_name = {
        example.name: example
        for example in (workflow_memory_action_contract.examples if workflow_memory_action_contract else [])
    }
    unpinned_ids = []
    if workflow_memory_recommendations is not None:
        unpinned_ids = [
            item.memory_id
            for item in workflow_memory_recommendations.items
            if item.memory_id and not item.pinned
        ]

    blocked_accept_action = WorkflowSuggestedAction(
        action_id="accept",
        title="Accept current result",
        summary="Acceptance is currently blocked by the workflow state.",
        blocked=True,
        reasons=list(acceptance_blockers),
        payload={
            "review_decision": {
                "decision": "accept",
                "summary": "Accept current result",
            }
        },
    )

    if status == "completed" and not acceptance_blockers:
        return WorkflowSuggestedNextActions(
            primary=WorkflowSuggestedAction(
                action_id="accept",
                title="Accept current result",
                summary="The current result is ready to be accepted as the best version.",
                blocked=False,
                reasons=[],
                payload={
                    "review_decision": {
                        "decision": "accept",
                        "summary": "Accept current result",
                    }
                },
            ),
            alternatives=[],
        )

    if unpinned_ids and "pin" in examples_by_name:
        alternatives: list[WorkflowSuggestedAction] = [
            WorkflowSuggestedAction(
                action_id="revise",
                title="Revise with current memory",
                summary="Create another revision without changing the shared workflow memory set.",
                payload=workflow_memory_action_payload(
                    summary="Revise with current workflow memory",
                    feedback="Continue iterating on the current task.",
                ),
            )
        ]
        if acceptance_blockers:
            alternatives.append(blocked_accept_action)
        return WorkflowSuggestedNextActions(
            primary=WorkflowSuggestedAction(
                action_id="pin_and_revise",
                title="Pin suggested memory and revise",
                summary="Attach the most relevant shared workflow memory before creating the next revision.",
                reasons=["workflow_memory_recommendations_available"],
                payload=dict(examples_by_name["pin"].payload),
            ),
            alternatives=alternatives,
        )

    if status == "failed":
        alternatives = [blocked_accept_action] if acceptance_blockers else []
        return WorkflowSuggestedNextActions(
            primary=WorkflowSuggestedAction(
                action_id="retry",
                title="Retry generation",
                summary="The current task failed, so the safest next step is a retry.",
                payload={
                    "review_decision": {
                        "decision": "retry",
                        "summary": "Retry failed task",
                    }
                },
            ),
            alternatives=alternatives,
        )

    alternatives = [blocked_accept_action] if acceptance_blockers else []
    return WorkflowSuggestedNextActions(
        primary=WorkflowSuggestedAction(
            action_id="revise",
            title="Create another revision",
            summary="Keep iterating on the current task with the existing workflow memory set.",
            payload=workflow_memory_action_payload(
                summary="Create another revision",
                feedback="Continue iterating on the current task.",
            ),
        ),
        alternatives=alternatives,
    )


def build_available_actions(
    suggested_next_actions: WorkflowSuggestedNextActions | None,
) -> WorkflowAvailableActions | None:
    if suggested_next_actions is None:
        return None

    action_items: list[WorkflowAvailableActionCard] = []
    seen_action_ids: set[str] = set()
    ordered_actions: list[tuple[WorkflowSuggestedAction, bool]] = []
    if suggested_next_actions.primary is not None:
        ordered_actions.append((suggested_next_actions.primary, True))
    ordered_actions.extend((item, False) for item in suggested_next_actions.alternatives)

    for action, is_primary in ordered_actions:
        if action.action_id in seen_action_ids:
            continue
        seen_action_ids.add(action.action_id)
        intent = build_action_intent(action.payload)
        action_items.append(
            WorkflowAvailableActionCard(
                action_id=action.action_id,
                title=action.title,
                button_label=button_label_for_action(action.action_id),
                action_family=resolve_action_family(intent),
                summary=action.summary,
                blocked=action.blocked,
                reasons=list(action.reasons),
                is_primary=is_primary,
                intent=intent,
                payload=dict(action.payload),
            )
        )

    return WorkflowAvailableActions(items=action_items)


def build_action_sections(
    available_actions: WorkflowAvailableActions | None,
) -> WorkflowAvailableActionSections | None:
    if available_actions is None:
        return None

    recommended_items = [item for item in available_actions.items if item.is_primary]
    available_items = [item for item in available_actions.items if not item.is_primary and not item.blocked]
    blocked_items = [item for item in available_actions.items if item.blocked]

    sections: list[WorkflowAvailableActionSection] = []
    if recommended_items:
        sections.append(
            WorkflowAvailableActionSection(
                section_id="recommended",
                title="Recommended next step",
                summary="The strongest next action based on the current workflow state.",
                items=recommended_items,
            )
        )
    if available_items:
        sections.append(
            WorkflowAvailableActionSection(
                section_id="available",
                title="Other available actions",
                summary="Alternative actions that can be taken immediately.",
                items=available_items,
            )
        )
    if blocked_items:
        sections.append(
            WorkflowAvailableActionSection(
                section_id="blocked",
                title="Blocked actions",
                summary="Actions that are currently unavailable until blockers are resolved.",
                items=blocked_items,
            )
        )
    return WorkflowAvailableActionSections(items=sections)


def build_workflow_review_status_summary(
    *,
    acceptance_blockers: list[str],
    pinned_memory_ids: list[str],
    recent_memory_events: list[Any],
    suggested_next_actions: WorkflowSuggestedNextActions | None,
    workflow_memory_recommendations: WorkflowMemoryRecommendations | None,
) -> WorkflowReviewStatusSummary:
    latest_memory_event = recent_memory_events[-1] if recent_memory_events else None
    pending_recommendation_ids: list[str] = []
    if workflow_memory_recommendations is not None:
        for item in workflow_memory_recommendations.items:
            if item.pinned or not item.memory_id:
                continue
            if item.memory_id not in pending_recommendation_ids:
                pending_recommendation_ids.append(item.memory_id)

    normalized_pinned_ids = [str(item) for item in pinned_memory_ids if str(item).strip()]
    primary_action_id = None
    if suggested_next_actions is not None and suggested_next_actions.primary is not None:
        primary_action_id = suggested_next_actions.primary.action_id

    return WorkflowReviewStatusSummary(
        recommended_action_id=primary_action_id,
        acceptance_ready=not acceptance_blockers,
        acceptance_blockers=list(acceptance_blockers),
        pinned_memory_count=len(normalized_pinned_ids),
        pending_memory_recommendation_count=len(pending_recommendation_ids),
        has_pending_memory_updates=bool(pending_recommendation_ids),
        latest_workflow_memory_event_type=None if latest_memory_event is None else latest_memory_event.event_type,
        latest_workflow_memory_event_at=None if latest_memory_event is None else latest_memory_event.created_at,
    )


def build_panel_header(
    *,
    recent_memory_events: list[Any],
    status_summary: WorkflowReviewStatusSummary | None,
) -> WorkflowReviewPanelHeader | None:
    if status_summary is None:
        return None

    badges: list[WorkflowReviewPanelBadge] = []
    if status_summary.recommended_action_id:
        badges.append(
            WorkflowReviewPanelBadge(
                badge_id="recommended_action",
                label="Recommended",
                value=status_summary.recommended_action_id,
                tone="ready" if status_summary.recommended_action_id == "accept" else "attention",
            )
        )
    if status_summary.pending_memory_recommendation_count > 0:
        badges.append(
            WorkflowReviewPanelBadge(
                badge_id="pending_memory",
                label="Pending memory",
                value=str(status_summary.pending_memory_recommendation_count),
                tone="attention",
            )
        )
    if status_summary.acceptance_blockers:
        badges.append(
            WorkflowReviewPanelBadge(
                badge_id="acceptance_blockers",
                label="Blockers",
                value=str(len(status_summary.acceptance_blockers)),
                tone="blocked",
            )
        )

    latest_event = recent_memory_events[-1] if recent_memory_events else None
    highlighted_event = None
    if latest_event is not None:
        highlighted_event = WorkflowReviewPanelEvent(
            event_type=latest_event.event_type,
            title=panel_event_title(latest_event.event_type),
            summary="Most recent shared workflow memory change.",
            memory_id=latest_event.memory_id,
            created_at=latest_event.created_at,
        )

    return WorkflowReviewPanelHeader(
        tone=panel_header_tone(status_summary),
        summary=panel_header_summary(status_summary),
        badges=badges,
        highlighted_event=highlighted_event,
    )


def build_action_intent(payload: dict[str, Any]) -> WorkflowAvailableActionIntent:
    review_decision_payload = payload.get("review_decision")
    review_decision = None
    if isinstance(review_decision_payload, dict):
        decision_value = str(review_decision_payload.get("decision") or "").strip()
        review_decision = decision_value or None
    pin_ids = extract_action_memory_ids(payload.get("pin_workflow_memory_ids"))
    unpin_ids = extract_action_memory_ids(payload.get("unpin_workflow_memory_ids"))
    has_memory_change = bool(pin_ids or unpin_ids)
    memory_change = None
    if has_memory_change:
        memory_change = WorkflowAvailableActionMemoryChange(
            pin_memory_ids=pin_ids,
            unpin_memory_ids=unpin_ids,
            pin_count=len(pin_ids),
            unpin_count=len(unpin_ids),
        )
    return WorkflowAvailableActionIntent(
        review_decision=review_decision,
        mutates_workflow_memory=has_memory_change,
        workflow_memory_change=memory_change,
    )


def resolve_action_family(intent: WorkflowAvailableActionIntent) -> str:
    if intent.mutates_workflow_memory and intent.review_decision is not None:
        return "combined"
    if intent.mutates_workflow_memory:
        return "workflow_memory"
    return "review_decision"


def extract_action_memory_ids(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def button_label_for_action(action_id: str) -> str:
    return {
        "accept": "Accept result",
        "revise": "Create revision",
        "retry": "Retry task",
        "pin_and_revise": "Pin memory and revise",
    }.get(action_id, "Run action")


def workflow_memory_action_payload(
    *,
    summary: str,
    feedback: str,
    pin_ids: list[str] | None = None,
    unpin_ids: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "review_decision": {
            "decision": "revise",
            "summary": summary,
            "feedback": feedback,
        }
    }
    if pin_ids:
        payload["pin_workflow_memory_ids"] = list(pin_ids)
    if unpin_ids:
        payload["unpin_workflow_memory_ids"] = list(unpin_ids)
    return payload


def panel_header_tone(status_summary: WorkflowReviewStatusSummary) -> str:
    if status_summary.acceptance_ready and status_summary.recommended_action_id == "accept":
        return "ready"
    if status_summary.acceptance_blockers and status_summary.recommended_action_id is None:
        return "blocked"
    return "attention"


def panel_header_summary(status_summary: WorkflowReviewStatusSummary) -> str:
    action_id = status_summary.recommended_action_id
    if action_id == "accept":
        return "Current result is ready to accept as the best version."
    if action_id == "pin_and_revise":
        return "Pin suggested workflow memory before creating the next revision."
    if action_id == "retry":
        return "Retry the failed task to continue the workflow."
    if action_id == "revise":
        return "Create another revision with the current workflow memory set."
    return "Review the current workflow state and choose the next action."


def panel_event_title(event_type: str) -> str:
    return {
        "workflow_memory_pinned": "Workflow memory pinned",
        "workflow_memory_unpinned": "Workflow memory unpinned",
    }.get(event_type, "Workflow memory updated")
