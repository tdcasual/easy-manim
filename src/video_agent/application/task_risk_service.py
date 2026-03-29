from __future__ import annotations

from typing import Any

from video_agent.domain.scene_spec_models import TaskRiskProfile


class TaskRiskService:
    def classify(
        self,
        *,
        prompt: str,
        style_hints: dict[str, Any],
        scene_spec: dict[str, Any] | None = None,
        runtime_status: dict[str, Any] | None = None,
    ) -> TaskRiskProfile:
        scene_spec = scene_spec or {}
        runtime_status = runtime_status or {}
        text = prompt.lower()
        triggered_signals: list[str] = []
        expected_failure_modes: list[str] = []

        formula_present = bool(scene_spec.get("formula_present")) or "mathtex" in text or "tex" in text
        if formula_present:
            triggered_signals.append("formula_present")
            expected_failure_modes.extend(["latex_dependency_missing", "render_failed"])

        complexity_level = _normalize_level(scene_spec.get("requested_scene_complexity") or style_hints.get("scene_complexity"))
        if complexity_level == "high":
            triggered_signals.append("requested_scene_complexity:high")
            expected_failure_modes.append("render_timeout")

        animation_density = _normalize_level(scene_spec.get("animation_density") or style_hints.get("animation_density"))
        if animation_density == "high":
            triggered_signals.append("animation_density:high")
            expected_failure_modes.append("animation_overload")

        provider_limitations = runtime_status.get("provider", {}).get("limitations", [])
        for limitation in provider_limitations:
            triggered_signals.append(f"provider_limit:{limitation}")

        if formula_present or complexity_level == "high" or animation_density == "high" or provider_limitations:
            return TaskRiskProfile(
                task_id="",
                risk_level="high",
                generation_mode="template_first",
                expected_failure_modes=list(dict.fromkeys(expected_failure_modes)),
                budget_class="tight",
                triggered_signals=triggered_signals,
            )

        if "logo" in text or "开场" in prompt:
            return TaskRiskProfile(
                task_id="",
                risk_level="low",
                generation_mode="guided_generate",
                budget_class="standard",
                triggered_signals=triggered_signals,
            )

        return TaskRiskProfile(
            task_id="",
            risk_level="medium",
            generation_mode="guided_generate",
            budget_class="standard",
            triggered_signals=triggered_signals,
        )


def _normalize_level(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"low", "medium", "high"}:
        return text
    return None
