from __future__ import annotations

from typing import Any

from video_agent.application.scene_plan import build_scene_plan
from video_agent.domain.scene_spec_models import SceneSpec


class SceneSpecService:
    def build(
        self,
        *,
        prompt: str,
        output_profile: dict[str, Any],
        style_hints: dict[str, Any],
        generation_mode: str = "guided_generate",
    ) -> SceneSpec:
        scene_plan = build_scene_plan(
            prompt=prompt,
            output_profile=output_profile,
            style_hints=style_hints,
        )
        requested_scene_complexity = _normalize_level(style_hints.get("scene_complexity"))
        animation_density = _normalize_level(style_hints.get("animation_density")) or _density_from_plan(scene_plan)
        animation_density_score = _density_score(animation_density)
        return SceneSpec(
            task_id="",
            summary=scene_plan.scene_goal or prompt,
            scene_count=max(1, len(scene_plan.sections)),
            scenes=[scene_plan.model_dump(mode="json")],
            camera_strategy=scene_plan.camera_strategy,
            generation_mode=generation_mode,
            formula_present=scene_plan.formula_strategy != "none",
            requested_scene_complexity=requested_scene_complexity,
            animation_density=animation_density,
            animation_density_score=animation_density_score,
        )


def _normalize_level(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"low", "medium", "high"}:
        return text
    return None


def _density_from_plan(scene_plan: Any) -> str:
    recipe_count = len(getattr(scene_plan, "animation_recipes", []))
    if recipe_count >= 2:
        return "high"
    if recipe_count == 1:
        return "medium"
    return "low"


def _density_score(level: str | None) -> int:
    if level == "high":
        return 3
    if level == "medium":
        return 2
    if level == "low":
        return 1
    return 0
