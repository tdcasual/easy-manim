from video_agent.application.preference_resolver import compute_profile_digest, resolve_effective_request_config


def test_preference_resolver_uses_expected_precedence() -> None:
    effective = resolve_effective_request_config(
        system_defaults={"style_hints": {"tone": "clean"}},
        profile_json={"style_hints": {"tone": "teaching", "pace": "steady"}},
        token_override_json={"style_hints": {"pace": "brisk"}},
        request_overrides={"style_hints": {"tone": "dramatic"}},
    )

    assert effective["style_hints"] == {"tone": "dramatic", "pace": "brisk"}


def test_compute_profile_digest_is_stable_for_same_content() -> None:
    first = compute_profile_digest({"style_hints": {"tone": "teaching"}, "validation_profile": {"strict": True}})
    second = compute_profile_digest({"validation_profile": {"strict": True}, "style_hints": {"tone": "teaching"}})

    assert first == second
