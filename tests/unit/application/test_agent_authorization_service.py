from video_agent.application.agent_authorization_service import AgentAuthorizationService
from video_agent.domain.agent_models import AgentProfile, AgentToken


def test_token_scope_can_deny_mutation() -> None:
    service = AgentAuthorizationService()
    profile = AgentProfile(agent_id="agent-a", name="Agent A")
    token = AgentToken(token_hash="hash", agent_id="agent-a", scopes_json={"allow": ["task:read"]})

    assert service.is_allowed(profile, token, "task:read") is True
    assert service.is_allowed(profile, token, "task:create") is False


def test_profile_policy_can_deny_action_when_token_has_no_allow_list() -> None:
    service = AgentAuthorizationService()
    profile = AgentProfile(
        agent_id="agent-a",
        name="Agent A",
        policy_json={"deny_actions": ["task:mutate"]},
    )
    token = AgentToken(token_hash="hash", agent_id="agent-a")

    assert service.is_allowed(profile, token, "task:read") is True
    assert service.is_allowed(profile, token, "task:mutate") is False


def test_token_deny_overrides_allow() -> None:
    service = AgentAuthorizationService()
    profile = AgentProfile(agent_id="agent-a", name="Agent A")
    token = AgentToken(
        token_hash="hash",
        agent_id="agent-a",
        scopes_json={"allow": ["task:create"], "deny": ["task:create"]},
    )

    assert service.is_allowed(profile, token, "task:create") is False
