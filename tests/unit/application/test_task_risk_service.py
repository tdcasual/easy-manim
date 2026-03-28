from video_agent.application.task_risk_service import TaskRiskService


def test_task_risk_service_routes_formula_prompt_to_high_risk() -> None:
    service = TaskRiskService()

    profile = service.classify(prompt="使用 MathTex 展示二次公式推导", style_hints={})

    assert profile.risk_level == "high"
    assert profile.generation_mode == "template_first"
    assert "latex_dependency_missing" in profile.expected_failure_modes


def test_task_risk_service_uses_guided_generate_for_general_prompt() -> None:
    service = TaskRiskService()

    profile = service.classify(prompt="draw a blue circle", style_hints={"tone": "teaching"})

    assert profile.risk_level in {"low", "medium"}
    assert profile.generation_mode == "guided_generate"
