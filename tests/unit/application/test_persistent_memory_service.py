import pytest

from video_agent.application.persistent_memory_service import (
    PersistentMemoryError,
    PersistentMemoryService,
)
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.session_memory_models import SessionMemorySummary


def test_promote_session_summary_creates_agent_memory_record() -> None:
    created: list[AgentMemoryRecord] = []

    service = PersistentMemoryService(
        create_record=lambda record: created.append(record) or record,
        get_session_summary=lambda session_id: SessionMemorySummary(
            session_id=session_id,
            agent_id="agent-a",
            entries=[],
            lineage_refs=["video-task://task-1/task.json"],
            summary_text="Use a light background.",
            summary_digest="digest-1",
        ),
        memory_id_factory=lambda: "mem-1",
    )

    record = service.promote_session_memory("session-1", agent_id="agent-a")

    assert record.memory_id == "mem-1"
    assert record.agent_id == "agent-a"
    assert record.source_session_id == "session-1"
    assert record.summary_text == "Use a light background."
    assert record.summary_digest == "digest-1"
    assert record.lineage_refs == ["video-task://task-1/task.json"]
    assert record.snapshot["session_id"] == "session-1"
    assert created == [record]


def test_promote_still_succeeds_when_enhancement_is_unavailable() -> None:
    service = PersistentMemoryService(
        create_record=lambda record: record,
        get_session_summary=lambda session_id: SessionMemorySummary(
            session_id=session_id,
            agent_id="agent-a",
            entries=[],
            lineage_refs=["video-task://task-1/task.json"],
            summary_text="Use a light background.",
            summary_digest="digest-1",
        ),
        enhancer=lambda record: {
            "status": "unavailable",
            "code": "agent_memory_enhancement_unavailable",
        },
        memory_id_factory=lambda: "mem-1",
    )

    record = service.promote_session_memory("session-1", agent_id="agent-a")

    assert record.enhancement["status"] == "unavailable"


def test_promote_rejects_empty_session_summary() -> None:
    service = PersistentMemoryService(
        create_record=lambda record: record,
        get_session_summary=lambda session_id: SessionMemorySummary(
            session_id=session_id,
            agent_id="agent-a",
            entries=[],
            lineage_refs=[],
            summary_text="",
            summary_digest=None,
        ),
    )

    with pytest.raises(PersistentMemoryError, match="agent_memory_empty_session"):
        service.promote_session_memory("session-1", agent_id="agent-a")
