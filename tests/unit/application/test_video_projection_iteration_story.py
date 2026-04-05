import importlib
import importlib.util

from video_agent.domain.video_thread_models import (
    VideoAgentRun,
    VideoIteration,
    VideoResult,
    VideoThreadLatestExplanation,
    VideoThreadParticipant,
    VideoTurn,
)


MODULE_NAME = "video_agent.application.video_projection_iteration_story"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


def test_build_rationale_snapshots_marks_current_selection_and_archives_previous_owner_goal() -> None:
    module = _load_module()
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
            participant_id="reviewer-1",
            participant_type="agent",
            agent_id="reviewer-1",
            role="reviewer",
            display_name="Reviewer",
        ),
    ]
    iterations = [
        VideoIteration(
            iteration_id="iter-1",
            thread_id="thread-1",
            goal="Keep the opener brisk",
        ),
        VideoIteration(
            iteration_id="iter-2",
            thread_id="thread-1",
            parent_iteration_id="iter-1",
            goal="Make the title entrance more deliberate",
            responsible_role="reviewer",
            responsible_agent_id="reviewer-1",
            selected_result_id="result-2",
        ),
    ]
    results = [
        VideoResult(
            result_id="result-1",
            thread_id="thread-1",
            iteration_id="iter-1",
            result_summary="Fast opener cut",
        ),
        VideoResult(
            result_id="result-2",
            thread_id="thread-1",
            iteration_id="iter-2",
            result_summary="Deliberate title cut",
        ),
    ]
    turns = [
        VideoTurn(
            turn_id="turn-owner-1",
            thread_id="thread-1",
            iteration_id="iter-1",
            turn_type="owner_request",
            speaker_type="owner",
            title="Original direction",
            summary="Keep the opener brisk.",
        ),
        VideoTurn(
            turn_id="turn-owner-2",
            thread_id="thread-1",
            iteration_id="iter-2",
            turn_type="owner_request",
            speaker_type="owner",
            title="Slow the opener",
            summary="Give the title more room.",
            addressed_agent_id="reviewer-1",
        ),
    ]
    runs = [
        VideoAgentRun(
            run_id="run-2",
            thread_id="thread-1",
            iteration_id="iter-2",
            agent_id="reviewer-1",
            role="reviewer",
            status="completed",
        )
    ]

    snapshots = module.build_rationale_snapshots(
        participants=participants,
        iterations=iterations,
        results=results,
        turns=turns,
        runs=runs,
        current_iteration_id="iter-2",
        current_result_selection_reason="The title lands more clearly in this revision.",
    )

    assert snapshots.current_iteration_id == "iter-2"
    assert [item.snapshot_kind for item in snapshots.items] == [
        "owner_goal",
        "selection_rationale",
    ]
    assert snapshots.items[0].status == "archived"
    assert snapshots.items[0].summary == "Keep the opener brisk."
    assert snapshots.items[1].status == "current"
    assert snapshots.items[1].title == "Why the current revision is selected"
    assert snapshots.items[1].summary == "The title lands more clearly in this revision."
    assert snapshots.items[1].source_result_id == "result-2"
    assert snapshots.items[1].actor_display_name == "Reviewer"
    assert snapshots.items[1].actor_role == "reviewer"


def test_build_iteration_compare_reports_changed_participant_continuity() -> None:
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
    previous_iteration = VideoIteration(
        iteration_id="iter-1",
        thread_id="thread-1",
        goal="Keep the opener brisk",
    )
    current_iteration = VideoIteration(
        iteration_id="iter-2",
        thread_id="thread-1",
        parent_iteration_id="iter-1",
        goal="Make the title entrance more deliberate",
        responsible_role="reviewer",
        responsible_agent_id="reviewer-1",
        selected_result_id="result-2",
    )
    results = [
        VideoResult(
            result_id="result-1",
            thread_id="thread-1",
            iteration_id="iter-1",
            result_summary="Fast opener cut",
            selected=True,
        ),
        VideoResult(
            result_id="result-2",
            thread_id="thread-1",
            iteration_id="iter-2",
            result_summary="Deliberate title cut",
        ),
    ]
    turns = [
        VideoTurn(
            turn_id="turn-owner-1",
            thread_id="thread-1",
            iteration_id="iter-1",
            turn_type="owner_request",
            speaker_type="owner",
            title="Keep it brisk",
            summary="Keep the opener brisk.",
        )
    ]
    runs = [
        VideoAgentRun(
            run_id="run-1",
            thread_id="thread-1",
            iteration_id="iter-1",
            agent_id="repairer-1",
            role="repairer",
            status="completed",
        ),
        VideoAgentRun(
            run_id="run-2",
            thread_id="thread-1",
            iteration_id="iter-2",
            agent_id="reviewer-1",
            role="reviewer",
            status="running",
        ),
    ]

    compare = module.build_iteration_compare(
        participants=participants,
        iterations=[previous_iteration, current_iteration],
        results=results,
        turns=turns,
        runs=runs,
        current_iteration=current_iteration,
        current_result=results[1],
        current_result_selection_reason="The title lands more clearly in this revision.",
        latest_explanation=VideoThreadLatestExplanation(summary="Use more space before the animation starts."),
    )

    assert compare.previous_iteration_id == "iter-1"
    assert compare.current_iteration_id == "iter-2"
    assert compare.previous_result_id == "result-1"
    assert compare.current_result_id == "result-2"
    assert compare.change_summary == "Deliberate title cut"
    assert "Keep the opener brisk." in compare.rationale_shift_summary
    assert "Make the title entrance more deliberate" in compare.rationale_shift_summary
    assert compare.continuity_status == "changed"
    assert compare.continuity_summary == (
        "Participant continuity changed from Repairer to Reviewer between the compared iterations."
    )
