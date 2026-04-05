from __future__ import annotations

from video_agent.domain.video_thread_models import (
    VideoThreadComposerTarget,
    VideoThreadParticipant,
)


def build_composer_target(
    *,
    iteration,
    participants: list[VideoThreadParticipant],
    runs,
    results,
    turns,
) -> VideoThreadComposerTarget:
    if iteration is None:
        return VideoThreadComposerTarget(summary="No iteration is available yet.")
    target_result = target_result_for_iteration(iteration=iteration, results=results)
    addressed_participant = resolve_composer_participant(
        iteration=iteration,
        participants=participants,
        runs=runs,
        turns=turns,
    )
    latest_run = next((run for run in reversed(runs) if run.iteration_id == iteration.iteration_id), None)
    latest_agent_turn = next(
        (
            turn
            for turn in reversed(turns)
            if turn.iteration_id == iteration.iteration_id
            and turn.visibility == "product_safe"
            and turn.speaker_type == "agent"
        ),
        None,
    )
    fallback_agent_turn = latest_agent_turn or next(
        (
            turn
            for turn in reversed(turns)
            if turn.visibility == "product_safe" and turn.speaker_type == "agent"
        ),
        None,
    )
    target_agent_role = (
        iteration.responsible_role
        or (None if latest_run is None else latest_run.role)
        or (None if fallback_agent_turn is None else fallback_agent_turn.speaker_role)
    )
    target_agent_display_name = None
    target_agent_id = (
        (None if addressed_participant is None else addressed_participant.agent_id)
        or iteration.responsible_agent_id
        or (None if latest_run is None else latest_run.agent_id)
        or (None if fallback_agent_turn is None else fallback_agent_turn.speaker_agent_id)
    )
    if target_agent_id is not None:
        participant = next((item for item in participants if item.agent_id == target_agent_id), None)
        if participant is not None:
            target_agent_display_name = participant.display_name
    if target_agent_display_name is None and target_agent_role is not None:
        target_agent_display_name = target_agent_role.replace("_", " ").strip().title()
    summary_parts = [f"New messages will attach to {iteration.iteration_id}"]
    if target_result is not None:
        summary_parts.append(f"stay anchored to {target_result.result_id}")
    if target_agent_display_name is not None:
        summary_parts.append(f"hand off to {target_agent_display_name}")
    if len(summary_parts) > 1:
        summary = f"{', '.join(summary_parts[:-1])}, and {summary_parts[-1]}."
    else:
        summary = f"{summary_parts[0]}."
    return VideoThreadComposerTarget(
        iteration_id=iteration.iteration_id,
        result_id=None if target_result is None else target_result.result_id,
        addressed_participant_id=None if addressed_participant is None else addressed_participant.participant_id,
        addressed_agent_id=None if addressed_participant is None else addressed_participant.agent_id,
        addressed_display_name=None if addressed_participant is None else addressed_participant.display_name,
        agent_role=target_agent_role,
        agent_display_name=target_agent_display_name,
        summary=summary,
    )


def resolve_composer_participant(
    *,
    iteration,
    participants: list[VideoThreadParticipant],
    runs,
    turns,
) -> VideoThreadParticipant | None:
    participant_by_id = {participant.participant_id: participant for participant in participants}
    participant_by_agent_id = {
        participant.agent_id: participant
        for participant in participants
        if participant.agent_id is not None
    }
    if iteration.responsible_agent_id is not None:
        participant = participant_by_agent_id.get(iteration.responsible_agent_id)
        if participant is not None:
            return participant
    participant = participant_from_addressed_turn(
        turns=turns,
        participant_by_id=participant_by_id,
        iteration_id=iteration.iteration_id,
    )
    if participant is not None:
        return participant
    participant = participant_from_runs(
        runs=runs,
        participant_by_agent_id=participant_by_agent_id,
        iteration_id=iteration.iteration_id,
    )
    if participant is not None:
        return participant
    participant = participant_from_agent_turns(
        turns=turns,
        participant_by_agent_id=participant_by_agent_id,
        iteration_id=iteration.iteration_id,
    )
    if participant is not None:
        return participant
    participant = participant_from_addressed_turn(
        turns=turns,
        participant_by_id=participant_by_id,
        iteration_id=None,
    )
    if participant is not None:
        return participant
    return participant_from_agent_turns(
        turns=turns,
        participant_by_agent_id=participant_by_agent_id,
        iteration_id=None,
    )


def participant_from_addressed_turn(
    *,
    turns,
    participant_by_id: dict[str, VideoThreadParticipant],
    iteration_id: str | None,
) -> VideoThreadParticipant | None:
    for turn in reversed(turns):
        if iteration_id is not None and turn.iteration_id != iteration_id:
            continue
        if turn.addressed_participant_id is None:
            continue
        participant = participant_by_id.get(turn.addressed_participant_id)
        if participant is not None:
            return participant
    return None


def participant_from_runs(
    *,
    runs,
    participant_by_agent_id: dict[str, VideoThreadParticipant],
    iteration_id: str | None,
) -> VideoThreadParticipant | None:
    for run in reversed(runs):
        if iteration_id is not None and run.iteration_id != iteration_id:
            continue
        participant = participant_by_agent_id.get(run.agent_id)
        if participant is not None:
            return participant
    return None


def participant_from_agent_turns(
    *,
    turns,
    participant_by_agent_id: dict[str, VideoThreadParticipant],
    iteration_id: str | None,
) -> VideoThreadParticipant | None:
    for turn in reversed(turns):
        if iteration_id is not None and turn.iteration_id != iteration_id:
            continue
        if turn.visibility != "product_safe" or turn.speaker_type != "agent" or turn.speaker_agent_id is None:
            continue
        participant = participant_by_agent_id.get(turn.speaker_agent_id)
        if participant is not None:
            return participant
    return None


def target_result_for_iteration(*, iteration, results):
    selected = next(
        (
            result
            for result in reversed(results)
            if result.iteration_id == iteration.iteration_id and result.selected
        ),
        None,
    )
    if selected is not None:
        return selected
    explicit = next(
        (
            result
            for result in reversed(results)
            if result.result_id == iteration.selected_result_id
        ),
        None,
    )
    if explicit is not None:
        return explicit
    return next(
        (
            result
            for result in reversed(results)
            if result.iteration_id == iteration.iteration_id
        ),
        None,
    )
