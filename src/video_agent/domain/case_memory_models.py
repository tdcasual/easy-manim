from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CaseMemorySnapshot(BaseModel):
    root_task_id: str
    planner_notes: list[dict[str, Any]] = Field(default_factory=list)
    review_findings: list[dict[str, Any]] = Field(default_factory=list)
    repair_constraints: list[dict[str, Any]] = Field(default_factory=list)
    branch_comparisons: list[dict[str, Any]] = Field(default_factory=list)
    decision_log: list[dict[str, Any]] = Field(default_factory=list)
    delivery_invariants: list[str] = Field(default_factory=list)
