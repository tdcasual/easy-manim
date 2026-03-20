from __future__ import annotations

import hashlib
from typing import Callable

from pydantic import BaseModel

from video_agent.application.agent_authorization_service import AgentAuthorizationService
from video_agent.domain.agent_models import AgentProfile, AgentToken


class AgentPrincipal(BaseModel):
    agent_id: str
    profile: AgentProfile
    token: AgentToken


class AgentIdentityService:
    def __init__(
        self,
        profile_lookup: Callable[[str], AgentProfile | None],
        token_lookup: Callable[[str], AgentToken | None],
        authorization_service: AgentAuthorizationService | None = None,
    ) -> None:
        self._profile_lookup = profile_lookup
        self._token_lookup = token_lookup
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
        if profile.status != "active":
            raise ValueError("inactive agent profile")

        return AgentPrincipal(agent_id=profile.agent_id, profile=profile, token=token)

    def require_action(self, principal: AgentPrincipal, action: str) -> None:
        self._authorization_service.require_allowed(principal.profile, principal.token, action)


def hash_agent_token(plain_token: str) -> str:
    return hashlib.sha256(plain_token.encode("utf-8")).hexdigest()
