from __future__ import annotations

from video_agent.application.video_projection_collaboration_runtime import (
    display_name_for_addressed_turn,
    display_name_for_turn,
)
from video_agent.application.video_projection_composer_target import (
    build_composer_target,
    target_result_for_iteration,
)
from video_agent.domain.video_thread_models import (
    VideoThreadIterationDetail,
    VideoThreadIterationDetailResult,
    VideoThreadIterationDetailRun,
    VideoThreadIterationDetailSummary,
    VideoThreadIterationDetailTurn,
    VideoThreadIterationExecutionSummary,
    VideoThreadParticipant,
)


def build_iteration_detail_summary(
    *,
    thread_id: str,
    selected_iteration,
    participants: list[VideoThreadParticipant],
    turns,
    runs,
    results,
) -> VideoThreadIterationDetailSummary:
    if selected_iteration is None:
        return VideoThreadIterationDetailSummary(
            summary="No iteration is selected yet.",
        )
    iteration_turns = [
        turn
        for turn in turns
        if turn.iteration_id == selected_iteration.iteration_id and turn.visibility == "product_safe"
    ]
    iteration_runs = [run for run in runs if run.iteration_id == selected_iteration.iteration_id]
    iteration_results = [result for result in results if result.iteration_id == selected_iteration.iteration_id]
    summary = (
        f"This iteration is focused on {selected_iteration.goal.strip()} "
        f"and currently tracks {len(iteration_turns)} visible turns, {len(iteration_runs)} runs, "
        f"and {len(iteration_results)} results."
        if selected_iteration.goal.strip()
        else f"This iteration currently tracks {len(iteration_turns)} visible turns, "
        f"{len(iteration_runs)} runs, and {len(iteration_results)} results."
    )
    return VideoThreadIterationDetailSummary(
        summary=summary,
        selected_iteration_id=selected_iteration.iteration_id,
        resource_uri=f"video-thread://{thread_id}/iterations/{selected_iteration.iteration_id}.json",
        turn_count=len(iteration_turns),
        run_count=len(iteration_runs),
        result_count=len(iteration_results),
        execution_summary=build_iteration_execution_summary(
            iteration=selected_iteration,
            participants=participants,
            runs=iteration_runs,
            results=iteration_results,
            turns=iteration_turns,
        ),
    )


def build_iteration_detail(
    *,
    thread_id: str,
    iteration,
    participants: list[VideoThreadParticipant],
    turns,
    runs,
    results,
) -> VideoThreadIterationDetail:
    participant_by_agent_id = {
        participant.agent_id: participant
        for participant in participants
        if participant.agent_id
    }
    iteration_turns = [
        turn
        for turn in turns
        if turn.iteration_id == iteration.iteration_id and turn.visibility == "product_safe"
    ]
    iteration_runs = [run for run in runs if run.iteration_id == iteration.iteration_id]
    iteration_results = [result for result in results if result.iteration_id == iteration.iteration_id]
    summary = (
        f"This iteration is carrying the goal '{iteration.goal.strip()}' across visible discussion, "
        f"agent activity, and produced results."
        if iteration.goal.strip()
        else "This iteration captures the visible discussion, agent activity, and produced results."
    )
    composer_target = build_composer_target(
        iteration=iteration,
        participants=participants,
        runs=iteration_runs,
        results=iteration_results,
        turns=iteration_turns,
    )
    return VideoThreadIterationDetail(
        thread_id=thread_id,
        iteration_id=iteration.iteration_id,
        summary=summary,
        execution_summary=build_iteration_execution_summary(
            iteration=iteration,
            participants=participants,
            runs=iteration_runs,
            results=iteration_results,
            turns=iteration_turns,
        ),
        composer_target=composer_target,
        iteration=iteration,
        turns=[
            VideoThreadIterationDetailTurn(
                turn_id=turn.turn_id,
                turn_type=turn.turn_type,
                title=turn.title,
                summary=turn.summary,
                intent_type=turn.intent_type,
                reply_to_turn_id=turn.reply_to_turn_id,
                related_result_id=turn.related_result_id,
                addressed_participant_id=turn.addressed_participant_id,
                addressed_agent_id=turn.addressed_agent_id,
                addressed_display_name=display_name_for_addressed_turn(
                    turn=turn,
                    participants=participants,
                ),
                speaker_display_name=display_name_for_turn(
                    turn=turn,
                    participants=participants,
                ),
                speaker_role=turn.speaker_role,
                created_at=turn.created_at,
            )
            for turn in iteration_turns
        ],
        runs=[
            VideoThreadIterationDetailRun(
                run_id=run.run_id,
                agent_id=run.agent_id,
                agent_display_name=(
                    participant_by_agent_id.get(run.agent_id).display_name
                    if participant_by_agent_id.get(run.agent_id) is not None
                    else run.role.replace("_", " ").strip().title()
                ),
                role=run.role,
                status=run.status,
                phase=run.phase,
                output_summary=run.output_summary,
                task_id=run.task_id,
                created_at=run.created_at,
            )
            for run in iteration_runs
        ],
        results=[
            VideoThreadIterationDetailResult(
                result_id=result.result_id,
                status=result.status,
                result_summary=result.result_summary,
                selected=result.selected,
                video_resource=result.video_resource,
                created_at=result.created_at,
            )
            for result in iteration_results
        ],
    )


