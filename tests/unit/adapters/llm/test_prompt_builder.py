from video_agent.adapters.llm.prompt_builder import build_generation_prompt
from video_agent.application.scene_plan import ScenePlan, ScenePlanSection



def test_prompt_builder_includes_prompt_and_output_profile() -> None:
    prompt = build_generation_prompt(
        prompt="draw a circle",
        output_profile={"width": 1280, "height": 720},
        feedback=None,
    )
    assert "draw a circle" in prompt
    assert "1280" in prompt


def test_prompt_builder_includes_scene_plan_and_style_hints() -> None:
    plan = ScenePlan(
        scene_class="MovingCameraScene",
        formula_strategy="none",
        transition_style="lagged",
        camera_strategy="auto_zoom",
        pacing_strategy="measured",
        animation_recipes=["LaggedStart", "AnimationGroup"],
        quality_directives=[
            "avoid_blank_opening_frame",
            "prefer_light_background",
            "favor_clear_labels",
            "ensure_distinct_section_staging",
            "end_on_distinct_frame",
        ],
        sections=[ScenePlanSection(name="intro", goal="introduce the main shape")],
    )
    prompt = build_generation_prompt(
        prompt="show a labeled axis animation",
        output_profile={"quality_preset": "production"},
        feedback=None,
        style_hints={"tone": "clean"},
        scene_plan=plan,
    )

    assert "MovingCameraScene" in prompt
    assert "auto_zoom" in prompt
    assert "LaggedStart" in prompt
    assert "measured" in prompt
    assert "avoid_blank_opening_frame" in prompt
    assert "Prefer a light background unless the prompt explicitly asks for a dark scene." in prompt
    assert 'Set `config.background_color = "#F7F4EA"` for light-background scenes.' in prompt
    assert "Use dark foreground colors such as BLACK when you switch to a light background." in prompt
    assert "Do not open on an almost empty or partially written frame." in prompt
    assert "Ensure each section creates a materially different visual state" in prompt
    assert "End on a frame that is visibly different from the opening frame" in prompt


def test_prompt_builder_expands_formula_safety_requirements() -> None:
    plan = ScenePlan(
        scene_class="Scene",
        formula_strategy="mathtex_focus",
        transition_style="lagged",
        camera_strategy="static",
        pacing_strategy="measured",
        animation_recipes=["Indicate", "SurroundingRectangle"],
        quality_directives=[
            "avoid_numeric_mathtex_slices",
            "prefer_symbolic_tex_selection",
            "prefer_non_destructive_formula_emphasis",
            "only_transform_matching_full_expressions",
            "relayout_formula_for_recap",
            "isolate_full_tex_term_before_highlight",
            "avoid_bare_tex_control_sequence_highlights",
            "avoid_bare_tex_control_sequence_selection",
            "only_pass_animations_to_play",
            "use_mathex_for_symbolic_labels",
            "ensure_visible_motion_stage",
        ],
        sections=[ScenePlanSection(name="focus", goal="Highlight the discriminant")],
    )

    prompt = build_generation_prompt(
        prompt="show the quadratic formula and focus on the discriminant",
        output_profile={"quality_preset": "production"},
        feedback=None,
        style_hints={"tone": "teaching"},
        scene_plan=plan,
    )

    assert "Do not isolate MathTex or Tex content with fixed numeric indices" in prompt
    assert "`get_part_by_tex`" in prompt
    assert "`set_color_by_tex`" in prompt
    assert "`Indicate`" in prompt
    assert "`SurroundingRectangle`" in prompt
    assert "Use `TransformMatchingTex` only between full `MathTex` expressions" in prompt
    assert "During the recap or takeaway, materially relayout the formula scene" in prompt
    assert "Isolate the full target term before using `SurroundingRectangle`" in prompt
    assert "Do not highlight a bare TeX control sequence like `\\sqrt`" in prompt
    assert "Do not call `get_part_by_tex` with a bare TeX control sequence like `\\sqrt`" in prompt
    assert "Pass only animation objects to `self.play`" in prompt
    assert "Wrap plain mobjects like `SurroundingRectangle(...)` in `Create`, `FadeIn`, or another animation." in prompt
    assert "Use `MathTex` for symbolic labels" in prompt
    assert "Include at least one clearly visible motion beat" in prompt


def test_prompt_builder_expands_graph_api_safety_requirements() -> None:
    plan = ScenePlan(
        scene_class="MovingCameraScene",
        formula_strategy="none",
        transition_style="lagged",
        camera_strategy="auto_zoom",
        pacing_strategy="balanced",
        animation_recipes=["LaggedStart", "AnimationGroup"],
        quality_directives=[
            "use_mathex_for_symbolic_labels",
            "avoid_backstroke_width_keyword",
            "avoid_nonexistent_axis_label_getters",
            "avoid_nonexistent_graph_area_getters",
            "ensure_visible_motion_stage",
        ],
        sections=[ScenePlanSection(name="focus", goal="Label graph features clearly")],
    )

    prompt = build_generation_prompt(
        prompt="show a cosine wave with labeled period markers",
        output_profile={"quality_preset": "production"},
        feedback=None,
        style_hints=None,
        scene_plan=plan,
    )

    assert "Use `MathTex` for symbolic labels" in prompt
    assert "If you use `set_backstroke`, use `stroke_width=`" in prompt
    assert "Do not call nonexistent helpers such as `axes.get_x_axis_labels`" in prompt
    assert "Do not call nonexistent helpers such as `axes.get_area_under_graph`" in prompt
    assert "Include at least one clearly visible motion beat" in prompt


def test_prompt_builder_expands_geometry_api_safety_requirements() -> None:
    plan = ScenePlan(
        scene_class="MovingCameraScene",
        formula_strategy="none",
        transition_style="lagged",
        camera_strategy="auto_zoom",
        pacing_strategy="balanced",
        animation_recipes=["LaggedStart", "AnimationGroup"],
        quality_directives=[
            "avoid_diagonal_corner_getters",
            "ensure_visible_motion_stage",
        ],
        sections=[ScenePlanSection(name="focus", goal="Highlight the hypotenuse clearly")],
    )

    prompt = build_generation_prompt(
        prompt="show a right triangle and highlight the hypotenuse",
        output_profile={"quality_preset": "production"},
        feedback=None,
        style_hints=None,
        scene_plan=plan,
    )

    assert "Do not call diagonal corner getters such as `get_bottom_right()`" in prompt
    assert "Use `get_corner(...)` with a direction like `DR` or explicit vertices instead." in prompt


def test_prompt_builder_includes_session_memory_context_when_present() -> None:
    prompt = build_generation_prompt(
        prompt="draw a circle",
        output_profile={"quality_preset": "production"},
        feedback="add labels",
        style_hints={"tone": "teaching"},
        memory_context_summary="Recent attempts succeeded with a light background and failed on blank openings.",
    )

    assert "Session memory context:" in prompt
    assert "failed on blank openings" in prompt


def test_prompt_builder_includes_persistent_memory_context_when_present() -> None:
    prompt = build_generation_prompt(
        prompt="draw a circle",
        output_profile={"quality_preset": "production"},
        feedback="add labels",
        persistent_memory_context="Always prefer a warm light background and explicit labels.",
    )

    assert "Persistent memory context:" in prompt
    assert "warm light background" in prompt
