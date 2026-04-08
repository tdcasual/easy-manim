from __future__ import annotations

import pytest

from video_agent.application.agent_runtime_service import AgentRuntimeDefinitionService
from video_agent.domain.agent_models import AgentProfile
from video_agent.domain.agent_runtime_models import AgentRuntimeDefinition


def test_runtime_service_prefers_stored_runtime_definition() -> None:
    stored = AgentRuntimeDefinition(
        agent_id="agent-a",
        name="Agent A Runtime",
        workspace="/tmp/runtime-a",
        agent_dir="/tmp/runtime-a/agent",
        tools_allow=["read", "exec"],
        channels=[{"channel": "discord", "account_id": "ops"}],
    )
    service = AgentRuntimeDefinitionService(
        definition_lookup=lambda agent_id: stored if agent_id == "agent-a" else None,
    )

    resolved = service.resolve("agent-a", profile=AgentProfile(agent_id="agent-a", name="Agent A"))

    assert resolved == stored
    assert resolved.definition_source == "explicit"


def test_runtime_service_requires_persisted_runtime_definition() -> None:
    stored = AgentRuntimeDefinition(
        agent_id="agent-a",
        name="Agent A Runtime",
        workspace="/tmp/runtime-a",
        agent_dir="/tmp/runtime-a/agent",
        tools_allow=["read", "exec"],
    )
    service = AgentRuntimeDefinitionService(
        definition_lookup=lambda agent_id: stored if agent_id == "agent-a" else None,
    )

    assert service.require_persisted("agent-a") == stored


def test_runtime_service_rejects_missing_persisted_runtime_definition() -> None:
    service = AgentRuntimeDefinitionService(
        definition_lookup=lambda agent_id: None,
    )

    try:
        service.require_persisted("agent-a")
    except ValueError as exc:
        assert str(exc) == "agent runtime definition not found"
    else:
        raise AssertionError("Expected missing persisted runtime definition to raise")


def test_runtime_service_rejects_missing_runtime_definition_in_resolve() -> None:
    profile = AgentProfile(agent_id="agent-a", name="Agent A")
    service = AgentRuntimeDefinitionService(
        definition_lookup=lambda agent_id: None,
        default_workspace_root="/runtime-root",
    )

    with pytest.raises(ValueError, match="agent runtime definition not found"):
        service.resolve("agent-a", profile=profile)


def test_runtime_service_can_persist_materialized_runtime_definition() -> None:
    profile = AgentProfile(agent_id="agent-a", name="Agent A")
    persisted: list[AgentRuntimeDefinition] = []
    service = AgentRuntimeDefinitionService(
        definition_lookup=lambda agent_id: None,
        definition_upsert=lambda definition: persisted.append(definition) or definition,
        default_workspace_root="/runtime-root",
    )

    resolved = service.ensure_persisted(profile)

    assert resolved.agent_id == "agent-a"
    assert resolved.workspace == "/runtime-root/agent-a/workspace"
    assert resolved.agent_dir == "/runtime-root/agent-a/agent"
    assert resolved.definition_source == "materialized"
    assert persisted == [resolved]


def test_runtime_service_backfills_missing_definitions_for_existing_profiles() -> None:
    persisted: list[AgentRuntimeDefinition] = []
    existing = AgentRuntimeDefinition(
        agent_id="agent-b",
        name="Agent B",
        workspace="/runtime-root/agent-b/workspace",
        agent_dir="/runtime-root/agent-b/agent",
        tools_allow=["read", "exec"],
    )
    profiles = [
        AgentProfile(agent_id="agent-a", name="Agent A"),
        AgentProfile(agent_id="agent-b", name="Agent B"),
    ]
    service = AgentRuntimeDefinitionService(
        definition_lookup=lambda agent_id: existing if agent_id == "agent-b" else None,
        definition_upsert=lambda definition: persisted.append(definition) or definition,
        default_workspace_root="/runtime-root",
    )

    synced = service.ensure_persisted_for_profiles(profiles)

    assert [item.agent_id for item in synced] == ["agent-a"]
    assert synced[0].definition_source == "materialized"
    assert persisted == synced
