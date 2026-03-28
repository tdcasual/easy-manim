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


def test_capability_gate_allows_non_formula_prompt() -> None:
    gate = CapabilityGateService()

    decision = gate.evaluate(
        prompt="draw a blue circle",
        scene_spec={"generation_mode": "guided_generate"},
        runtime_status={"mathtex": {"available": False}},
    )

    assert decision.allowed is True
    assert decision.block_reason is None
