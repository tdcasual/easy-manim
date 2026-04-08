import hashlib

import pytest

from video_agent.application.agent_identity_service import AgentIdentityService
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.domain.agent_runtime_models import AgentRuntimeDefinition


def test_identity_service_resolves_active_token_to_profile() -> None:
    runtime_definition = AgentRuntimeDefinition(
        agent_id="agent-a",
        name="Agent A",
        workspace="/tmp/agent-a/workspace",
        agent_dir="/tmp/agent-a/agent",
        tools_allow=["read", "exec"],
    )
    service = AgentIdentityService(
        profile_lookup=lambda agent_id: AgentProfile(agent_id=agent_id, name="Agent A"),
        token_lookup=lambda token_hash: AgentToken(token_hash=token_hash, agent_id="agent-a"),
        runtime_definition_resolver=lambda agent_id, profile: runtime_definition,
    )

    principal = service.authenticate("plain-token")

    assert principal.agent_id == "agent-a"
    assert principal.profile.name == "Agent A"
    assert principal.token.token_hash == hashlib.sha256(b"plain-token").hexdigest()
    assert principal.runtime_definition == runtime_definition


def test_identity_service_can_resolve_principal_from_existing_profile_and_token() -> None:
    profile = AgentProfile(agent_id="agent-a", name="Agent A")
    token = AgentToken(token_hash="token-hash", agent_id="agent-a")
    runtime_definition = AgentRuntimeDefinition(
        agent_id="agent-a",
        name="Agent A",
        workspace="/tmp/agent-a/workspace",
        agent_dir="/tmp/agent-a/agent",
        tools_allow=["read", "exec"],
    )
    service = AgentIdentityService(
        profile_lookup=lambda agent_id: profile,
        token_lookup=lambda token_hash: token,
        runtime_definition_resolver=lambda agent_id, loaded_profile: runtime_definition,
    )

    principal = service.resolve_principal(profile=profile, token=token)

    assert principal.agent_id == "agent-a"
    assert principal.profile == profile
    assert principal.token == token
    assert principal.runtime_definition == runtime_definition


def test_identity_service_rejects_inactive_token() -> None:
    service = AgentIdentityService(
        profile_lookup=lambda agent_id: AgentProfile(agent_id=agent_id, name="Agent A"),
        token_lookup=lambda token_hash: AgentToken(token_hash=token_hash, agent_id="agent-a", status="disabled"),
        runtime_definition_resolver=lambda agent_id, profile: AgentRuntimeDefinition(
            agent_id=agent_id,
            name="Agent A",
            workspace="/tmp/agent-a/workspace",
            agent_dir="/tmp/agent-a/agent",
            tools_allow=["read", "exec"],
        ),
    )

    with pytest.raises(ValueError, match="inactive agent token"):
        service.authenticate("plain-token")


def test_identity_service_rejects_token_profile_agent_mismatch() -> None:
    profile = AgentProfile(agent_id="agent-a", name="Agent A")
    token = AgentToken(token_hash="token-hash", agent_id="agent-b")
    service = AgentIdentityService(
        profile_lookup=lambda agent_id: profile,
        token_lookup=lambda token_hash: token,
        runtime_definition_resolver=lambda agent_id, loaded_profile: AgentRuntimeDefinition(
            agent_id="agent-a",
            name="Agent A",
            workspace="/tmp/agent-a/workspace",
            agent_dir="/tmp/agent-a/agent",
            tools_allow=["read", "exec"],
        ),
    )

    with pytest.raises(ValueError, match="agent token does not match profile"):
        service.resolve_principal(profile=profile, token=token)


def test_identity_service_rejects_missing_persisted_runtime_definition() -> None:
    profile = AgentProfile(agent_id="agent-a", name="Agent A")
    token = AgentToken(token_hash="token-hash", agent_id="agent-a")
    service = AgentIdentityService(
        profile_lookup=lambda agent_id: profile,
        token_lookup=lambda token_hash: token,
        runtime_definition_resolver=lambda agent_id, loaded_profile: (_ for _ in ()).throw(
            ValueError("agent runtime definition not found")
        ),
    )

    with pytest.raises(ValueError, match="agent runtime definition not found"):
        service.resolve_principal(profile=profile, token=token)
