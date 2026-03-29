from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SceneSpec(BaseModel):
    scene_spec_id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str
    summary: str
    scene_count: int
    scenes: list[dict[str, Any]] = Field(default_factory=list)
    timing_budget_seconds: float | None = None
    camera_strategy: str | None = None
    visual_constraints: list[str] = Field(default_factory=list)
    text_constraints: list[str] = Field(default_factory=list)
    style_constraints: list[str] = Field(default_factory=list)
    forbidden_elements: list[str] = Field(default_factory=list)
    generation_mode: str | None = None
    formula_present: bool = False
    requested_scene_complexity: str | None = None
    animation_density: str | None = None
    animation_density_score: int = 0
    risk_signals: list[str] = Field(default_factory=list)
    capability_gate: dict[str, Any] | None = None
    capability_gate_signals: list[str] = Field(default_factory=list)


class TaskRiskProfile(BaseModel):
    task_id: str
    risk_level: str
    generation_mode: str
    blocked_capabilities: list[str] = Field(default_factory=list)
    expected_failure_modes: list[str] = Field(default_factory=list)
    budget_class: str | None = None
    triggered_signals: list[str] = Field(default_factory=list)
