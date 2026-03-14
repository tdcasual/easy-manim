from video_agent.adapters.llm.client import StubLLMClient



def test_stub_llm_generates_animated_scene_by_default() -> None:
    script = StubLLMClient().generate_script("draw a circle")
    assert "Create" in script
    assert "self.play(" in script


def test_stub_llm_generates_visible_formula_scene_for_quality_prompt() -> None:
    script = StubLLMClient().generate_script(
        "User request: show the quadratic formula and focus on the discriminant\n"
        "Formula strategy: mathtex_focus\n"
        "Quality directives: ['avoid_blank_opening_frame']\n"
    )

    assert "config.background_color" in script
    assert "Quadratic Formula" in script
    assert "self.add(" in script
