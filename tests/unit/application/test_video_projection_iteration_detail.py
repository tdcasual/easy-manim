import importlib
import importlib.util

from video_agent.domain.video_thread_models import (
    VideoAgentRun,
    VideoIteration,
    VideoResult,
    VideoThreadParticipant,
    VideoTurn,
)


MODULE_NAME = "video_agent.application.video_projection_iteration_detail"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


def test_iteration_detail_module_builds_execution_summary_and_detail_for_running_run() -> None:
    module = _load_module()
    iteration = VideoIteration(
        iteration_id="iter-2",
        thread_id="thread-1",
        goal="Refine the opener pacing",
        requested_action="revise",
        responsible_role="repairer",
        responsible_agent_id="repairer-1",
    )
    participants = [
        VideoThreadParticipant(
            thread_id="thread-1",
            participant_id="repairer-1",
            participant_type="agent",
            agent_id="repairer-1",
            role="repairer",
            display_name="Repairer",
        )
    ]
    turns = [
        VideoTurn(
            turn_id="turn-owner",
            thread_id="thread-1",
            iteration_id="iter-2",
            turn_type="owner_request",
            intent_type="request_revision",
            speaker_type="owner",
            title="Slow the opener",
            summary="Make the opener more deliberate.",
            addressed_participant_id="repairer-1",
            addressed_agent_id="repairer-1",
        ),
        VideoTurn(
            turn_id="turn-agent",
            thread_id="thread-1",
            iteration_id="iter-2",
            turn_type="agent_reply",
            intent_type="request_revision",
            speaker_type="agent",
            speaker_agent_id="repairer-1",
            speaker_role="repairer",
            title="Working on it",
            summary="Adjusting the title motion.",
            reply_to_turn_id="turn-owner",
        ),
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
            phase="repairing",
            output_summary="Refining the title motion timing.",
        )
    ]
    results = [
        VideoResult(
            result_id="result-2",
            thread_id="thread-1",
            iteration_id="iter-2",
            result_summary="Slower opener with more deliberate title motion.",
        )
    ]

    detail_summary = module.build_iteration_detail_summary(
        thread_id="thread-1",
        selected_iteration=iteration,
        participants=participants,
        turns=turns,
        runs=runs,
        results=results,
    )
    detail = module.build_iteration_detail(
        thread_id="thread-1",
        iteration=iteration,
        participants=participants,
        turns=turns,
        runs=runs,
        results=results,
    )

    assert detail_summary.selected_iteration_id == "iter-2"
    assert detail_summary.execution_summary.summary == (
        "Repairer is currently repairing for task task-1 while shaping result result-2."
    )
    assert detail_summary.execution_summary.discussion_group_id == "group-turn-owner"
    assert detail_summary.execution_summary.latest_agent_turn_id == "turn-agent"
    assert detail.composer_target.addressed_display_name == "Repairer"
    assert detail.turns[0].addressed_display_name == "Repairer"
    assert detail.turns[1].speaker_display_name == "Repairer"
    assert detail.runs[0].agent_display_name == "Repairer"


def test_iteration_detail_module_falls_back_to_responsible_agent_when_no_run_exists() -> None:
    module = _load_module()
    iteration = VideoIteration(
        iteration_id="iter-3",
        thread_id="thread-1",
        goal="Polish the ending",
        requested_action="revise",
        responsible_role="reviewer",
        responsible_agent_id="reviewer-1",
    )
    participants = [
        VideoThreadParticipant(
            thread_id="thread-1",
            participant_id="reviewer-1",
            participant_type="agent",
            agent_id="reviewer-1",
            role="reviewer",
            display_name="Reviewer",
        )
    ]

    execution_summary = module.build_iteration_execution_summary(
        iteration=iteration,
        participants=participants,
        runs=[],
        results=[],
        turns=[],
    )

    assert execution_summary.agent_id == "reviewer-1"
    assert execution_summary.agent_display_name == "Reviewer"
    assert execution_summary.agent_role == "reviewer"
    assert (
        execution_summary.summary
        == "Reviewer has not started a tracked task yet, but the iteration is anchored to this agent."
    )
