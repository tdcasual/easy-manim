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

    @property
    def confidence(self) -> float:
        return float(self.rationale_json.get("confidence", 0.0) or 0.0)

    @property
    def conflicts(self) -> list[dict[str, Any]]:
        raw = self.rationale_json.get("conflicts", [])
        return [item for item in raw if isinstance(item, dict)]

    @property
    def supporting_evidence_counts(self) -> dict[str, int]:
        raw = self.rationale_json.get("supporting_evidence_counts", {})
        if not isinstance(raw, dict):
            return {}
        counts: dict[str, int] = {}
        for field, value in raw.items():
            try:
                counts[str(field)] = int(value)
            except (TypeError, ValueError):
                continue
        return counts

    @property
    def field_support(self) -> dict[str, dict[str, Any]]:
        raw = self.rationale_json.get("field_support", {})
        if not isinstance(raw, dict):
            return {}
        return {
            str(field): value
            for field, value in raw.items()
            if isinstance(value, dict)
        }

    def is_safe_for_auto_apply(
        self,
        *,
        min_confidence: float = 0.8,
    ) -> bool:
        supporting_evidence_counts = self.supporting_evidence_counts
        return (
            self.status == "pending"
            and bool(self.patch_json)
            and self.confidence >= min_confidence
            and not self.conflicts
            and bool(supporting_evidence_counts)
            and all(count >= 2 for count in supporting_evidence_counts.values())
        )
