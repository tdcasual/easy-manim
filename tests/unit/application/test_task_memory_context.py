from video_agent.application.task_memory_context import (
    apply_persistent_memory_context_to_task,
    session_memory_digest_from_task,
    session_memory_summary_from_task,
)
from video_agent.application.persistent_memory_service import PersistentMemoryContext
from video_agent.domain.models import VideoTask


def test_session_memory_helpers_prefer_structured_task_memory_context() -> None:
    task = VideoTask(
        task_id="task-1",
        root_task_id="task-1",
        prompt="draw a circle",
        task_memory_context={
            "session": {
                "session_id": "session-1",
                "summary_text": "Structured session continuity summary.",
                "summary_digest": "digest-structured",
                "entry_count": 1,
            }
        },
        memory_context_summary="Legacy session summary.",
        memory_context_digest="digest-legacy",
    )

    assert session_memory_summary_from_task(task) == "Structured session continuity summary."
    assert session_memory_digest_from_task(task) == "digest-structured"


def test_session_memory_helpers_fall_back_to_legacy_summary_fields() -> None:
    task = VideoTask(
        task_id="task-1",
        root_task_id="task-1",
        prompt="draw a circle",
        memory_context_summary="Legacy session summary.",
        memory_context_digest="digest-legacy",
    )

    assert session_memory_summary_from_task(task) == "Legacy session summary."
    assert session_memory_digest_from_task(task) == "digest-legacy"


def test_apply_persistent_memory_context_to_task_writes_structured_context_and_legacy_mirrors() -> None:
    task = VideoTask(task_id="task-1", root_task_id="task-1", prompt="draw a circle")

    apply_persistent_memory_context_to_task(
        task,
        PersistentMemoryContext(
            memory_ids=["mem-a"],
            summary_text="Prefer high-contrast diagrams.",
            summary_digest="digest-a",
        ),
    )

    assert task.task_memory_context["persistent"]["memory_ids"] == ["mem-a"]
    assert task.task_memory_context["persistent"]["summary_text"] == "Prefer high-contrast diagrams."
    assert task.task_memory_context["persistent"]["items"][0]["memory_id"] == "mem-a"
    assert task.selected_memory_ids == ["mem-a"]
    assert task.persistent_memory_context_summary == "Prefer high-contrast diagrams."
    assert task.persistent_memory_context_digest == "digest-a"


def test_apply_persistent_memory_context_to_task_clears_existing_persistent_context_when_empty() -> None:
    task = VideoTask(
        task_id="task-1",
        root_task_id="task-1",
        prompt="draw a circle",
        task_memory_context={
            "persistent": {
                "memory_ids": ["legacy"],
                "summary_text": "Legacy summary.",
                "summary_digest": "legacy-digest",
                "items": [{"memory_id": "legacy", "summary_text": "Legacy summary."}],
            }
        },
        selected_memory_ids=["legacy"],
        persistent_memory_context_summary="Legacy summary.",
        persistent_memory_context_digest="legacy-digest",
    )

    apply_persistent_memory_context_to_task(task, PersistentMemoryContext())

    assert task.task_memory_context["persistent"]["memory_ids"] == []
    assert task.task_memory_context["persistent"]["items"] == []
    assert task.selected_memory_ids == []
    assert task.persistent_memory_context_summary is None
    assert task.persistent_memory_context_digest is None