def build_iteration_execution_summary(
    *,
    iteration,
    participants: list[VideoThreadParticipant],
    runs,
    results,
    turns,
) -> VideoThreadIterationExecutionSummary:
    target_result = target_result_for_iteration(iteration=iteration, results=results)
    composer_target = build_composer_target(
        iteration=iteration,
        participants=participants,
        runs=runs,
        results=results,
        turns=turns,
    )
    latest_owner_turn = next(
        (
            turn
            for turn in reversed(turns)
            if turn.iteration_id == iteration.iteration_id
            and turn.visibility == "product_safe"
            and turn.speaker_type == "owner"
            and turn.reply_to_turn_id is None
            and turn.intent_type != "generate"
        ),
        None,
    )
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
    discussion_group_id = None if latest_owner_turn is None else f"group-{latest_owner_turn.turn_id}"
    participant_by_agent_id = {
        participant.agent_id: participant
        for participant in participants
        if participant.agent_id is not None
    }
    latest_run = next((run for run in reversed(runs) if run.iteration_id == iteration.iteration_id), None)
    if latest_run is not None:
        agent_display_name = (
            participant_by_agent_id.get(latest_run.agent_id).display_name
            if participant_by_agent_id.get(latest_run.agent_id) is not None
            else composer_target.agent_display_name
            or latest_run.role.replace("_", " ").strip().title()
        )
        phase_label = latest_run.phase or latest_run.status.replace("_", " ").strip()
        result_suffix = (
            f" while shaping result {target_result.result_id}"
            if target_result is not None
            else ""
        )
        if latest_run.status in {"running", "queued", "pending"}:
            summary = (
                f"{agent_display_name} is currently {phase_label} for task {latest_run.task_id}{result_suffix}."
                if latest_run.task_id
                else f"{agent_display_name} is currently {phase_label}{result_suffix}."
            )
        elif latest_run.status == "completed":
            summary = (
                f"{agent_display_name} completed {phase_label} for task {latest_run.task_id}"
                f"{' and produced result ' + target_result.result_id if target_result is not None else ''}."
                if latest_run.task_id
                else f"{agent_display_name} completed {phase_label}"
                f"{' and produced result ' + target_result.result_id if target_result is not None else ''}."
            )
        else:
            summary = (
                f"{agent_display_name} ended {phase_label} for task {latest_run.task_id} with status {latest_run.status}."
                if latest_run.task_id
                else f"{agent_display_name} ended {phase_label} with status {latest_run.status}."
            )
        return VideoThreadIterationExecutionSummary(
            summary=summary,
            task_id=latest_run.task_id,
            run_id=latest_run.run_id,
            status=latest_run.status,
            phase=latest_run.phase,
            agent_id=latest_run.agent_id,
            agent_display_name=agent_display_name,
            agent_role=latest_run.role,
            result_id=None if target_result is None else target_result.result_id,
            discussion_group_id=discussion_group_id,
            reply_to_turn_id=None if latest_owner_turn is None else latest_owner_turn.turn_id,
            latest_owner_turn_id=None if latest_owner_turn is None else latest_owner_turn.turn_id,
            latest_agent_turn_id=None if latest_agent_turn is None else latest_agent_turn.turn_id,
            is_active=latest_run.status in {"running", "queued", "pending"},
        )

    agent_id = iteration.responsible_agent_id or composer_target.addressed_agent_id
    agent_role = iteration.responsible_role or composer_target.agent_role
    agent_display_name = composer_target.addressed_display_name or composer_target.agent_display_name
    if agent_display_name is None and agent_role is not None:
        agent_display_name = agent_role.replace("_", " ").strip().title()
    if agent_display_name is not None:
        return VideoThreadIterationExecutionSummary(
            summary=(
                f"{agent_display_name} has not started a tracked task yet, but the iteration is anchored to this agent."
            ),
            agent_id=agent_id,
            agent_display_name=agent_display_name,
            agent_role=agent_role,
            result_id=None if target_result is None else target_result.result_id,
            discussion_group_id=discussion_group_id,
            reply_to_turn_id=None if latest_owner_turn is None else latest_owner_turn.turn_id,
            latest_owner_turn_id=None if latest_owner_turn is None else latest_owner_turn.turn_id,
            latest_agent_turn_id=None if latest_agent_turn is None else latest_agent_turn.turn_id,
        )
    if target_result is not None:
        return VideoThreadIterationExecutionSummary(
            summary=f"This iteration is currently anchored to result {target_result.result_id}.",
            result_id=target_result.result_id,
            discussion_group_id=discussion_group_id,
            reply_to_turn_id=None if latest_owner_turn is None else latest_owner_turn.turn_id,
            latest_owner_turn_id=None if latest_owner_turn is None else latest_owner_turn.turn_id,
            latest_agent_turn_id=None if latest_agent_turn is None else latest_agent_turn.turn_id,
        )
    return VideoThreadIterationExecutionSummary()
