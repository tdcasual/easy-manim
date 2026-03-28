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
        return SceneSpec(
            task_id="",
            summary=scene_plan.scene_goal or prompt,
            scene_count=max(1, len(scene_plan.sections)),
            scenes=[scene_plan.model_dump(mode="json")],
            camera_strategy=scene_plan.camera_strategy,
            generation_mode=generation_mode,
        )
