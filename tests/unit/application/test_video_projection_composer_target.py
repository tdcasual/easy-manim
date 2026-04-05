import importlib
import importlib.util

from video_agent.domain.video_thread_models import (
    VideoAgentRun,
    VideoIteration,
    VideoResult,
    VideoThreadParticipant,
    VideoTurn,
)


MODULE_NAME = "video_agent.application.video_projection_composer_target"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


def test_build_composer_target_prefers_iteration_selected_result_and_responsible_agent() -> None:
    module = _load_module()
    iteration = VideoIteration(
        iteration_id="iter-2",
        thread_id="thread-1",
        goal="Refine the opener pacing",
        responsible_role="repairer",
        responsible_agent_id="repairer-1",
        selected_result_id="result-2",
    )
    participants = [
        VideoThreadParticipant(
            thread_id="thread-1",
            participant_id="owner",
            participant_type="owner",
            agent_id="owner",
            role="owner",
            display_name="Owner",
        ),
        VideoThreadParticipant(
            thread_id="thread-1",
            participant_id="repairer-1",
            participant_type="agent",
            agent_id="repairer-1",
            role="repairer",
            display_name="Repairer",
        ),
    ]
    results = [
        VideoResult(
            result_id="result-1",
            thread_id="thread-1",
            iteration_id="iter-2",
            result_summary="Earlier cut",
        ),
        VideoResult(
            result_id="result-2",
            thread_id="thread-1",
            iteration_id="iter-2",
            result_summary="Selected cut",
            selected=True,
        ),
    ]

    target = module.build_composer_target(
        iteration=iteration,
        participants=participants,
        runs=[],
        results=results,
        turns=[],
    )

    assert target.iteration_id == "iter-2"
    assert target.result_id == "result-2"
    assert target.addressed_participant_id == "repairer-1"
    assert target.addressed_agent_id == "repairer-1"
    assert target.addressed_display_name == "Repairer"
    assert target.agent_role == "repairer"
    assert target.agent_display_name == "Repairer"
    assert target.summary == (
        "New messages will attach to iter-2, stay anchored to result-2, and hand off to Repairer."
    )


def test_resolve_composer_participant_falls_back_from_addressed_turn_to_runs_to_agent_turns() -> None:
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
            participant_id="reviewer-1",
            participant_type="agent",
            agent_id="reviewer-1",
            role="reviewer",
            display_name="Reviewer",
        ),
    ]
    iteration = VideoIteration(
        iteration_id="iter-2",
        thread_id="thread-1",
        goal="Refine the opener pacing",
    )

    addressed_turn = VideoTurn(
        turn_id="turn-1",
        thread_id="thread-1",
        iteration_id="iter-2",
        turn_type="owner_request",
        speaker_type="owner",
        title="Please revise",
        addressed_participant_id="reviewer-1",
    )
    run = VideoAgentRun(
        run_id="run-1",
        thread_id="thread-1",
        iteration_id="iter-2",
        agent_id="repairer-1",
        role="repairer",
    )
    agent_turn = VideoTurn(
        turn_id="turn-2",
        thread_id="thread-1",
        iteration_id="iter-2",
        turn_type="agent_reply",
        speaker_type="agent",
        speaker_agent_id="repairer-1",
        speaker_role="repairer",
        title="Updated pacing",
    )

    addressed = module.resolve_composer_participant(
        iteration=iteration,
        participants=participants,
        runs=[run],
        turns=[addressed_turn, agent_turn],
    )
    from_runs = module.resolve_composer_participant(
        iteration=iteration,
        participants=participants,
        runs=[run],
        turns=[agent_turn.model_copy(update={"iteration_id": "iter-1"})],
    )
    from_agent_turns = module.resolve_composer_participant(
        iteration=iteration,
        participants=participants,
        runs=[],
        turns=[agent_turn],
    )

    assert addressed is not None
    assert addressed.participant_id == "reviewer-1"
    assert from_runs is not None
    assert from_runs.participant_id == "repairer-1"
    assert from_agent_turns is not None
    assert from_agent_turns.participant_id == "repairer-1"


def test_target_result_for_iteration_prefers_selected_then_explicit_then_latest_iteration_result() -> None:
    module = _load_module()
    iteration = VideoIteration(
        iteration_id="iter-2",
        thread_id="thread-1",
        goal="Refine the opener pacing",
        selected_result_id="result-2",
    )
    results = [
        VideoResult(
            result_id="result-1",
            thread_id="thread-1",
            iteration_id="iter-2",
            result_summary="First cut",
        ),
        VideoResult(
            result_id="result-2",
            thread_id="thread-1",
            iteration_id="iter-2",
            result_summary="Chosen cut",
        ),
        VideoResult(
            result_id="result-3",
            thread_id="thread-1",
            iteration_id="iter-2",
            result_summary="Latest cut",
        ),
    ]

    explicit = module.target_result_for_iteration(iteration=iteration, results=results)
    selected = module.target_result_for_iteration(
        iteration=iteration,
        results=[*results, results[1].model_copy(update={"selected": True})],
    )
    latest = module.target_result_for_iteration(
        iteration=iteration.model_copy(update={"selected_result_id": None}),
        results=results,
    )

    assert explicit is not None
    assert explicit.result_id == "result-2"
    assert selected is not None
    assert selected.result_id == "result-2"
    assert latest is not None
    assert latest.result_id == "result-3"
