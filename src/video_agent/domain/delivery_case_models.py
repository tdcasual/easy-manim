from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DeliveryCase(BaseModel):
    case_id: str
    root_task_id: str
    active_task_id: str | None = None
    selected_task_id: str | None = None
    selected_branch_id: str | None = None
    status: str = "queued"
    delivery_status: str = "pending"
    completion_mode: str | None = None
    stop_reason: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class AgentRun(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    case_id: str
    root_task_id: str
    thread_id: str | None = None
    iteration_id: str | None = None
    result_id: str | None = None
    task_id: str | None = None
    role: str
    status: str
    phase: str | None = None
    summary: str | None = None
    input_refs: list[str] = Field(default_factory=list)
    output_refs: list[str] = Field(default_factory=list)
    decision: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    stop_reason: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
