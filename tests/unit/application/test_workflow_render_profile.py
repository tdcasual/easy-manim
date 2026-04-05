from types import SimpleNamespace

from video_agent.config import Settings
from video_agent.application.workflow_render_profile import (
    build_degraded_delivery_feedback,
    build_degraded_output_profile,
    build_degraded_style_hints,
    optional_positive_int,
    resolve_render_profile,
)


def test_optional_positive_int_accepts_positive_integers_and_strings() -> None:
    assert optional_positive_int(24) == 24
    assert optional_positive_int("60") == 60


def test_optional_positive_int_rejects_blank_non_numeric_and_non_positive_values() -> None:
    assert optional_positive_int(None) is None
    assert optional_positive_int("") is None
    assert optional_positive_int("abc") is None
    assert optional_positive_int(0) is None
    assert optional_positive_int(-10) is None


def test_resolve_render_profile_prefers_effective_request_profile_output_profile() -> None:
    settings = Settings(
        default_quality_preset="development",
        default_frame_rate=15,
        default_pixel_width=854,
        default_pixel_height=480,
    )
    task = SimpleNamespace(
        effective_request_profile={
            "output_profile": {
                "quality_preset": "production",
                "frame_rate": "30",
                "pixel_width": "1280",
                "height": "720",
            }
        },
        output_profile={"quality_preset": "preview", "frame_rate": 24},
    )

    assert resolve_render_profile(task, settings) == {
        "quality_preset": "production",
        "frame_rate": 30,
        "pixel_width": 1280,
        "pixel_height": 720,
    }


def test_resolve_render_profile_falls_back_to_task_and_settings_defaults() -> None:
    settings = Settings(
        default_quality_preset="development",
        default_frame_rate=15,
        default_pixel_width=854,
        default_pixel_height=480,
    )
    task = SimpleNamespace(
        effective_request_profile=None,
        output_profile={"quality_preset": "preview", "frame_rate": 0, "width": "1024"},
    )

    assert resolve_render_profile(task, settings) == {
        "quality_preset": "preview",
        "frame_rate": None,
        "pixel_width": 1024,
        "pixel_height": 480,
    }


def test_build_degraded_style_hints_overrides_motion_related_defaults() -> None:
    assert build_degraded_style_hints({"pace": "fast", "tone": "teaching"}) == {
        "pace": "steady",
        "tone": "teaching",
        "scene_complexity": "low",
        "animation_density": "low",
        "camera": "static",
    }


def test_build_degraded_output_profile_forces_development_quality() -> None:
    assert build_degraded_output_profile({"quality_preset": "production", "frame_rate": 30}) == {
        "quality_preset": "development",
        "frame_rate": 30,
    }


def test_build_degraded_delivery_feedback_mentions_issue_and_generation_mode() -> None:
    feedback = build_degraded_delivery_feedback(issue_code="preview_static", generation_mode="safe_generate")

    assert "preview_static" in feedback
    assert "safe_generate" in feedback
    assert "simplest playable video" in feedback
