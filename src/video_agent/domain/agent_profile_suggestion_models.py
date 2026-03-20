from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentProfileSuggestion(BaseModel):
    suggestion_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_id: str
    patch_json: dict[str, Any] = Field(default_factory=dict)
    rationale_json: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"
    created_at: datetime = Field(default_factory=_utcnow)
    applied_at: datetime | None = None

    @property
    def patch(self) -> dict[str, Any]:
        return self.patch_json
