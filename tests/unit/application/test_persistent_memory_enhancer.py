from video_agent.application.persistent_memory_enhancer import normalize_retrieval_metadata
from video_agent.domain.agent_memory_models import AgentMemoryRecord


def test_normalize_retrieval_metadata_produces_stable_payload() -> None:
    record = AgentMemoryRecord(
        memory_id="mem-1",
        agent_id="agent-a",
        source_session_id="session-1",
        summary_text="Use dark backgrounds, smooth transitions, and concise labels.",
        summary_digest="digest-1",
    )

    payload = normalize_retrieval_metadata(record)

    assert payload["version"] == 1
    assert payload["memory_id"] == "mem-1"
    assert payload["text"] == "Use dark backgrounds, smooth transitions, and concise labels."
    assert payload["tokens"] == [
        "use",
        "dark",
        "backgrounds",
        "smooth",
        "transitions",
        "and",
        "concise",
        "labels",
    ]
    assert payload["keywords"] == ["dark", "backgrounds", "smooth", "transitions", "concise", "labels"]


def test_normalize_retrieval_metadata_normalizes_existing_tokens_and_keywords() -> None:
    record = AgentMemoryRecord(
        memory_id="mem-2",
        agent_id="agent-a",
        source_session_id="session-2",
        summary_text="Any text",
        summary_digest="digest-2",
    )

    payload = normalize_retrieval_metadata(
        record,
        existing={
            "retrieval": {
                "keywords": [" Cinematic ", "AND", "Depth!", "x", "depth"],
                "tokens": ["Cinematic", "Depth!", "  ", "and"],
            }
        },
    )

    assert payload["tokens"] == ["cinematic", "depth", "and"]
    assert payload["keywords"] == ["cinematic", "depth"]
