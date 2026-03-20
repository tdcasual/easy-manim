from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentProfile(BaseModel):
    agent_id: str
    name: str
    status: str = "active"
    profile_version: int = 1
    profile_json: dict[str, Any] = Field(default_factory=dict)
    policy_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    @property
    def denied_actions(self) -> set[str]:
        raw = self.policy_json.get("deny_actions", [])
        if not isinstance(raw, list):
            return set()
        return {str(item) for item in raw}


class AgentToken(BaseModel):
    token_hash: str
    agent_id: str
    status: str = "active"
    scopes_json: dict[str, Any] = Field(default_factory=dict)
    override_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    @property
    def allowed_actions(self) -> set[str]:
        raw = self.scopes_json.get("allow", [])
        if not isinstance(raw, list):
            return set()
        return {str(item) for item in raw}

    @property
    def denied_actions(self) -> set[str]:
        raw = self.scopes_json.get("deny", [])
        if not isinstance(raw, list):
            return set()
        return {str(item) for item in raw}
