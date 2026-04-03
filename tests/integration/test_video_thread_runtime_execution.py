from pathlib import Path

from video_agent.config import Settings
from video_agent.server.app import create_app_context
from tests.support import bootstrapped_settings


def _build_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            run_embedded_worker=False,
        )
    )


def test_create_thread_creates_initial_execution_task_bound_to_root_iteration(tmp_path: Path) -> None:
    app_context = create_app_context(_build_settings(tmp_path))

    outcome = app_context.video_thread_service.create_thread(
        owner_agent_id="owner",
        title="Circle explainer",
        prompt="draw a circle with a bold title card",
    )

    assert outcome.created_task is not None
    task = app_context.store.get_task(outcome.created_task.task_id)

    assert task is not None
    assert task.thread_id == outcome.thread.thread_id
    assert task.iteration_id == outcome.iteration.iteration_id
    assert task.execution_kind == "initial_generation"
    assert task.parent_task_id is None


def test_request_revision_creates_new_iteration_and_child_task(tmp_path: Path) -> None:
    app_context = create_app_context(_build_settings(tmp_path))
    created = app_context.video_thread_service.create_thread(
        owner_agent_id="owner",
        title="Circle explainer",
        prompt="draw a circle with a bold title card",
    )

    outcome = app_context.video_thread_service.request_revision(
        thread_id=created.thread.thread_id,
        base_task_id=created.created_task.task_id if created.created_task is not None else "",
        summary="Keep the slower opening, but make the title entrance more deliberate.",
        preserve_working_parts=True,
    )

    assert outcome.created_task is not None
    child_task = app_context.store.get_task(outcome.created_task.task_id)

    assert child_task is not None
    assert outcome.iteration.parent_iteration_id == created.iteration.iteration_id
    assert child_task.parent_task_id == created.created_task.task_id
    assert child_task.thread_id == created.thread.thread_id
    assert child_task.iteration_id == outcome.iteration.iteration_id
    assert child_task.execution_kind == "revision"


def test_revision_runtime_lifecycle_projects_targeted_thread_run(tmp_path: Path) -> None:
    app_context = create_app_context(_build_settings(tmp_path))
    created = app_context.video_thread_service.create_thread(
        owner_agent_id="owner",
        title="Circle explainer",
        prompt="draw a circle with a bold title card",
    )
    app_context.video_thread_service.upsert_participant(
        thread_id=created.thread.thread_id,
        participant_id="repairer-1",
        participant_type="agent",
        agent_id="repairer-1",
        role="repairer",
        display_name="Repairer",
    )
    app_context.video_iteration_service.assign_responsibility(
        created.iteration.iteration_id,
        responsible_role="repairer",
        responsible_agent_id="repairer-1",
    )
    origin_result = app_context.video_iteration_service.register_result(
        thread_id=created.thread.thread_id,
        iteration_id=created.iteration.iteration_id,
        source_task_id=created.created_task.task_id if created.created_task is not None else "task-origin",
        status="ready",
        result_summary="Initial cut with a brisk opener.",
    )
    app_context.video_thread_service.select_result(created.thread.thread_id, origin_result.result_id)

    outcome = app_context.video_thread_service.request_revision(
        thread_id=created.thread.thread_id,
        base_iteration_id=created.iteration.iteration_id,
        summary="Keep the geometry but let Repairer soften the title entrance.",
        preserve_working_parts=True,
    )

    assert outcome.created_task is not None
    child_task = app_context.store.get_task(outcome.created_task.task_id)
    assert child_task is not None
    assert app_context.store.list_video_agent_runs(created.thread.thread_id) == []

    app_context.delivery_case_service.mark_planner_running(task=child_task)
    running_runs = app_context.store.list_video_agent_runs(created.thread.thread_id)

    assert len(running_runs) == 1
    running_run = running_runs[0]
    assert running_run.task_id == child_task.task_id
    assert running_run.iteration_id == outcome.iteration.iteration_id
    assert running_run.agent_id == "repairer-1"
    assert running_run.role == "repairer"
    assert running_run.status == "running"
    assert running_run.phase == "scene_planning"
    assert running_run.output_summary == "Scene planning running"

    app_context.delivery_case_service.record_generator_run(
        task=child_task,
        status="completed",
        summary="Generation and render completed",
        phase="rendering",
    )
    completed_runs = app_context.store.list_video_agent_runs(created.thread.thread_id)

    assert len(completed_runs) == 1
    assert completed_runs[0].run_id == running_run.run_id
    assert completed_runs[0].status == "completed"
    assert completed_runs[0].phase == "rendering"
    assert completed_runs[0].output_summary == "Generation and render completed"
