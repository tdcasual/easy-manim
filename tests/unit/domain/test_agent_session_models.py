from video_agent.domain.agent_session_models import AgentSession


def test_agent_session_defaults_to_active() -> None:
    session = AgentSession(session_id="sess-1", session_hash="hash-1", agent_id="agent-a")

    assert session.status == "active"
    assert session.expires_at is not None
    assert session.last_seen_at is not None
