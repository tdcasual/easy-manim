from video_agent.application.preference_resolver import (
    build_system_default_request_config,
    compute_profile_digest,
    resolve_effective_request_config,
)


def test_preference_resolver_uses_expected_precedence() -> None:
    effective = resolve_effective_request_config(
        system_defaults={"style_hints": {"tone": "clean"}},
        profile_json={"style_hints": {"tone": "teaching", "pace": "steady"}},
        token_override_json={"style_hints": {"pace": "brisk"}},
        strategy_profile_json={"style_hints": {"tone": "coach", "camera": "static"}},
        request_overrides={"style_hints": {"tone": "dramatic"}},
    )

    assert effective["style_hints"] == {"tone": "dramatic", "pace": "brisk", "camera": "static"}


def test_compute_profile_digest_is_stable_for_same_content() -> None:
    first = compute_profile_digest({"style_hints": {"tone": "teaching"}, "validation_profile": {"strict": True}})
    second = compute_profile_digest({"validation_profile": {"strict": True}, "style_hints": {"tone": "teaching"}})

    assert first == second


def test_system_default_request_config_includes_render_defaults() -> None:
    defaults = build_system_default_request_config(
        default_quality_preset="production",
        default_frame_rate=60,
        default_pixel_width=1920,
        default_pixel_height=1080,
    )

    assert defaults["output_profile"] == {
        "quality_preset": "production",
        "frame_rate": 60,
        "pixel_width": 1920,
        "pixel_height": 1080,
    }
