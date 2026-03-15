from video_agent.domain.agent_models import AgentProfile, AgentToken


def test_agent_profile_defaults_to_active() -> None:
    profile = AgentProfile(agent_id="agent-a", name="Agent A")

    assert profile.status == "active"
    assert profile.profile_json == {}
    assert profile.policy_json == {}


def test_agent_token_stores_hash_not_plaintext() -> None:
    token = AgentToken(token_hash="abc123", agent_id="agent-a")

    assert token.token_hash == "abc123"
    assert token.status == "active"
    assert token.scopes_json == {}
    assert token.override_json == {}
