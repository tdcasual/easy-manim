from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RecoveryPlan(BaseModel):
    issue_code: str | None = None
    task_id: str
    candidate_actions: list[str] = Field(default_factory=list)
    selected_action: str | None = None
    repair_recipe: dict[str, Any] | str | None = None
    fallback_generation_mode: str | None = None
    cost_class: str | None = None
    human_gate_required: bool = False
