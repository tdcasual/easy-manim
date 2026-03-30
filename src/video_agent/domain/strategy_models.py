from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StrategyProfile(BaseModel):
    strategy_id: str
    scope: str
    prompt_cluster: str | None = None
    status: str
    params: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class PromptClusterStats(BaseModel):
    prompt_cluster: str
    total_runs: int = 0
    success_rate: float = 0.0
    average_quality_score: float | None = None


class StrategyPromotionDecision(BaseModel):
    approved: bool
    reasons: list[str] = Field(default_factory=list)
    deltas: dict[str, float] = Field(default_factory=dict)
    mode: str = "shadow"
    applied: bool = False
    recorded_at: str | None = None
