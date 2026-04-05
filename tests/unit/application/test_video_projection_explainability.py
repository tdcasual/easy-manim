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


MODULE_NAME = "video_agent.application.video_projection_explainability"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


def test_explainability_builds_latest_explanation_and_decision_notes() -> None:
    module = _load_module()
    participants = [
        VideoThreadParticipant(
            thread_id="thread-1",
            participant_id="planner-1",
            participant_type="agent",
            agent_id="planner-1",
            role="planner",
            display_name="Planner",
        )
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
            turn_id="turn-agent",
            thread_id="thread-1",
            iteration_id="iter-2",
            turn_type="agent_explanation",
            intent_type="request_explanation",
            speaker_type="agent",
            speaker_agent_id="planner-1",
            speaker_role="planner",
            title="Why the opener changed",
            summary="The slower opening gives the title card room to land.",
            related_result_id=current_result.result_id,
        )
    ]

    latest_explanation = module.build_latest_explanation(
        participants=participants,
        current_iteration=current_iteration,
        turns=turns,
        runs=[],
    )
    decision_notes = module.build_decision_notes(
        current_iteration=current_iteration,
        current_result=current_result,
        current_result_selection_reason="This is the latest selected revision for the active iteration.",
        latest_explanation=latest_explanation,
    )

    assert latest_explanation.turn_id == "turn-agent"
    assert latest_explanation.speaker_display_name == "Planner"
    assert [item.note_kind for item in decision_notes.items] == [
        "selection_rationale",
        "agent_explanation",
        "iteration_goal",
    ]
    assert decision_notes.items[1].source_turn_id == "turn-agent"


def test_explainability_builds_artifact_lineage_and_authorship() -> None:
    module = _load_module()
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
    iterations = [
        VideoIteration(
            iteration_id="iter-1",
            thread_id="thread-1",
            goal="Create the first cut",
            requested_action="generate",
        ),
        VideoIteration(
            iteration_id="iter-2",
            thread_id="thread-1",
            parent_iteration_id="iter-1",
            goal="Refine the opener pacing",
            requested_action="revise",
            source_result_id="result-1",
            responsible_role="repairer",
            responsible_agent_id="repairer-1",
        ),
    ]
    results = [
        VideoResult(
            result_id="result-1",
            thread_id="thread-1",
            iteration_id="iter-1",
            result_summary="Initial cut with a brisk opener.",
        ),
        VideoResult(
            result_id="result-2",
            thread_id="thread-1",
            iteration_id="iter-2",
            result_summary="Slower opener with more deliberate title motion.",
        ),
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
            related_result_id="result-2",
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
    latest_explanation = VideoThreadLatestExplanation(
        summary="The opener now has room to breathe.",
        speaker_display_name="Repairer",
        speaker_role="repairer",
    )

    lineage = module.build_artifact_lineage(
        participants=participants,
        iterations=iterations,
        results=results,
        turns=turns,
        runs=runs,
        selected_result_id="result-2",
        current_iteration_id="iter-2",
        current_result_selection_reason="This is the latest selected revision for the active iteration.",
        latest_explanation=latest_explanation,
    )
    authorship = module.build_authorship(
        participants=participants,
        current_iteration=iterations[-1],
        current_result=results[-1],
        turns=turns,
        runs=runs,
    )

    assert [item.status for item in lineage.items] == ["origin", "selected"]
    assert lineage.items[1].trigger_label == "Owner requested revision"
    assert lineage.items[1].actor_display_name == "Repairer"
    assert authorship.primary_agent_display_name == "Repairer"
    assert authorship.primary_agent_role == "repairer"
    assert authorship.source_run_id == "run-1"
