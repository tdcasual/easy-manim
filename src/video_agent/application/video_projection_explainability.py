from __future__ import annotations

from video_agent.application.video_projection_history import latest_relevant_run
from video_agent.application.video_projection_iteration_story import (
    latest_relevant_agent_turn,
    resolve_participant_display_name,
)
from video_agent.domain.video_thread_models import (
    VideoThreadArtifactLineage,
    VideoThreadArtifactLineageItem,
    VideoThreadAuthorship,
    VideoThreadDecisionNote,
    VideoThreadDecisionNotes,
    VideoThreadLatestExplanation,
    VideoThreadParticipant,
)


def build_decision_notes(
    *,
    current_iteration,
    current_result,
    current_result_selection_reason: str | None,
    latest_explanation: VideoThreadLatestExplanation,
) -> VideoThreadDecisionNotes:
    items: list[VideoThreadDecisionNote] = []
    if current_result_selection_reason:
        items.append(
            VideoThreadDecisionNote(
                note_id=f"decision-selection-{None if current_result is None else current_result.result_id or 'current'}",
                note_kind="selection_rationale",
                title="Why this version is selected",
                summary=current_result_selection_reason,
                emphasis="primary",
                source_iteration_id=None if current_iteration is None else current_iteration.iteration_id,
                source_result_id=None if current_result is None else current_result.result_id,
            )
        )
    if latest_explanation.summary:
        items.append(
            VideoThreadDecisionNote(
                note_id=f"decision-explanation-{latest_explanation.turn_id or 'latest'}",
                note_kind="agent_explanation",
                title=latest_explanation.title or "Latest visible explanation",
                summary=latest_explanation.summary,
                emphasis="supporting",
                source_iteration_id=None if current_iteration is None else current_iteration.iteration_id,
                source_turn_id=latest_explanation.turn_id,
                source_result_id=None if current_result is None else current_result.result_id,
                actor_display_name=latest_explanation.speaker_display_name,
                actor_role=latest_explanation.speaker_role,
            )
        )
    if current_iteration is not None and current_iteration.goal.strip():
        items.append(
            VideoThreadDecisionNote(
                note_id=f"decision-goal-{current_iteration.iteration_id}",
                note_kind="iteration_goal",
                title="Current iteration goal",
                summary=current_iteration.goal,
                emphasis="supporting",
                source_iteration_id=current_iteration.iteration_id,
                actor_display_name="Owner",
                actor_role="owner",
            )
        )
    return VideoThreadDecisionNotes(items=items)


def build_artifact_lineage(
    *,
    participants: list[VideoThreadParticipant],
    iterations,
    results,
    turns,
    runs,
    selected_result_id: str | None,
    current_iteration_id: str | None,
    current_result_selection_reason: str | None,
    latest_explanation: VideoThreadLatestExplanation,
) -> VideoThreadArtifactLineage:
    result_by_id = {result.result_id: result for result in results}
    items: list[VideoThreadArtifactLineageItem] = []
    ordered_iterations = sorted(iterations, key=lambda item: (item.created_at, item.iteration_id))

    for iteration in ordered_iterations:
        to_result = lineage_target_result(
            iteration=iteration,
            results=results,
            result_by_id=result_by_id,
        )
        if to_result is None and iteration.source_result_id is None:
            continue

        trigger_turn = lineage_trigger_turn(turns=turns, iteration=iteration)
        latest_run = latest_relevant_run(runs=runs, iteration_id=iteration.iteration_id)
        latest_agent_turn = latest_relevant_agent_turn(
            turns=turns,
            iteration_id=iteration.iteration_id,
        )
        is_selected = to_result is not None and to_result.result_id == selected_result_id
        is_active = current_iteration_id == iteration.iteration_id and not is_selected
        status = "selected" if is_selected else "active" if is_active else "origin" if iteration.source_result_id is None else "superseded"
        emphasis = "primary" if is_selected else "supporting" if is_active else "context" if iteration.source_result_id is None else "supporting"

        actor_role = None
        actor_display_name = None
        if latest_run is not None:
            actor_role = latest_run.role
            actor_display_name = resolve_participant_display_name(
                participants=participants,
                agent_id=latest_run.agent_id,
                role=latest_run.role,
            )
        elif latest_agent_turn is not None:
            actor_role = latest_agent_turn.speaker_role
            actor_display_name = resolve_participant_display_name(
                participants=participants,
                agent_id=latest_agent_turn.speaker_agent_id,
                role=latest_agent_turn.speaker_role,
            )
        elif iteration.responsible_role or iteration.responsible_agent_id:
            actor_role = iteration.responsible_role
            actor_display_name = resolve_participant_display_name(
                participants=participants,
                agent_id=iteration.responsible_agent_id,
                role=iteration.responsible_role,
            )

        change_summary = ""
        if to_result is not None and to_result.result_summary.strip():
            change_summary = to_result.result_summary.strip()
        elif iteration.focus_summary and iteration.focus_summary.strip():
            change_summary = iteration.focus_summary.strip()
        else:
            change_summary = iteration.goal.strip()

        change_reason = ""
        if trigger_turn is not None and trigger_turn.summary.strip():
            change_reason = trigger_turn.summary.strip()
        elif is_selected and current_result_selection_reason:
            change_reason = current_result_selection_reason
        elif latest_agent_turn is not None and latest_agent_turn.summary.strip():
            change_reason = latest_agent_turn.summary.strip()
        elif latest_explanation.summary and current_iteration_id == iteration.iteration_id:
            change_reason = latest_explanation.summary

        items.append(
            VideoThreadArtifactLineageItem(
                lineage_id=f"lineage-{iteration.iteration_id}",
                iteration_id=iteration.iteration_id,
                from_result_id=iteration.source_result_id,
                to_result_id=None if to_result is None else to_result.result_id,
                change_summary=change_summary,
                change_reason=change_reason,
                trigger_turn_id=None if trigger_turn is None else trigger_turn.turn_id,
                trigger_label=lineage_trigger_label(trigger_turn),
                actor_display_name=actor_display_name,
                actor_role=actor_role,
                emphasis=emphasis,
                status=status,
            )
        )

    return VideoThreadArtifactLineage(
        summary="How the current video evolved across visible revisions.",
        selected_result_id=selected_result_id,
        items=items,
    )


