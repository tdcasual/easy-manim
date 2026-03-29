from video_agent.application.task_risk_service import TaskRiskService


def test_task_risk_service_routes_formula_prompt_to_high_risk() -> None:
    service = TaskRiskService()

    profile = service.classify(prompt="使用 MathTex 展示二次公式推导", style_hints={})

    assert profile.risk_level == "high"
    assert profile.generation_mode == "template_first"
    assert "latex_dependency_missing" in profile.expected_failure_modes
    assert "formula_present" in profile.triggered_signals


def test_task_risk_service_uses_guided_generate_for_general_prompt() -> None:
    service = TaskRiskService()

    profile = service.classify(prompt="draw a blue circle", style_hints={"tone": "teaching"})

    assert profile.risk_level in {"low", "medium"}
    assert profile.generation_mode == "guided_generate"


def test_task_risk_service_uses_scene_spec_complexity_and_animation_density() -> None:
    service = TaskRiskService()

    profile = service.classify(
        prompt="show a concept map",
        style_hints={},
        scene_spec={
            "requested_scene_complexity": "high",
            "animation_density": "high",
            "formula_present": False,
        },
    )

    assert profile.risk_level == "high"
    assert profile.generation_mode == "template_first"
    assert "requested_scene_complexity:high" in profile.triggered_signals
    assert "animation_density:high" in profile.triggered_signals


def test_task_risk_service_captures_provider_limitations_as_structured_signal() -> None:
    service = TaskRiskService()

    profile = service.classify(
        prompt="draw a blue circle",
        style_hints={},
        scene_spec={"animation_density": "high"},
        runtime_status={"provider": {"limitations": ["dense_animation_unstable"]}},
    )

    assert profile.risk_level == "high"
    assert profile.generation_mode == "template_first"
    assert "provider_limit:dense_animation_unstable" in profile.triggered_signals
