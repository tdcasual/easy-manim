from video_agent.adapters.llm.client import StubLLMClient



def test_stub_llm_generates_animated_scene_by_default() -> None:
    script = StubLLMClient().generate_script("draw a circle")
    assert "Create" in script
    assert "self.play(" in script