def lineage_target_result(*, iteration, results, result_by_id):
    if iteration.selected_result_id and iteration.selected_result_id in result_by_id:
        return result_by_id[iteration.selected_result_id]
    for result in reversed(results):
        if result.iteration_id == iteration.iteration_id:
            return result
    return None


def lineage_trigger_turn(*, turns, iteration):
    if iteration.initiated_by_turn_id:
        for turn in turns:
            if turn.turn_id == iteration.initiated_by_turn_id and turn.visibility == "product_safe":
                return turn
    for turn in reversed(turns):
        if turn.iteration_id != iteration.iteration_id or turn.visibility != "product_safe":
            continue
        if turn.turn_type == "owner_request":
            return turn
    return None


def lineage_trigger_label(trigger_turn) -> str | None:
    if trigger_turn is None:
        return None
    if trigger_turn.intent_type == "generate":
        return "Owner started the thread"
    if trigger_turn.intent_type == "request_revision":
        return "Owner requested revision"
    if trigger_turn.intent_type == "request_explanation":
        return "Owner asked for explanation"
    if trigger_turn.intent_type == "discuss":
        return "Owner added note"
    return trigger_turn.title or "Visible trigger"


def build_authorship(
    *,
    participants: list[VideoThreadParticipant],
    current_iteration,
    current_result,
    turns,
    runs,
) -> VideoThreadAuthorship:
    source_run = latest_relevant_run(
        runs=runs,
        iteration_id=None if current_iteration is None else current_iteration.iteration_id,
    )
    source_turn = latest_relevant_agent_turn(
        turns=turns,
        iteration_id=None if current_iteration is None else current_iteration.iteration_id,
    )
    primary_agent_display_name = None
    primary_agent_role = None
    source_iteration_id = None
    source_run_id = None
    source_turn_id = None

    if source_run is not None:
        primary_agent_display_name = resolve_participant_display_name(
            participants=participants,
            agent_id=source_run.agent_id,
            role=source_run.role,
        )
        primary_agent_role = source_run.role
        source_iteration_id = source_run.iteration_id
        source_run_id = source_run.run_id
    elif source_turn is not None:
        primary_agent_display_name = resolve_participant_display_name(
            participants=participants,
            agent_id=source_turn.speaker_agent_id,
            role=source_turn.speaker_role,
        )
        primary_agent_role = source_turn.speaker_role
        source_iteration_id = source_turn.iteration_id
        source_turn_id = source_turn.turn_id
    elif current_iteration is not None:
        primary_agent_display_name = resolve_participant_display_name(
            participants=participants,
            agent_id=current_iteration.responsible_agent_id,
            role=current_iteration.responsible_role,
        )
        primary_agent_role = current_iteration.responsible_role
        source_iteration_id = current_iteration.iteration_id

    summary = ""
    if primary_agent_display_name or primary_agent_role:
        actor_label = primary_agent_display_name or primary_agent_role or "The active agent"
        if current_result is not None:
            summary = (
                f"{actor_label} is the latest visible agent shaping the selected cut for this iteration."
            )
        elif current_iteration is not None:
            summary = f"{actor_label} is the latest visible agent shaping the active iteration."
        else:
            summary = f"{actor_label} is the latest visible agent in this collaboration thread."

    return VideoThreadAuthorship(
        summary=summary,
        primary_agent_display_name=primary_agent_display_name,
        primary_agent_role=primary_agent_role,
        source_iteration_id=source_iteration_id,
        source_run_id=source_run_id,
        source_turn_id=source_turn_id,
    )


def build_latest_explanation(
    *,
    participants: list[VideoThreadParticipant],
    current_iteration,
    turns,
    runs,
) -> VideoThreadLatestExplanation:
    for turn in reversed(turns):
        if turn.visibility != "product_safe" or turn.turn_type != "agent_explanation":
            continue
        return VideoThreadLatestExplanation(
            title=turn.title or "Latest visible explanation",
            summary=turn.summary,
            turn_id=turn.turn_id,
            speaker_display_name=resolve_participant_display_name(
                participants=participants,
                agent_id=turn.speaker_agent_id,
                role=turn.speaker_role,
            ),
            speaker_role=turn.speaker_role,
        )
    latest_run = runs[-1] if runs else None
    if latest_run is not None and latest_run.output_summary:
        return VideoThreadLatestExplanation(
            title="Latest visible explanation",
            summary=latest_run.output_summary,
            speaker_display_name=resolve_participant_display_name(
                participants=participants,
                agent_id=latest_run.agent_id,
                role=latest_run.role,
            ),
            speaker_role=latest_run.role,
        )
    if current_iteration is not None and current_iteration.goal:
        return VideoThreadLatestExplanation(
            title="Latest visible explanation",
            summary=f"The active iteration is currently focused on '{current_iteration.goal}'.",
            speaker_display_name=resolve_participant_display_name(
                participants=participants,
                agent_id=current_iteration.responsible_agent_id,
                role=current_iteration.responsible_role,
            ),
            speaker_role=current_iteration.responsible_role,
        )
    return VideoThreadLatestExplanation()
