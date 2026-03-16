from video_agent.domain.agent_memory_models import AgentMemoryRecord


def test_agent_memory_record_defaults_to_active() -> None:
    record = AgentMemoryRecord(
        memory_id="mem-1",
        agent_id="agent-a",
        source_session_id="session-1",
        summary_text="Use a light background and clear labels.",
        summary_digest="digest-1",
        lineage_refs=["video-task://task-1/task.json"],
        snapshot={"entry_count": 1},
    )

    assert record.status == "active"
    assert record.disabled_at is None
