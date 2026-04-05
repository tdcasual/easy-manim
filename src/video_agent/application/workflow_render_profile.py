from __future__ import annotations

from typing import Any

from video_agent.config import Settings


def resolve_render_profile(task: Any, settings: Settings) -> dict[str, Any]:
    effective_profile = {}
    if getattr(task, "effective_request_profile", None):
        effective_profile = task.effective_request_profile.get("output_profile", {})
    profile = effective_profile or task.output_profile or {}
    return {
        "quality_preset": str(profile.get("quality_preset", settings.default_quality_preset)),
        "frame_rate": optional_positive_int(profile.get("frame_rate", settings.default_frame_rate)),
        "pixel_width": optional_positive_int(
            profile.get("pixel_width", profile.get("width", settings.default_pixel_width))
        ),
        "pixel_height": optional_positive_int(
            profile.get("pixel_height", profile.get("height", settings.default_pixel_height))
        ),
    }


def optional_positive_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def build_degraded_style_hints(style_hints: dict[str, Any] | None) -> dict[str, Any]:
    return {
        **(style_hints or {}),
        "scene_complexity": "low",
        "animation_density": "low",
        "camera": "static",
        "pace": "steady",
    }


def build_degraded_output_profile(output_profile: dict[str, Any] | None) -> dict[str, Any]:
    profile = dict(output_profile or {})
    profile["quality_preset"] = "development"
    return profile


def build_degraded_delivery_feedback(*, issue_code: str, generation_mode: str) -> str:
    issue_label = issue_code or "unknown_failure"
    return (
        "Guaranteed delivery degraded fallback. "
        f"Previous attempt failed with {issue_label}. "
        f"Prefer generation mode {generation_mode}. "
        "Produce the simplest playable video that still satisfies the core request. "
        "Use a static camera, low animation density, one focal idea, and simple shapes or text. "
        "Prioritize successful rendering over richness."
    )
