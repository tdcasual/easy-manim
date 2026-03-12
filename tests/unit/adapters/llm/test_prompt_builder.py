from video_agent.adapters.llm.prompt_builder import build_generation_prompt



def test_prompt_builder_includes_prompt_and_output_profile() -> None:
    prompt = build_generation_prompt(
        prompt="draw a circle",
        output_profile={"width": 1280, "height": 720},
        feedback=None,
    )
    assert "draw a circle" in prompt
    assert "1280" in prompt
