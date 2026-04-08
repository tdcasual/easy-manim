from __future__ import annotations

import hashlib
from typing import Callable

from video_agent.application.agent_authorization_service import AgentAuthorizationService
from video_agent.domain.agent_models import AgentProfile, AgentRuntimePrincipal, AgentToken
from video_agent.domain.agent_runtime_models import AgentRuntimeDefinition


AgentPrincipal = AgentRuntimePrincipal


class AgentIdentityService:
    def __init__(
        self,
        profile_lookup: Callable[[str], AgentProfile | None],
        token_lookup: Callable[[str], AgentToken | None],
        runtime_definition_resolver: Callable[[str, AgentProfile], AgentRuntimeDefinition] | None = None,
        authorization_service: AgentAuthorizationService | None = None,
    ) -> None:
        self._profile_lookup = profile_lookup
        self._token_lookup = token_lookup
        self._runtime_definition_resolver = runtime_definition_resolver
        self._authorization_service = authorization_service or AgentAuthorizationService()

    def authenticate(self, plain_token: str) -> AgentPrincipal:
        token_hash = hash_agent_token(plain_token)
        token = self._token_lookup(token_hash)
        if token is None:
            raise ValueError("unknown agent token")
        if token.status != "active":
            raise ValueError("inactive agent token")

        profile = self._profile_lookup(token.agent_id)
        if profile is None:
            raise ValueError("agent profile not found")
        return self.resolve_principal(profile=profile, token=token)

    def resolve_principal(
        self,
        *,
        profile: AgentProfile,
        token: AgentToken,
    ) -> AgentPrincipal:
        if profile.status != "active":
            raise ValueError("inactive agent profile")
        if token.status != "active":
            raise ValueError("inactive agent token")
        if token.agent_id != profile.agent_id:
            raise ValueError("agent token does not match profile")

        if self._runtime_definition_resolver is None:
            raise ValueError("agent runtime definition not found")
        runtime_definition = self._runtime_definition_resolver(profile.agent_id, profile)
        if getattr(runtime_definition, "status", None) != "active":
            raise ValueError("inactive agent runtime definition")

        return AgentPrincipal(
            agent_id=profile.agent_id,
            profile=profile,
            token=token,
            runtime_definition=runtime_definition,
        )

    def require_action(self, principal: AgentPrincipal, action: str) -> None:
        self._authorization_service.require_allowed(principal.profile, principal.token, action)


def hash_agent_token(plain_token: str) -> str:
    return hashlib.sha256(plain_token.encode("utf-8")).hexdigest()
