from video_agent.server.session_memory import SessionMemoryRegistry


def test_registry_allocates_distinct_session_ids_for_distinct_session_keys() -> None:
    registry = SessionMemoryRegistry()

    session_a = registry.ensure_session("session-a", agent_id="agent-a")
    session_b = registry.ensure_session("session-b", agent_id="agent-a")

    assert session_a.session_id != session_b.session_id


def test_registry_returns_stable_empty_memory_snapshot() -> None:
    registry = SessionMemoryRegistry()
    session = registry.ensure_session("session-a", agent_id="agent-a")

    snapshot = registry.get_snapshot(session.session_id)

    assert snapshot.session_id == session.session_id
    assert snapshot.agent_id == "agent-a"
    assert snapshot.entries == []
    assert snapshot.entry_count == 0


def test_clear_only_removes_the_target_session() -> None:
    registry = SessionMemoryRegistry()
    session_a = registry.ensure_session("session-a", agent_id="agent-a")
    session_b = registry.ensure_session("session-b", agent_id="agent-a")

    registry.clear_session(session_a.session_id)

    assert registry.get_snapshot(session_a.session_id).entry_count == 0
    assert registry.get_snapshot(session_b.session_id).session_id == session_b.session_id
