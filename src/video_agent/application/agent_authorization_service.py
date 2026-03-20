from __future__ import annotations

from video_agent.domain.agent_models import AgentProfile, AgentToken


class AgentAuthorizationService:
    KNOWN_ACTIONS = {
        "task:create",
        "task:read",
        "task:mutate",
        "memory:read",
        "memory:clear",
        "memory:promote",
        "memory:write",
        "profile:read",
        "profile:write",
    }

    def is_allowed(self, profile: AgentProfile, token: AgentToken, action: str) -> bool:
        allow = token.allowed_actions
        deny = token.denied_actions
        if action in deny:
            return False
        if allow:
            return action in allow
        return action not in profile.denied_actions

    def require_allowed(self, profile: AgentProfile, token: AgentToken, action: str) -> None:
        if not self.is_allowed(profile, token, action):
            raise PermissionError("agent_scope_denied")
