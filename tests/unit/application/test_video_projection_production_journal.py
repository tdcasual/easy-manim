import importlib
import importlib.util

from video_agent.domain.video_thread_models import (
    VideoAgentRun,
    VideoIteration,
    VideoResult,
    VideoThreadParticipant,
)


MODULE_NAME = "video_agent.application.video_projection_production_journal"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


def test_build_production_journal_orders_iteration_run_and_result_entries_with_selected_resources() -> None:
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
            status="active",
        ),
        VideoIteration(
            iteration_id="iter-2",
            thread_id="thread-1",
            goal="Slow the opener",
            requested_action="revise",
            status="active",
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
            output_summary="Refining the title timing.",
        )
    ]
    results = [
        VideoResult(
            result_id="result-1",
            thread_id="thread-1",
            iteration_id="iter-1",
            result_summary="Initial cut",
        ),
        VideoResult(
            result_id="result-2",
            thread_id="thread-1",
            iteration_id="iter-2",
            source_task_id="task-1",
            status="ready",
            result_summary="Selected revised cut",
            video_resource="video-task://task-1/artifacts/final.mp4",
            preview_resources=["video-task://task-1/artifacts/previews/frame-001.png"],
            script_resource="video-task://task-1/artifacts/script.py",
            validation_report_resource="video-task://task-1/artifacts/report.json",
        ),
    ]

    journal = module.build_production_journal(
        participants=participants,
        iterations=iterations,
        runs=runs,
        results=results,
        selected_result_id="result-2",
    )

    assert journal.summary == "5 visible production entries across 2 iteration(s), 1 run(s), and 2 result(s)."
    assert [item.entry_kind for item in journal.entries] == [
        "iteration",
        "iteration",
        "run",
        "result",
        "result",
    ]
    assert journal.entries[0].title == "Generation iteration opened"
    assert journal.entries[1].title == "Revision iteration opened"
    assert journal.entries[2].title == "Repairer is repairing"
    assert journal.entries[2].actor_display_name == "Repairer"
    assert journal.entries[3].title == "Result candidate recorded"
    assert journal.entries[4].title == "Selected result recorded"
    assert journal.entries[4].resource_refs == [
        "video-task://task-1/artifacts/final.mp4",
        "video-task://task-1/artifacts/previews/frame-001.png",
        "video-task://task-1/artifacts/script.py",
        "video-task://task-1/artifacts/report.json",
    ]
