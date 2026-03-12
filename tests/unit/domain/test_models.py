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
