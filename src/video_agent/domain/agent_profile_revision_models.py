from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentProfileRevision(BaseModel):
    revision_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_id: str
    patch_json: dict[str, Any] = Field(default_factory=dict)
    source: str
    created_at: datetime = Field(default_factory=_utcnow)
