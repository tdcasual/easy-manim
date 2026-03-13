from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.server.app import create_app_context
from video_agent.server.mcp_tools import retry_video_task_tool



def test_retry_video_task_creates_new_child_from_failed_parent(temp_settings) -> None:
    app = create_app_context(temp_settings)
    created = app.task_service.create_video_task(prompt="draw a circle")

    task = app.store.get_task(created.task_id)
    assert task is not None
    task.status = TaskStatus.FAILED
    task.phase = TaskPhase.FAILED
    app.store.update_task(task)

    retried = app.task_service.retry_video_task(created.task_id)
    snapshot = app.task_service.get_video_task(retried.task_id)

    assert snapshot.parent_task_id == created.task_id
    assert snapshot.status == "queued"



def test_retry_video_task_tool_returns_new_child_task(temp_settings) -> None:
    app = create_app_context(temp_settings)
    created = app.task_service.create_video_task(prompt="draw a circle")

    task = app.store.get_task(created.task_id)
    assert task is not None
    task.status = TaskStatus.FAILED
    task.phase = TaskPhase.FAILED
    app.store.update_task(task)

    payload = retry_video_task_tool(app, {"task_id": created.task_id})
    snapshot = app.task_service.get_video_task(payload["task_id"])

    assert snapshot.parent_task_id == created.task_id


def test_auto_repair_task_creates_new_child_from_failed_parent(temp_settings) -> None:
    app = create_app_context(temp_settings)
    created = app.task_service.create_video_task(prompt="draw a circle")

    task = app.store.get_task(created.task_id)
    assert task is not None
    task.status = TaskStatus.FAILED
    task.phase = TaskPhase.FAILED
    app.store.update_task(task)

    repaired = app.task_service.create_auto_repair_task(created.task_id, feedback="Fix render_failed and keep working parts")
    snapshot = app.task_service.get_video_task(repaired.task_id)
    child_task = app.store.get_task(repaired.task_id)

    assert snapshot.parent_task_id == created.task_id
    assert snapshot.status == "queued"
    assert child_task is not None
    assert child_task.feedback == "Fix render_failed and keep working parts"
