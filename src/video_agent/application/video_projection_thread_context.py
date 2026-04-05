from __future__ import annotations

from video_agent.application.video_projection_composer_target import build_composer_target
from video_agent.domain.video_thread_models import (
    VideoThreadAction,
    VideoThreadActions,
    VideoThreadComposer,
    VideoThreadComposerTarget,
    VideoThreadParticipant,
    VideoThreadParticipantManagement,
    VideoThreadResponsibility,
)


def resolve_participants(*, store_participants: list[VideoThreadParticipant], thread) -> list[VideoThreadParticipant]:
    if store_participants:
        return store_participants
    return [
        VideoThreadParticipant(
            thread_id=thread.thread_id,
            participant_id="owner",
            participant_type="owner",
            agent_id=thread.owner_agent_id,
            role="owner",
            display_name="Owner",
        )
    ]


def build_participant_management(
    *,
    owner_agent_id: str,
    participants: list[VideoThreadParticipant],
    viewer_agent_id: str | None,
) -> VideoThreadParticipantManagement:
    can_manage = viewer_agent_id is None or viewer_agent_id == owner_agent_id
    removable_participant_ids = [
        participant.participant_id
        for participant in participants
        if participant.participant_type != "owner"
    ]
    return VideoThreadParticipantManagement(
        can_manage=can_manage,
        can_invite=can_manage,
        can_remove=can_manage and bool(removable_participant_ids),
        removable_participant_ids=removable_participant_ids if can_manage else [],
        disabled_reason="" if can_manage else "Only the thread owner can manage participants.",
        context_hint=(
            "Invite reviewers or helper agents into this thread."
            if can_manage
            else "Only the thread owner can invite or remove participants."
        ),
    )


def build_responsibility(
    *,
    current_iteration,
    current_result,
    runs,
) -> VideoThreadResponsibility:
    latest_run = runs[-1] if runs else None
    owner_action_required = "none"
    if current_result is not None:
        owner_action_required = "review_latest_result"
    elif latest_run is not None and latest_run.status in {"pending", "running"}:
        owner_action_required = "wait_for_agent"
    elif current_iteration is not None and current_iteration.requested_action == "revise":
        owner_action_required = "provide_follow_up"

    expected_agent_role = None
    expected_agent_id = None
    if current_iteration is not None:
        expected_agent_role = current_iteration.responsible_role
        expected_agent_id = current_iteration.responsible_agent_id
    if latest_run is not None:
        expected_agent_role = expected_agent_role or latest_run.role
        expected_agent_id = expected_agent_id or latest_run.agent_id

    return VideoThreadResponsibility(
        owner_action_required=owner_action_required,
        expected_agent_role=expected_agent_role,
        expected_agent_id=expected_agent_id,
    )


def build_actions(
    *,
    current_iteration,
    current_result,
) -> VideoThreadActions:
    has_iteration = current_iteration is not None
    has_result = current_result is not None
    return VideoThreadActions(
        items=[
            VideoThreadAction(
                action_id="request_revision",
                label="Request revision",
                description=(
                    "Create the next revision from the selected result and current goal."
                    if has_result
                    else "Create the next revision for the active iteration."
                ),
                tone="strong",
                disabled=not has_iteration,
                disabled_reason="" if has_iteration else "No active iteration is available yet.",
            ),
            VideoThreadAction(
                action_id="request_explanation",
                label="Ask why",
                description="Request a product-safe explanation for the current direction.",
                tone="neutral",
                disabled=not has_iteration,
                disabled_reason="" if has_iteration else "No active iteration is available yet.",
            ),
            VideoThreadAction(
                action_id="discuss",
                label="Add note",
                description="Record context without creating a new revision immediately.",
                tone="muted",
                disabled=not has_iteration,
                disabled_reason="" if has_iteration else "No active iteration is available yet.",
            ),
        ]
    )


def build_composer(
    *,
    participants: list[VideoThreadParticipant],
    current_iteration,
    current_result,
    runs,
    results,
    turns,
) -> VideoThreadComposer:
    disabled = current_iteration is None
    context_hint = ""
    if current_result is not None and current_result.result_summary.strip():
        context_hint = (
            "The selected cut is ready for review or a focused revision request: "
            f"{current_result.result_summary.strip()}"
        )
    elif current_iteration is not None and current_iteration.goal.strip():
        context_hint = f"The active iteration is focused on: {current_iteration.goal.strip()}"
    target = VideoThreadComposerTarget(summary="No iteration is available yet.")
    if current_iteration is not None:
        target = build_composer_target(
            iteration=current_iteration,
            participants=participants,
            runs=runs,
            results=results,
            turns=turns,
        )
    return VideoThreadComposer(
        disabled=disabled,
        disabled_reason="" if not disabled else "No active iteration is available yet.",
        context_hint=context_hint,
        target=target,
    )
