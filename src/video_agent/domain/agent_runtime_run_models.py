from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentRuntimeRun(BaseModel):
    run_id: str = Field(default_factory=lambda: f"agent-run-{uuid4().hex}")
    session_id: str
    agent_id: str
    source_kind: str
    trigger_kind: str
    status: str = "completed"
    task_id: str | None = None
    thread_id: str | None = None
    iteration_id: str | None = None
    summary: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
