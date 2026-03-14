from __future__ import annotations

from typing import Any, Optional

from video_agent.application.scene_plan import ScenePlan



def build_generation_prompt(
    prompt: str,
    output_profile: dict[str, Any] | None = None,
    feedback: Optional[str] = None,
    style_hints: dict[str, Any] | None = None,
    scene_plan: ScenePlan | None = None,
) -> str:
    lines = ["Generate a runnable Manim script.", f"User request: {prompt}"]
    if output_profile:
        lines.append(f"Output profile: {output_profile}")
    if style_hints:
        lines.append(f"Style hints: {style_hints}")
    if scene_plan:
        lines.append(f"Scene class: {scene_plan.scene_class}")
        lines.append(f"Camera strategy: {scene_plan.camera_strategy}")
        lines.append(f"Pacing strategy: {scene_plan.pacing_strategy}")
        lines.append(f"Transition style: {scene_plan.transition_style}")
        lines.append(f"Formula strategy: {scene_plan.formula_strategy}")
        lines.append(f"Animation recipes: {scene_plan.animation_recipes}")
        lines.append(f"Quality directives: {scene_plan.quality_directives}")
        expanded_quality_instructions = _expand_quality_directives(scene_plan.quality_directives)
        if expanded_quality_instructions:
            lines.append("Quality requirements:")
            lines.extend(f"- {instruction}" for instruction in expanded_quality_instructions)
        lines.append(f"Sections: {[section.model_dump(mode='json') for section in scene_plan.sections]}")
    if feedback:
        lines.append(f"Revision feedback: {feedback}")
    lines.append("Return only Python code.")
    return "\n".join(lines)


def _expand_quality_directives(quality_directives: list[str]) -> list[str]:
    instruction_map = {
        "avoid_blank_opening_frame": "Do not open on an almost empty or partially written frame.",
        "prefer_light_background": (
            'Prefer a light background unless the prompt explicitly asks for a dark scene. '
            'Set `config.background_color = "#F7F4EA"` for light-background scenes. '
            "Use dark foreground colors such as BLACK when you switch to a light background."
        ),
        "favor_readable_spacing": "Keep generous spacing and readable margins so text never feels cramped.",
        "compose_for_single_focus": "Compose each beat around a single focal point instead of competing elements.",
        "favor_clear_labels": "Use explicit labels or titles when they improve clarity.",
        "keep_formula_large_and_centered": "Keep the main formula large, centered, and fully readable on screen.",
        "hold_focus_before_transition": "Hold the highlighted state long enough to read before transitioning away.",
        "one_idea_per_section": "Limit each section to one teaching idea at a time.",
        "ensure_distinct_section_staging": (
            "Ensure each section creates a materially different visual state, not just a minor label change."
        ),
        "end_on_distinct_frame": (
            "End on a frame that is visibly different from the opening frame through layout, camera framing, "
            "highlighted objects, or a takeaway callout."
        ),
        "avoid_numeric_mathtex_slices": (
            "Do not isolate MathTex or Tex content with fixed numeric indices such as "
            "`expr[0][9:18]` or similar slice-based submobject access."
        ),
        "prefer_symbolic_tex_selection": (
            "When selecting part of a formula, prefer symbolic helpers such as "
            "`substrings_to_isolate`, `get_part_by_tex`, `get_parts_by_tex`, or `set_color_by_tex`."
        ),
        "prefer_non_destructive_formula_emphasis": (
            "For formula emphasis, prefer non-destructive highlighting such as `Indicate`, "
            "`SurroundingRectangle`, or `set_color_by_tex` before creating a separate term mobject."
        ),
        "only_transform_matching_full_expressions": (
            "Use `TransformMatchingTex` only between full `MathTex` expressions with compatible tokenization, "
            "not on arbitrary indexed slices of another expression."
        ),
        "relayout_formula_for_recap": (
            "During the recap or takeaway, materially relayout the formula scene. Move the main formula to a new "
            "position such as the upper portion of the frame or one side, then place the takeaway or isolated key "
            "term in a separate area so the final composition is not just the original centered formula plus a small label."
        ),
        "isolate_full_tex_term_before_highlight": (
            "Isolate the full target term before using `SurroundingRectangle` or similar box highlights. Prefer "
            "boxing a full isolated expression such as `\\sqrt{...}` rather than a bare LaTeX control sequence like `\\sqrt`."
        ),
        "avoid_bare_tex_control_sequence_highlights": (
            "Do not highlight a bare TeX control sequence like `\\sqrt`. Select or isolate a full rendered term "
            "before boxing or indicating it."
        ),
        "avoid_bare_tex_control_sequence_selection": (
            "Do not call `get_part_by_tex` with a bare TeX control sequence like `\\sqrt`. Use "
            "`substrings_to_isolate`, `get_parts_by_tex`, or a full rendered term selection instead."
        ),
        "only_pass_animations_to_play": (
            "Pass only animation objects to `self.play`. If you need a style change, use the `.animate` interface "
            "or perform the style mutation before or after `self.play`, not as a plain method call argument. "
            "Wrap plain mobjects like `SurroundingRectangle(...)` in `Create`, `FadeIn`, or another animation."
        ),
        "use_mathex_for_symbolic_labels": (
            "Use `MathTex` for symbolic labels or axis markers containing mathematical notation such as `\\pi`, "
            "fractions, exponents, or subscripts. Reserve `Tex` or `Text` for plain-language labels."
        ),
        "avoid_backstroke_width_keyword": (
            "If you use `set_backstroke`, use `stroke_width=` rather than `width=`. It is also acceptable to omit "
            "backstroke styling entirely when readability is already good."
        ),
        "avoid_nonexistent_axis_label_getters": (
            "Do not call nonexistent helpers such as `axes.get_x_axis_labels` or `axes.get_y_axis_labels`. "
            "Use `add_labels(...)`, `get_axis_labels(...)`, or singular axis-label helpers instead."
        ),
        "avoid_nonexistent_graph_area_getters": (
            "Do not call nonexistent helpers such as `axes.get_area_under_graph`. Prefer supported helpers like "
            "`axes.get_area(...)` when you need to shade graph regions."
        ),
        "avoid_diagonal_corner_getters": (
            "Do not call diagonal corner getters such as `get_bottom_right()` or `get_top_left()`. "
            "Use `get_corner(...)` with a direction like `DR` or explicit vertices instead."
        ),
        "ensure_visible_motion_stage": (
            "Include at least one clearly visible motion beat such as a graph trace, transform, camera move, or "
            "object relocation. Do not rely on a sequence of mostly static fade-ins."
        ),
    }
    return [instruction_map[directive] for directive in quality_directives if directive in instruction_map]
