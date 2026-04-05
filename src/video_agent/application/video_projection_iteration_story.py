from __future__ import annotations

from video_agent.application.video_projection_composer_target import target_result_for_iteration
from video_agent.domain.video_thread_models import (
    VideoThreadIterationCompare,
    VideoThreadLatestExplanation,
    VideoThreadParticipant,
    VideoThreadRationaleSnapshot,
    VideoThreadRationaleSnapshots,
)


def build_rationale_snapshots(
    *,
    participants: list[VideoThreadParticipant],
    iterations,
    results,
    turns,
    runs,
    current_iteration_id: str | None,
    current_result_selection_reason: str | None,
) -> VideoThreadRationaleSnapshots:
    items: list[VideoThreadRationaleSnapshot] = []
    result_by_id = {result.result_id: result for result in results}
    ordered_iterations = sorted(iterations, key=lambda item: (item.created_at, item.iteration_id))

    for iteration in ordered_iterations:
        latest_explanation_turn = latest_iteration_explanation_turn(
            turns=turns,
            iteration_id=iteration.iteration_id,
        )
        latest_owner_turn = latest_iteration_owner_turn(
            turns=turns,
            iteration_id=iteration.iteration_id,
        )
        target_result = lineage_target_result(
            iteration=iteration,
            results=results,
            result_by_id=result_by_id,
        )
        is_current = iteration.iteration_id == current_iteration_id

        snapshot_kind = "owner_goal"
        title = "Original direction" if iteration.parent_iteration_id is None else "Revision goal"
        summary = (
            latest_owner_turn.summary.strip()
            if latest_owner_turn is not None and latest_owner_turn.summary.strip()
            else latest_owner_turn.title.strip()
            if latest_owner_turn is not None and latest_owner_turn.title.strip()
            else iteration.goal.strip()
        )
        source_turn_id = None if latest_owner_turn is None else latest_owner_turn.turn_id
        source_result_id = None if target_result is None else target_result.result_id
        actor_display_name = "Owner"
        actor_role = "owner"

        if is_current and current_result_selection_reason and target_result is not None:
            snapshot_kind = "selection_rationale"
            title = "Why the current revision is selected"
            summary = current_result_selection_reason
            source_turn_id = None
            source_result_id = None if target_result is None else target_result.result_id
            actor_role = current_result_author_role(
                current_iteration=iteration,
                runs=runs,
                turns=turns,
            )
            actor_display_name = current_result_author_display_name(
                participants=participants,
                current_iteration=iteration,
                runs=runs,
                turns=turns,
            )
        elif latest_explanation_turn is not None and latest_explanation_turn.summary.strip():
            snapshot_kind = "agent_explanation"
            title = latest_explanation_turn.title or "Visible rationale"
            summary = latest_explanation_turn.summary.strip()
            source_turn_id = latest_explanation_turn.turn_id
            source_result_id = latest_explanation_turn.related_result_id or (
                None if target_result is None else target_result.result_id
            )
            actor_display_name = resolve_participant_display_name(
                participants=participants,
                agent_id=latest_explanation_turn.speaker_agent_id,
                role=latest_explanation_turn.speaker_role,
            )
            actor_role = latest_explanation_turn.speaker_role

        items.append(
            VideoThreadRationaleSnapshot(
                snapshot_id=f"snapshot-{iteration.iteration_id}",
                iteration_id=iteration.iteration_id,
                snapshot_kind=snapshot_kind,
                title=title,
                summary=summary,
                source_turn_id=source_turn_id,
                source_result_id=source_result_id,
                actor_display_name=actor_display_name,
                actor_role=actor_role,
                emphasis="primary" if is_current else "context",
                status="current" if is_current else "archived",
            )
        )

    return VideoThreadRationaleSnapshots(
        summary="Canonical product-safe why notes across iterations.",
        current_iteration_id=current_iteration_id,
        items=items,
    )


