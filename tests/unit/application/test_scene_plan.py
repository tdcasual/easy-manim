from video_agent.application.scene_plan import build_scene_plan


def test_build_scene_plan_routes_formula_prompt_to_mathtex_profile() -> None:
    plan = build_scene_plan(
        prompt="show the quadratic formula and highlight the discriminant",
        output_profile={"quality_preset": "production"},
        style_hints={"tone": "teaching"},
    )

    assert plan.scene_class == "MovingCameraScene"
    assert plan.formula_strategy == "mathtex_focus"
    assert plan.sections[0].goal
    assert "Indicate" in plan.animation_recipes
    assert "SurroundingRectangle" in plan.animation_recipes
    assert "TransformMatchingTex" not in plan.animation_recipes
    assert "avoid_numeric_mathtex_slices" in plan.quality_directives
    assert "prefer_symbolic_tex_selection" in plan.quality_directives
    assert "prefer_non_destructive_formula_emphasis" in plan.quality_directives
    assert "only_transform_matching_full_expressions" in plan.quality_directives
    assert "relayout_formula_for_recap" in plan.quality_directives
    assert "isolate_full_tex_term_before_highlight" in plan.quality_directives
    assert "avoid_bare_tex_control_sequence_highlights" in plan.quality_directives
    assert "only_pass_animations_to_play" in plan.quality_directives
    assert "use_mathex_for_symbolic_labels" in plan.quality_directives
    assert "avoid_bare_tex_control_sequence_selection" in plan.quality_directives
    assert "ensure_visible_motion_stage" in plan.quality_directives


def test_build_scene_plan_uses_style_hints_and_output_profile_for_quality_guidance() -> None:
    plan = build_scene_plan(
        prompt="show a labeled axis animation",
        output_profile={"quality_preset": "production"},
        style_hints={"tone": "clean", "pace": "steady", "camera": "static"},
    )

    assert plan.scene_class == "Scene"
    assert plan.camera_strategy == "static"
    assert plan.transition_style == "lagged"
    assert plan.pacing_strategy == "measured"
    assert "avoid_blank_opening_frame" in plan.quality_directives
    assert "prefer_light_background" in plan.quality_directives
    assert "favor_readable_spacing" in plan.quality_directives
    assert "favor_clear_labels" in plan.quality_directives
    assert "ensure_distinct_section_staging" in plan.quality_directives
    assert "end_on_distinct_frame" in plan.quality_directives
    assert "ensure_visible_motion_stage" in plan.quality_directives
    assert "use_mathex_for_symbolic_labels" in plan.quality_directives
    assert "avoid_backstroke_width_keyword" in plan.quality_directives


def test_build_scene_plan_routes_wave_prompt_to_graph_profile() -> None:
    plan = build_scene_plan(
        prompt="show a sine wave and clearly label its amplitude and period with readable callouts",
        output_profile={"quality_preset": "production"},
        style_hints={},
    )

    assert plan.scene_class == "MovingCameraScene"
    assert plan.camera_strategy == "auto_zoom"
    assert plan.transition_style == "lagged"
    assert "LaggedStart" in plan.animation_recipes
    assert "AnimationGroup" in plan.animation_recipes
    assert plan.sections[0].name == "setup"
    assert plan.sections[1].name == "focus"
    assert "avoid_nonexistent_axis_label_getters" in plan.quality_directives
    assert "avoid_nonexistent_graph_area_getters" in plan.quality_directives
    assert "ensure_visible_motion_stage" in plan.quality_directives


def test_build_scene_plan_adds_geometry_api_safety_for_triangle_prompts() -> None:
    plan = build_scene_plan(
        prompt="show a right triangle with legs labeled a and b and highlight the hypotenuse c",
        output_profile={"quality_preset": "production"},
        style_hints={"tone": "teaching"},
    )

    assert plan.scene_class == "MovingCameraScene"
    assert "avoid_diagonal_corner_getters" in plan.quality_directives
