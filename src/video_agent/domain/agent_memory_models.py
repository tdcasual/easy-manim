from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentMemoryRecord(BaseModel):
    memory_id: str
    agent_id: str
    source_session_id: str
    status: str = "active"
    summary_text: str
    summary_digest: str
    lineage_refs: list[str] = Field(default_factory=list)
    snapshot: dict[str, Any] = Field(default_factory=dict)
    enhancement: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)
    disabled_at: datetime | None = None
