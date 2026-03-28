from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class CapabilityGateDecision(BaseModel):
    allowed: bool
    block_reason: str | None = None
    suggested_mode: str | None = None


class CapabilityGateService:
    def evaluate(
        self,
        *,
        prompt: str,
        scene_spec: dict[str, Any],
        runtime_status: dict[str, Any],
    ) -> CapabilityGateDecision:
        _ = scene_spec
        text = prompt.lower()
        mathtex_available = runtime_status.get("mathtex", {}).get("available", False)
        if ("mathtex" in text or "tex" in text) and not mathtex_available:
            return CapabilityGateDecision(
                allowed=False,
                block_reason="latex_dependency_missing",
                suggested_mode="guided_generate",
            )
        return CapabilityGateDecision(allowed=True)
