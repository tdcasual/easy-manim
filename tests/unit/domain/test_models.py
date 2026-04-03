from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.domain.models import VideoTask


def test_video_task_defaults() -> None:
    task = VideoTask(prompt="draw a circle")
    assert task.status is TaskStatus.QUEUED
    assert task.phase is TaskPhase.QUEUED
    assert task.attempt_count == 0
    assert task.root_task_id == task.task_id


def test_child_task_keeps_root_and_parent() -> None:
    parent = VideoTask(prompt="draw a circle")
    child = VideoTask.from_revision(parent=parent, feedback="make it blue")
    assert child.parent_task_id == parent.task_id
    assert child.root_task_id == parent.root_task_id


def test_child_task_inherits_display_title_metadata() -> None:
    parent = VideoTask(
        prompt="做一个蓝色圆形开场动画，画面干净简洁",
        display_title="蓝色圆形开场动画",
        title_source="prompt",
    )

    child = VideoTask.from_revision(parent=parent, feedback="把背景改成浅灰色")

    assert child.display_title == "蓝色圆形开场动画"
    assert child.title_source == "prompt"


def test_video_task_can_bind_to_thread_iteration_and_result() -> None:
    task = VideoTask(
        prompt="draw a circle",
        thread_id="thread-1",
        iteration_id="iter-1",
        result_id="result-1",
        execution_kind="initial_generation",
    )

    assert task.thread_id == "thread-1"
    assert task.iteration_id == "iter-1"
    assert task.result_id == "result-1"
    assert task.execution_kind == "initial_generation"
