from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from video_agent.domain.agent_models import AgentProfile
from video_agent.domain.agent_runtime_models import AgentRuntimeDefinition

DEFAULT_AGENT_RUNTIME_TOOLS_ALLOW = [
    "read",
    "exec",
    "message",
    "sessions_history",
    "sessions_list",
]


class AgentRuntimeDefinitionService:
    def __init__(
        self,
        *,
        definition_lookup: Callable[[str], AgentRuntimeDefinition | None],
        definition_upsert: Callable[[AgentRuntimeDefinition], AgentRuntimeDefinition] | None = None,
        default_workspace_root: str | Path = Path(".openclaw/agents"),
        default_tools_allow: list[str] | None = None,
    ) -> None:
        self.definition_lookup = definition_lookup
        self.definition_upsert = definition_upsert
        self.default_workspace_root = Path(default_workspace_root)
        self.default_tools_allow = list(default_tools_allow or DEFAULT_AGENT_RUNTIME_TOOLS_ALLOW)

    def resolve(self, agent_id: str, *, profile: AgentProfile) -> AgentRuntimeDefinition:
        _ = profile
        return self.require_persisted(agent_id)

    def require_persisted(self, agent_id: str) -> AgentRuntimeDefinition:
        stored = self.definition_lookup(agent_id)
        if stored is None:
            raise ValueError("agent runtime definition not found")
        return stored

    def build_default_definition(self, profile: AgentProfile) -> AgentRuntimeDefinition:
        runtime_root = self.default_workspace_root / profile.agent_id
        return AgentRuntimeDefinition(
            agent_id=profile.agent_id,
            name=profile.name,
            status=profile.status,
            workspace=str(runtime_root / "workspace"),
            agent_dir=str(runtime_root / "agent"),
            tools_allow=list(self.default_tools_allow),
            channels=[],
            delegate_metadata={},
            definition_source="materialized",
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )

    def ensure_persisted(self, profile: AgentProfile) -> AgentRuntimeDefinition:
        stored = self.definition_lookup(profile.agent_id)
        if stored is not None:
            return stored
        materialized = self.build_default_definition(profile)
        if self.definition_upsert is None:
            return materialized
        return self.definition_upsert(materialized)

    def ensure_persisted_for_profiles(
        self,
        profiles: list[AgentProfile],
    ) -> list[AgentRuntimeDefinition]:
        synced: list[AgentRuntimeDefinition] = []
        for profile in profiles:
            if self.definition_lookup(profile.agent_id) is not None:
                continue
            synced.append(self.ensure_persisted(profile))
        return synced
