from video_agent.application.capability_gate_service import CapabilityGateService


def test_capability_gate_blocks_formula_scene_when_latex_missing() -> None:
    gate = CapabilityGateService()

    decision = gate.evaluate(
        prompt="使用 MathTex 展示公式",
        scene_spec={"generation_mode": "template_first"},
        runtime_status={"mathtex": {"available": False}},
    )

    assert decision.allowed is False
    assert decision.block_reason == "latex_dependency_missing"
    assert decision.suggested_mode == "guided_generate"
    assert "formula_present" in decision.triggered_signals


def test_capability_gate_allows_non_formula_prompt() -> None:
    gate = CapabilityGateService()

    decision = gate.evaluate(
        prompt="draw a blue circle",
        scene_spec={"generation_mode": "guided_generate"},
        runtime_status={"mathtex": {"available": False}},
    )

    assert decision.allowed is True
    assert decision.block_reason is None


def test_capability_gate_blocks_formula_from_scene_spec_without_prompt_keywords() -> None:
    gate = CapabilityGateService()

    decision = gate.evaluate(
        prompt="introduce the concept",
        scene_spec={"formula_present": True, "generation_mode": "template_first"},
        runtime_status={"mathtex": {"available": False}},
    )

    assert decision.allowed is False
    assert decision.block_reason == "latex_dependency_missing"
    assert "formula_present" in decision.triggered_signals


def test_capability_gate_blocks_when_provider_density_limit_is_exceeded() -> None:
    gate = CapabilityGateService()

    decision = gate.evaluate(
        prompt="draw a flow",
        scene_spec={"animation_density_score": 4, "generation_mode": "guided_generate"},
        runtime_status={
            "mathtex": {"available": True},
            "provider": {"limits": {"max_animation_density_score": 2}},
        },
    )

    assert decision.allowed is False
    assert decision.block_reason == "provider_animation_density_limit"
    assert decision.suggested_mode == "template_first"
    assert "provider_limit:max_animation_density_score=2" in decision.triggered_signals
