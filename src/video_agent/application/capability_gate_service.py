from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CapabilityGateDecision(BaseModel):
    allowed: bool
    block_reason: str | None = None
    suggested_mode: str | None = None
    triggered_signals: list[str] = Field(default_factory=list)


class CapabilityGateService:
    def evaluate(
        self,
        *,
        prompt: str,
        scene_spec: dict[str, Any],
        runtime_status: dict[str, Any],
    ) -> CapabilityGateDecision:
        text = prompt.lower()
        triggered_signals: list[str] = []
        formula_present = bool(scene_spec.get("formula_present")) or "mathtex" in text or "tex" in text
        if formula_present:
            triggered_signals.append("formula_present")

        mathtex_available = runtime_status.get("mathtex", {}).get("available", False)
        if formula_present and not mathtex_available:
            return CapabilityGateDecision(
                allowed=False,
                block_reason="latex_dependency_missing",
                suggested_mode="guided_generate",
                triggered_signals=triggered_signals,
            )

        density_score = _as_int(scene_spec.get("animation_density_score"), fallback=0)
        max_density = _as_int(runtime_status.get("provider", {}).get("limits", {}).get("max_animation_density_score"))
        if max_density is not None and density_score > max_density:
            triggered_signals.append(f"provider_limit:max_animation_density_score={max_density}")
            return CapabilityGateDecision(
                allowed=False,
                block_reason="provider_animation_density_limit",
                suggested_mode="template_first",
                triggered_signals=triggered_signals,
            )

        return CapabilityGateDecision(allowed=True, triggered_signals=triggered_signals)


def _as_int(value: Any, fallback: int | None = None) -> int | None:
    if value is None:
        return fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback
