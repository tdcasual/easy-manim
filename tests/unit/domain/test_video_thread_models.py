from video_agent.domain.video_thread_models import (
    VideoAgentRun,
    VideoIteration,
    VideoResult,
    VideoThread,
    VideoThreadParticipant,
    VideoTurn,
)


def test_video_thread_defaults_to_active_root() -> None:
    thread = VideoThread(
        thread_id="thread-1",
        owner_agent_id="owner",
        title="Circle explainer",
        origin_prompt="draw a circle",
    )

    assert thread.status == "active"
    assert thread.selected_result_id is None
    assert thread.current_iteration_id is None
    assert thread.archived_at is None


def test_video_iteration_defaults_to_open_status() -> None:
    iteration = VideoIteration(
        iteration_id="iter-1",
        thread_id="thread-1",
        goal="Refine the opener pacing",
    )

    assert iteration.status == "active"
    assert iteration.resolution_state == "open"
    assert iteration.parent_iteration_id is None
    assert iteration.selected_result_id is None


def test_video_turn_defaults_to_product_safe_visibility() -> None:
    turn = VideoTurn(
        turn_id="turn-1",
        thread_id="thread-1",
        iteration_id="iter-1",
        turn_type="owner_request",
        speaker_type="owner",
        title="Please slow down the opening",
    )

    assert turn.visibility == "product_safe"
    assert turn.summary == ""
    assert turn.intent_type is None
    assert turn.reply_to_turn_id is None
    assert turn.related_result_id is None
    assert turn.source_run_id is None


def test_video_result_defaults_to_pending_not_selected() -> None:
    result = VideoResult(
        result_id="result-1",
        thread_id="thread-1",
        iteration_id="iter-1",
    )

    assert result.status == "pending"
    assert result.selected is False
    assert result.result_summary == ""


def test_video_agent_run_defaults_to_pending() -> None:
    run = VideoAgentRun(
        run_id="run-1",
        thread_id="thread-1",
        iteration_id="iter-1",
        agent_id="planner-1",
        role="planner",
    )

    assert run.status == "pending"
    assert run.phase is None
    assert run.output_summary is None


def test_video_thread_participant_defaults_to_active_membership() -> None:
    participant = VideoThreadParticipant(
        thread_id="thread-1",
        participant_id="participant-1",
        participant_type="agent",
        agent_id="reviewer-1",
        role="reviewer",
        display_name="Reviewer",
    )

    assert participant.capabilities == []
    assert participant.left_at is None
