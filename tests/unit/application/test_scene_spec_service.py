from video_agent.application.scene_spec_service import SceneSpecService


def test_scene_spec_service_builds_stable_scene_spec() -> None:
    service = SceneSpecService()

    spec = service.build(
        prompt="draw a blue circle and label the radius",
        output_profile={"quality_preset": "development"},
        style_hints={"tone": "teaching"},
    )

    assert spec.scene_count >= 1
    assert spec.summary
    assert spec.generation_mode in {"template_first", "guided_generate", "open_generate"}
    assert spec.scenes


def test_scene_spec_service_uses_scene_plan_camera_strategy() -> None:
    service = SceneSpecService()

    spec = service.build(
        prompt="show a sine wave and clearly label its amplitude",
        output_profile={"quality_preset": "production"},
        style_hints={},
        generation_mode="guided_generate",
    )

    assert spec.camera_strategy == "auto_zoom"
    assert spec.generation_mode == "guided_generate"
