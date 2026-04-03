from pathlib import Path

from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.video_iteration_service import VideoIterationService
from video_agent.application.video_run_binding_service import VideoRunBindingService


def _build_store(tmp_path: Path) -> SQLiteTaskStore:
    database_path = tmp_path / "agent.db"
    SQLiteBootstrapper(database_path).bootstrap()
    return SQLiteTaskStore(database_path)


def test_video_run_binding_service_attaches_and_updates_runs(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    store.upsert_video_thread_json(
        thread_id="thread-1",
        owner_agent_id="owner",
        title="Circle explainer",
        origin_prompt="draw a circle",
    )
    iteration = VideoIterationService(store=store).create_iteration(
        thread_id="thread-1",
        goal="Initial generation",
    )
    service = VideoRunBindingService(store=store)

    run = service.attach_run(
        thread_id="thread-1",
        iteration_id=iteration.iteration_id,
        agent_id="planner-1",
        role="planner",
        task_id="task-1",
    )
    updated = service.mark_run_status(
        run.run_id,
        status="running",
        phase="planning",
        output_summary="Preparing the scene plan.",
    )

    assert run.status == "pending"
    assert updated.status == "running"
    assert updated.phase == "planning"
    assert updated.output_summary == "Preparing the scene plan."
    participants = store.list_video_thread_participants("thread-1")
    assert len(participants) == 1
    assert participants[0].participant_type == "agent"
    assert participants[0].agent_id == "planner-1"
    assert participants[0].role == "planner"
