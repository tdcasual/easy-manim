import importlib
import importlib.util

from video_agent.domain.video_thread_models import (
    VideoAgentRun,
    VideoIteration,
    VideoResult,
    VideoThreadComposer,
    VideoThreadComposerTarget,
    VideoThreadIterationDetailSummary,
    VideoThreadIterationExecutionSummary,
    VideoThreadLatestExplanation,
    VideoThreadParticipant,
    VideoThreadResponsibility,
    VideoTurn,
)


MODULE_NAME = "video_agent.application.video_projection_collaboration_runtime"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


def test_collaboration_runtime_builds_discussion_groups_and_runtime_for_active_iteration() -> None:
    module = _load_module()
    participants = [
        VideoThreadParticipant(
            thread_id="thread-1",
            participant_id="repairer-1",
            participant_type="agent",
            agent_id="repairer-1",
            role="repairer",
            display_name="Repairer",
        ),
        VideoThreadParticipant(
            thread_id="thread-1",
            participant_id="planner-1",
            participant_type="agent",
            agent_id="planner-1",
            role="planner",
            display_name="Planner",
        ),
    ]
    current_iteration = VideoIteration(
        iteration_id="iter-2",
        thread_id="thread-1",
        goal="Refine the opener pacing",
    )
    current_result = VideoResult(
        result_id="result-2",
        thread_id="thread-1",
        iteration_id="iter-2",
        result_summary="Slower opener with more deliberate title motion.",
    )
    turns = [
        VideoTurn(
            turn_id="turn-owner",
            thread_id="thread-1",
            iteration_id="iter-2",
            turn_type="owner_request",
            intent_type="request_explanation",
            speaker_type="owner",
            title="Why this pacing?",
            summary="Explain the slower opener.",
            related_result_id=current_result.result_id,
        ),
        VideoTurn(
            turn_id="turn-agent",
            thread_id="thread-1",
            iteration_id="iter-2",
            turn_type="agent_reply",
            intent_type="request_explanation",
            speaker_type="agent",
            speaker_agent_id="planner-1",
            speaker_role="planner",
            title="Why the opener changed",
            summary="The slower opening gives the title card room to land.",
            reply_to_turn_id="turn-owner",
            related_result_id=current_result.result_id,
        ),
    ]
    composer = VideoThreadComposer(
        target=VideoThreadComposerTarget(
            iteration_id="iter-2",
            result_id=current_result.result_id,
            addressed_participant_id="repairer-1",
            addressed_agent_id="repairer-1",
            addressed_display_name="Repairer",
            agent_role="repairer",
            agent_display_name="Repairer",
        )
    )
    iteration_detail = VideoThreadIterationDetailSummary(
        selected_iteration_id="iter-2",
        execution_summary=VideoThreadIterationExecutionSummary(
            discussion_group_id="group-turn-owner",
            reply_to_turn_id="turn-owner",
            latest_owner_turn_id="turn-owner",
            latest_agent_turn_id="turn-agent",
            summary="Repairer is repairing the current cut.",
        ),
    )
    latest_explanation = VideoThreadLatestExplanation(
        turn_id="turn-agent",
        summary="The slower opening gives the title card room to land.",
        speaker_display_name="Planner",
        speaker_role="planner",
    )

    discussion_groups = module.build_discussion_groups(participants=participants, turns=turns)
    runtime = module.build_discussion_runtime(
        current_iteration=current_iteration,
        current_result=current_result,
        discussion_groups=discussion_groups,
        composer=composer,
        iteration_detail=iteration_detail,
        latest_explanation=latest_explanation,
    )

    assert discussion_groups.groups[0].status == "answered"
    assert discussion_groups.groups[0].replies[0].speaker_display_name == "Planner"
    assert runtime.active_discussion_group_id == "group-turn-owner"
    assert runtime.addressed_display_name == "Repairer"
    assert runtime.latest_agent_turn_id == "turn-agent"
    assert runtime.continuity_scope == "iteration"


def test_collaboration_runtime_builds_participant_runtime_with_expected_responder_and_recent_contributors() -> None:
    module = _load_module()
    participants = [
        VideoThreadParticipant(
            thread_id="thread-1",
            participant_id="repairer-1",
            participant_type="agent",
            agent_id="repairer-1",
            role="repairer",
            display_name="Repairer",
        ),
        VideoThreadParticipant(
            thread_id="thread-1",
            participant_id="planner-1",
            participant_type="agent",
            agent_id="planner-1",
            role="planner",
            display_name="Planner",
        ),
    ]
    current_iteration = VideoIteration(
        iteration_id="iter-2",
        thread_id="thread-1",
        goal="Refine the opener pacing",
    )
    turns = [
        VideoTurn(
            turn_id="turn-agent",
            thread_id="thread-1",
            iteration_id="iter-2",
            turn_type="agent_reply",
            speaker_type="agent",
            speaker_agent_id="planner-1",
            speaker_role="planner",
            title="Why the opener changed",
            summary="The slower opening gives the title card room to land.",
        )
    ]
    runs = [
        VideoAgentRun(
            run_id="run-1",
            thread_id="thread-1",
            iteration_id="iter-2",
            task_id="task-1",
            agent_id="repairer-1",
            role="repairer",
            status="running",
            output_summary="Refining the title motion timing.",
        )
    ]
    composer = VideoThreadComposer(
        target=VideoThreadComposerTarget(
            iteration_id="iter-2",
            addressed_participant_id="repairer-1",
            addressed_agent_id="repairer-1",
            addressed_display_name="Repairer",
            agent_role="repairer",
            agent_display_name="Repairer",
        )
    )
    responsibility = VideoThreadResponsibility(
        owner_action_required="review_latest_result",
        expected_agent_role="repairer",
        expected_agent_id="repairer-1",
    )

    runtime = module.build_participant_runtime(
        current_iteration=current_iteration,
        participants=participants,
        turns=turns,
        runs=runs,
        composer=composer,
        responsibility=responsibility,
    )

    assert runtime.expected_display_name == "Repairer"
    assert runtime.continuity_mode == "keep_current_participant"
    assert runtime.follow_up_target_locked is True
    assert [item.display_name for item in runtime.recent_contributors] == [
        "Repairer",
        "Planner",
    ]
