import pytest

from video_agent.application.persistent_memory_service import (
    PersistentMemoryBackendHit,
    PersistentMemoryError,
    PersistentMemoryService,
    build_persistent_memory_enhancer,
)
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.session_memory_models import SessionMemorySummary


class _FakeMemoryBackend:
    def __init__(
        self,
        *,
        promote_payload: dict[str, object] | None = None,
        search_hits: list[PersistentMemoryBackendHit] | None = None,
        search_error: Exception | None = None,
    ) -> None:
        self.promote_payload = promote_payload or {
            "status": "indexed",
            "backend": "memo0",
            "memory_ids": ["remote-mem-1"],
        }
        self.search_hits = list(search_hits or [])
        self.search_error = search_error
        self.deleted_memory_ids: list[str] = []

    def __call__(self, record: AgentMemoryRecord) -> dict[str, object]:
        return dict(self.promote_payload)

    def search(
        self,
        *,
        agent_id: str,
        query: str,
        limit: int,
    ) -> list[PersistentMemoryBackendHit]:
        if self.search_error is not None:
            raise self.search_error
        return list(self.search_hits[:limit])

    def delete(self, record: AgentMemoryRecord) -> None:
        self.deleted_memory_ids.append(record.memory_id)


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


def test_build_persistent_memory_enhancer_returns_unavailable_memo0_backend() -> None:
    enhancer = build_persistent_memory_enhancer(
        backend="memo0",
        enable_embeddings=True,
        embedding_provider="mock-provider",
        embedding_model="mock-model",
    )
    record = AgentMemoryRecord(
        memory_id="mem-1",
        agent_id="agent-a",
        source_session_id="session-1",
        summary_text="Use a light background.",
        summary_digest="digest-1",
    )

    assert enhancer is not None
    payload = enhancer(record)

    assert payload["status"] == "unavailable"
    assert payload["code"] == "agent_memory_enhancement_unavailable"
    assert payload["backend"] == "memo0"


def test_promote_session_summary_records_memo0_index_metadata() -> None:
    service = PersistentMemoryService(
        create_record=lambda record: record,
        get_session_summary=lambda session_id: SessionMemorySummary(
            session_id=session_id,
            agent_id="agent-a",
            entries=[],
            summary_text="Use a light background.",
            summary_digest="digest-1",
        ),
        enhancer=_FakeMemoryBackend(),
        memory_id_factory=lambda: "mem-1",
    )

    record = service.promote_session_memory("session-1", agent_id="agent-a")

    assert record.enhancement["status"] == "indexed"
    assert record.enhancement["backend"] == "memo0"
    assert record.enhancement["memory_ids"] == ["remote-mem-1"]


def test_query_agent_memories_prefers_memo0_backend_results() -> None:
    records = {
        "mem-a": AgentMemoryRecord(
            memory_id="mem-a",
            agent_id="agent-a",
            source_session_id="session-a",
            summary_text="Use smooth transitions.",
            summary_digest="digest-a",
        ),
        "mem-b": AgentMemoryRecord(
            memory_id="mem-b",
            agent_id="agent-a",
            source_session_id="session-b",
            summary_text="Use bold color contrast.",
            summary_digest="digest-b",
        ),
    }
    service = PersistentMemoryService(
        create_record=lambda record: record,
        get_session_summary=lambda session_id: SessionMemorySummary(
            session_id=session_id,
            entries=[],
            summary_text="unused",
        ),
        get_record=lambda memory_id: records.get(memory_id),
        list_records=lambda agent_id, include_disabled=False: list(records.values()),
        enhancer=_FakeMemoryBackend(
            search_hits=[
                PersistentMemoryBackendHit(
                    memory_id="mem-b",
                    score=0.92,
                    match_reasons=["memo0_semantic_search"],
                ),
                PersistentMemoryBackendHit(
                    memory_id="mem-a",
                    score=0.71,
                    match_reasons=["memo0_semantic_search"],
                ),
            ]
        ),
    )

    hits = service.query_agent_memories(
        "agent-a",
        query="high contrast visuals",
        limit=2,
    )

    assert [hit.memory_id for hit in hits] == ["mem-b", "mem-a"]
    assert hits[0].match_reasons == ["memo0_semantic_search"]
    assert hits[0].score == 0.92


def test_query_agent_memories_falls_back_to_local_when_memo0_is_unavailable() -> None:
    service = PersistentMemoryService(
        create_record=lambda record: record,
        get_session_summary=lambda session_id: SessionMemorySummary(
            session_id=session_id,
            entries=[],
            summary_text="unused",
        ),
        list_records=lambda agent_id, include_disabled=False: [
            AgentMemoryRecord(
                memory_id="mem-a",
                agent_id="agent-a",
                source_session_id="session-a",
                summary_text="Dark background with smooth transitions.",
                summary_digest="digest-a",
            ),
            AgentMemoryRecord(
                memory_id="mem-b",
                agent_id="agent-a",
                source_session_id="session-b",
                summary_text="Concise labels and clean spacing.",
                summary_digest="digest-b",
            ),
        ],
        enhancer=_FakeMemoryBackend(search_error=RuntimeError("memo0 unavailable")),
    )

    hits = service.query_agent_memories(
        "agent-a",
        query="dark transitions",
        limit=2,
    )

    assert [hit.memory_id for hit in hits] == ["mem-a"]
    assert "keyword_overlap" in hits[0].match_reasons


def test_disable_agent_memory_propagates_delete_to_memo0_backend() -> None:
    record = AgentMemoryRecord(
        memory_id="mem-1",
        agent_id="agent-a",
        source_session_id="session-a",
        summary_text="Use a light background.",
        summary_digest="digest-1",
        enhancement={"backend": "memo0", "memory_ids": ["remote-mem-1"]},
    )
    records = {"mem-1": record}
    backend = _FakeMemoryBackend()

    def _disable(memory_id: str) -> bool:
        records[memory_id] = records[memory_id].model_copy(update={"status": "disabled"})
        return True

    service = PersistentMemoryService(
        create_record=lambda created: created,
        get_session_summary=lambda session_id: SessionMemorySummary(
            session_id=session_id,
            entries=[],
            summary_text="unused",
        ),
        get_record=lambda memory_id: records.get(memory_id),
        disable_record=_disable,
        enhancer=backend,
    )

    updated = service.disable_agent_memory("mem-1", agent_id="agent-a")

    assert updated.status == "disabled"
    assert backend.deleted_memory_ids == ["mem-1"]
