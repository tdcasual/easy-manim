from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentSession(BaseModel):
    session_id: str
    session_hash: str
    agent_id: str
    status: str = "active"
    created_at: datetime = Field(default_factory=_utcnow)
    expires_at: datetime = Field(default_factory=lambda: _utcnow() + timedelta(days=7))
    last_seen_at: datetime = Field(default_factory=_utcnow)
    revoked_at: datetime | None = None