def build_iteration_compare(
    *,
    participants: list[VideoThreadParticipant],
    iterations,
    results,
    turns,
    runs,
    current_iteration,
    current_result,
    current_result_selection_reason: str | None,
    latest_explanation: VideoThreadLatestExplanation,
) -> VideoThreadIterationCompare:
    if current_iteration is None:
        return VideoThreadIterationCompare(
            summary="No iteration is selected yet.",
        )

    ordered_iterations = sorted(iterations, key=lambda item: (item.created_at, item.iteration_id))
    current_index = next(
        (
            index
            for index, iteration in enumerate(ordered_iterations)
            if iteration.iteration_id == current_iteration.iteration_id
        ),
        None,
    )
    previous_iteration = (
        ordered_iterations[current_index - 1]
        if current_index is not None and current_index > 0
        else None
    )
    previous_result = (
        None
        if previous_iteration is None
        else target_result_for_iteration(iteration=previous_iteration, results=results)
    )
    current_target_result = current_result or target_result_for_iteration(
        iteration=current_iteration,
        results=results,
    )

    continuity_status, continuity_summary = build_iteration_continuity(
        participants=participants,
        previous_iteration=previous_iteration,
        current_iteration=current_iteration,
        turns=turns,
        runs=runs,
    )
    if previous_iteration is None:
        return VideoThreadIterationCompare(
            summary="Compare the current selected cut against the nearest earlier visible iteration.",
            previous_iteration_id=None,
            current_iteration_id=current_iteration.iteration_id,
            previous_result_id=None,
            current_result_id=None if current_target_result is None else current_target_result.result_id,
            change_summary="" if current_target_result is None else current_target_result.result_summary,
            rationale_shift_summary=(
                current_iteration.goal
                or current_result_selection_reason
                or latest_explanation.summary
            ),
            continuity_status=continuity_status,
            continuity_summary=continuity_summary,
        )

    previous_rationale = iteration_rationale_summary(
        iteration=previous_iteration,
        target_result=previous_result,
        turns=turns,
    )
    current_rationale = (
        current_iteration.goal
        or current_result_selection_reason
        or latest_explanation.summary
        or iteration_rationale_summary(
            iteration=current_iteration,
            target_result=current_target_result,
            turns=turns,
        )
    )
    return VideoThreadIterationCompare(
        summary="Compare the current selected cut against the nearest earlier visible iteration.",
        previous_iteration_id=previous_iteration.iteration_id,
        current_iteration_id=current_iteration.iteration_id,
        previous_result_id=None if previous_result is None else previous_result.result_id,
        current_result_id=None if current_target_result is None else current_target_result.result_id,
        change_summary="" if current_target_result is None else current_target_result.result_summary,
        rationale_shift_summary=(
            f"The previous cut focused on {previous_rationale}. "
            f"The current revision shifts toward {current_rationale}."
        ),
        continuity_status=continuity_status,
        continuity_summary=continuity_summary,
    )


def build_iteration_continuity(
    *,
    participants: list[VideoThreadParticipant],
    previous_iteration,
    current_iteration,
    turns,
    runs,
) -> tuple[str, str]:
    if previous_iteration is None:
        return "new", "This is the first visible iteration in the thread, so there is no earlier participant continuity to preserve."
    previous_identity = iteration_participant_identity(
        participants=participants,
        iteration=previous_iteration,
        turns=turns,
        runs=runs,
    )
    current_identity = iteration_participant_identity(
        participants=participants,
        iteration=current_iteration,
        turns=turns,
        runs=runs,
    )
    previous_label = previous_identity["display_name"] or previous_identity["role"] or "the previous owner-safe context"
    current_label = current_identity["display_name"] or current_identity["role"] or "the current owner-safe context"
    if (
        previous_identity["agent_id"] is not None
        and current_identity["agent_id"] is not None
        and previous_identity["agent_id"] == current_identity["agent_id"]
    ):
        return "preserved", f"Participant continuity stays with {current_label} across the compared iterations."
    if (
        previous_identity["agent_id"] is None
        and current_identity["agent_id"] is None
        and previous_identity["role"] is not None
        and previous_identity["role"] == current_identity["role"]
    ):
        return "preserved", f"Role continuity stays with {current_label} across the compared iterations."
    if previous_label == current_label:
        return "preserved", f"Participant continuity stays with {current_label} across the compared iterations."
    if previous_identity["agent_id"] is None and current_identity["agent_id"] is None and previous_identity["role"] is None and current_identity["role"] is None:
        return "unknown", "The compared iterations do not expose enough participant continuity to make a stable comparison."
    return "changed", f"Participant continuity changed from {previous_label} to {current_label} between the compared iterations."


