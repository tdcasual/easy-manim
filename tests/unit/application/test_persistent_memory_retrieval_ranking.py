from datetime import datetime, timezone

from video_agent.application.persistent_memory_service import PersistentMemoryService
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.session_memory_models import SessionMemorySummary


def _record(
    memory_id: str,
    summary_text: str,
    *,
    created_at: datetime,
) -> AgentMemoryRecord:
    return AgentMemoryRecord(
        memory_id=memory_id,
        agent_id="agent-a",
        source_session_id=f"session-{memory_id}",
        summary_text=summary_text,
        summary_digest=f"digest-{memory_id}",
        created_at=created_at,
    )


def test_query_agent_memories_prefers_phrase_and_keyword_overlap() -> None:
    service = PersistentMemoryService(
        create_record=lambda record: record,
        get_session_summary=lambda session_id: SessionMemorySummary(
            session_id=session_id,
            entries=[],
            summary_text="unused",
        ),
        list_records=lambda agent_id, include_disabled=False: [
            _record(
                "mem-a",
                "Dark background smooth transitions for title cards.",
                created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
            ),
            _record(
                "mem-b",
                "Dark contrast guidance for subtitles.",
                created_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
            ),
        ],
    )

    hits = service.query_agent_memories(
        "agent-a",
        query="dark background smooth transitions",
        limit=2,
    )

    assert [hit.memory_id for hit in hits] == ["mem-a", "mem-b"]
    assert "phrase_match" in hits[0].match_reasons
    assert "keyword_overlap" in hits[0].match_reasons
    assert hits[0].matched_terms == ["background", "dark", "smooth", "transitions"]


def test_query_agent_memories_uses_created_at_for_stable_tie_breaks() -> None:
    service = PersistentMemoryService(
        create_record=lambda record: record,
        get_session_summary=lambda session_id: SessionMemorySummary(
            session_id=session_id,
            entries=[],
            summary_text="unused",
        ),
        list_records=lambda agent_id, include_disabled=False: [
            _record(
                "mem-older",
                "Dark background guidance.",
                created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
            ),
            _record(
                "mem-newer",
                "Dark background guidance.",
                created_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
            ),
        ],
    )

    hits = service.query_agent_memories(
        "agent-a",
        query="dark background",
        limit=2,
    )

    assert [hit.memory_id for hit in hits] == ["mem-older", "mem-newer"]
