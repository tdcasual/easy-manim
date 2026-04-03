from pathlib import Path

from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.video_iteration_service import VideoIterationService


def _build_store(tmp_path: Path) -> SQLiteTaskStore:
    database_path = tmp_path / "agent.db"
    SQLiteBootstrapper(database_path).bootstrap()
    return SQLiteTaskStore(database_path)


def test_video_iteration_service_creates_and_assigns_iteration(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    store.upsert_video_thread_json(
        thread_id="thread-1",
        owner_agent_id="owner",
        title="Circle explainer",
        origin_prompt="draw a circle",
    )
    service = VideoIterationService(store=store)

    iteration = service.create_iteration(
        thread_id="thread-1",
        goal="Refine the opener pacing",
        parent_iteration_id="iter-root",
        requested_action="revise",
        source_result_id="result-1",
    )
    assigned = service.assign_responsibility(
        iteration.iteration_id,
        responsible_role="repairer",
        responsible_agent_id="agent-repairer",
    )

    assert iteration.parent_iteration_id == "iter-root"
    assert iteration.requested_action == "revise"
    assert iteration.source_result_id == "result-1"
    assert assigned.responsible_role == "repairer"
    assert assigned.responsible_agent_id == "agent-repairer"


def test_video_iteration_service_closes_iteration_and_registers_result(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    store.upsert_video_thread_json(
        thread_id="thread-1",
        owner_agent_id="owner",
        title="Circle explainer",
        origin_prompt="draw a circle",
    )
    service = VideoIterationService(store=store)
    iteration = service.create_iteration(thread_id="thread-1", goal="Initial generation")

    result = service.register_result(
        thread_id="thread-1",
        iteration_id=iteration.iteration_id,
        source_task_id="task-1",
        status="ready",
        result_summary="Initial cut",
    )
    closed = service.close_iteration(
        iteration.iteration_id,
        resolution_state="delivered",
        status="completed",
        selected_result_id=result.result_id,
    )

    assert result.status == "ready"
    assert result.result_summary == "Initial cut"
    assert closed.status == "completed"
    assert closed.resolution_state == "delivered"
    assert closed.selected_result_id == result.result_id
