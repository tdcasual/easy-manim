from __future__ import annotations

from typing import Any

from video_agent.domain.scene_spec_models import TaskRiskProfile


class TaskRiskService:
    def classify(self, *, prompt: str, style_hints: dict[str, Any]) -> TaskRiskProfile:
        _ = style_hints
        text = prompt.lower()

        if "mathtex" in text or "tex" in text:
            return TaskRiskProfile(
                task_id="",
                risk_level="high",
                generation_mode="template_first",
                expected_failure_modes=["latex_dependency_missing", "render_failed"],
                budget_class="tight",
            )

        if "logo" in text or "开场" in prompt:
            return TaskRiskProfile(
                task_id="",
                risk_level="low",
                generation_mode="guided_generate",
                budget_class="standard",
            )

        return TaskRiskProfile(
            task_id="",
            risk_level="medium",
            generation_mode="guided_generate",
            budget_class="standard",
        )