def iteration_participant_identity(
    *,
    participants: list[VideoThreadParticipant],
    iteration,
    turns,
    runs,
) -> dict[str, str | None]:
    latest_run = next((run for run in reversed(runs) if run.iteration_id == iteration.iteration_id), None)
    if latest_run is not None:
        return {
            "agent_id": latest_run.agent_id,
            "role": latest_run.role,
            "display_name": resolve_participant_display_name(
                participants=participants,
                agent_id=latest_run.agent_id,
                role=latest_run.role,
            ),
        }
    latest_agent_turn = latest_relevant_agent_turn(turns=turns, iteration_id=iteration.iteration_id)
    if latest_agent_turn is not None:
        return {
            "agent_id": latest_agent_turn.speaker_agent_id,
            "role": latest_agent_turn.speaker_role,
            "display_name": resolve_participant_display_name(
                participants=participants,
                agent_id=latest_agent_turn.speaker_agent_id,
                role=latest_agent_turn.speaker_role,
            ),
        }
    latest_owner_turn = latest_iteration_owner_turn(turns=turns, iteration_id=iteration.iteration_id)
    if latest_owner_turn is not None and (
        latest_owner_turn.addressed_agent_id is not None or latest_owner_turn.addressed_participant_id is not None
    ):
        participant = next(
            (
                item
                for item in participants
                if item.participant_id == latest_owner_turn.addressed_participant_id
                or item.agent_id == latest_owner_turn.addressed_agent_id
            ),
            None,
        )
        return {
            "agent_id": latest_owner_turn.addressed_agent_id or (None if participant is None else participant.agent_id),
            "role": None if participant is None else participant.role,
            "display_name": None if participant is None else participant.display_name,
        }
    return {
        "agent_id": iteration.responsible_agent_id,
        "role": iteration.responsible_role,
        "display_name": resolve_participant_display_name(
            participants=participants,
            agent_id=iteration.responsible_agent_id,
            role=iteration.responsible_role,
        ),
    }


def iteration_rationale_summary(*, iteration, target_result, turns) -> str:
    latest_owner_turn = latest_iteration_owner_turn(
        turns=turns,
        iteration_id=iteration.iteration_id,
    )
    if latest_owner_turn is not None and latest_owner_turn.summary.strip():
        return latest_owner_turn.summary.strip()
    if latest_owner_turn is not None and latest_owner_turn.title.strip():
        return latest_owner_turn.title.strip()
    if target_result is not None and target_result.result_summary.strip():
        return target_result.result_summary.strip()
    return iteration.goal.strip()


def lineage_target_result(*, iteration, results, result_by_id):
    if iteration.selected_result_id and iteration.selected_result_id in result_by_id:
        return result_by_id[iteration.selected_result_id]
    for result in reversed(results):
        if result.iteration_id == iteration.iteration_id:
            return result
    return None


def latest_iteration_explanation_turn(*, turns, iteration_id: str):
    for turn in reversed(turns):
        if (
            turn.iteration_id == iteration_id
            and turn.visibility == "product_safe"
            and turn.turn_type == "agent_explanation"
        ):
            return turn
    return None


def latest_iteration_owner_turn(*, turns, iteration_id: str):
    for turn in reversed(turns):
        if (
            turn.iteration_id == iteration_id
            and turn.visibility == "product_safe"
            and turn.turn_type == "owner_request"
        ):
            return turn
    return None


def latest_relevant_agent_turn(*, turns, iteration_id: str | None):
    for turn in reversed(turns):
        if turn.visibility != "product_safe" or turn.speaker_type != "agent":
            continue
        if iteration_id is None or turn.iteration_id == iteration_id:
            return turn
    return None


def resolve_participant_display_name(
    *,
    participants: list[VideoThreadParticipant],
    agent_id: str | None,
    role: str | None,
) -> str | None:
    if agent_id:
        for participant in participants:
            if participant.agent_id == agent_id:
                return participant.display_name
    if role:
        return role.replace("_", " ").strip().title() or "Agent"
    return None


def current_result_author_role(*, current_iteration, runs, turns) -> str | None:
    latest_run = runs[-1] if runs else None
    if latest_run is not None:
        return latest_run.role
    for turn in reversed(turns):
        if turn.speaker_type == "agent" and turn.speaker_role:
            return turn.speaker_role
    if current_iteration is not None:
        return current_iteration.responsible_role
    return None


def current_result_author_display_name(
    *,
    participants: list[VideoThreadParticipant],
    current_iteration,
    runs,
    turns,
) -> str | None:
    latest_run = runs[-1] if runs else None
    if latest_run is not None:
        for participant in participants:
            if participant.agent_id == latest_run.agent_id:
                return participant.display_name
        return latest_run.role.replace("_", " ").strip().title() or "Agent"
    for turn in reversed(turns):
        if turn.speaker_type == "agent":
            if turn.speaker_agent_id:
                for participant in participants:
                    if participant.agent_id == turn.speaker_agent_id:
                        return participant.display_name
            if turn.speaker_role:
                return turn.speaker_role.replace("_", " ").strip().title() or "Agent"
    if current_iteration is not None and current_iteration.responsible_agent_id:
        for participant in participants:
            if participant.agent_id == current_iteration.responsible_agent_id:
                return participant.display_name
    if current_iteration is not None and current_iteration.responsible_role:
        return current_iteration.responsible_role.replace("_", " ").strip().title() or "Agent"
    return None
