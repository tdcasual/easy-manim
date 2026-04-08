from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentRuntimeDefinition(BaseModel):
    agent_id: str
    name: str
    status: str = "active"
    workspace: str
    agent_dir: str
    tools_allow: list[str] = Field(default_factory=list)
    channels: list[dict[str, Any]] = Field(default_factory=list)
    delegate_metadata: dict[str, Any] = Field(default_factory=dict)
    definition_source: str = "explicit"
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
