import pytest

from video_agent.application.errors import AdmissionControlError
from video_agent.config import Settings
from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.server.app import create_app_context
from video_agent.server.mcp_tools import create_video_task_tool, retry_video_task_tool



def test_create_video_task_rejects_when_queue_limit_reached(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path / "data", max_queued_tasks=1)
    context = create_app_context(settings)
    context.task_service.create_video_task(prompt="first")

    with pytest.raises(AdmissionControlError) as exc:
        context.task_service.create_video_task(prompt="second")

    assert exc.value.code == "queue_full"



def test_retry_video_task_rejects_when_attempt_limit_reached(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path / "data", max_attempts_per_root_task=1)
    context = create_app_context(settings)
    created = context.task_service.create_video_task(prompt="first")

    task = context.store.get_task(created.task_id)
    assert task is not None
    task.status = TaskStatus.FAILED
    task.phase = TaskPhase.FAILED
    context.store.update_task(task)

    with pytest.raises(AdmissionControlError) as exc:
        context.task_service.retry_video_task(created.task_id)

    assert exc.value.code == "attempt_limit_reached"



def test_create_video_task_tool_returns_normalized_error(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path / "data", max_queued_tasks=1)
    context = create_app_context(settings)
    context.task_service.create_video_task(prompt="first")

    payload = create_video_task_tool(context, {"prompt": "second"})

    assert payload["error"]["code"] == "queue_full"



def test_retry_video_task_tool_returns_normalized_error(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path / "data", max_attempts_per_root_task=1)
    context = create_app_context(settings)
    created = context.task_service.create_video_task(prompt="first")

    task = context.store.get_task(created.task_id)
    assert task is not None
    task.status = TaskStatus.FAILED
    task.phase = TaskPhase.FAILED
    context.store.update_task(task)

    payload = retry_video_task_tool(context, {"task_id": created.task_id})

    assert payload["error"]["code"] == "attempt_limit_reached"
