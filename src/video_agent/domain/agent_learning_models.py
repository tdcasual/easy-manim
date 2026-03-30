from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentLearningEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_id: str
    task_id: str
    session_id: str | None = None
    status: str
    quality_passed: bool | None = None
    issue_codes: list[str] = Field(default_factory=list)
    quality_score: float = 0.0
    profile_digest: str | None = None
    memory_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)
