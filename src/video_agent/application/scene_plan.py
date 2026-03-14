from __future__ import annotations

from pydantic import BaseModel, Field


class ScenePlanSection(BaseModel):
    name: str
    goal: str


class ScenePlan(BaseModel):
    scene_class: str = "Scene"
    formula_strategy: str = "none"
    transition_style: str = "succession"
    camera_strategy: str = "static"
    pacing_strategy: str = "balanced"
    animation_recipes: list[str] = Field(default_factory=list)
    quality_directives: list[str] = Field(default_factory=list)
    sections: list[ScenePlanSection] = Field(default_factory=list)


def build_scene_plan(
    prompt: str,
    output_profile: dict[str, object] | None = None,
    style_hints: dict[str, object] | None = None,
) -> ScenePlan:
    text = prompt.lower()
    output_profile = output_profile or {}
    style_hints = style_hints or {}
    plan = ScenePlan(sections=[ScenePlanSection(name="main", goal=prompt)])
    quality_preset = _as_text(output_profile.get("quality_preset")) or "development"
    pace_hint = _as_text(style_hints.get("pace"))
    tone_hint = _as_text(style_hints.get("tone"))
    graph_keywords = (
        "axis",
        "graph",
        "coordinate",
        "point",
        "wave",
        "sine",
        "cosine",
        "function",
        "parabola",
        "vertex",
        "amplitude",
        "period",
    )
    geometry_keywords = ("triangle", "square", "circle", "polygon", "hypotenuse", "leg")

    if any(keyword in text for keyword in ("formula", "mathtex", "equation")):
        plan.formula_strategy = "mathtex_focus"
        plan.animation_recipes.extend(["Indicate", "SurroundingRectangle"])
        plan.quality_directives.extend(
            [
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
            ]
        )
        plan.sections = [
            ScenePlanSection(name="setup", goal="Introduce the formula clearly"),
            ScenePlanSection(name="focus", goal="Highlight the key term or discriminant"),
            ScenePlanSection(name="recap", goal="Restate the main takeaway"),
        ]

    if any(keyword in text for keyword in ("highlight", "focus", "zoom")) or any(
        keyword in text for keyword in graph_keywords
    ):
        plan.scene_class = "MovingCameraScene"
        plan.camera_strategy = "auto_zoom"

    if any(keyword in text for keyword in graph_keywords):
        plan.transition_style = "lagged"
        plan.animation_recipes.extend(["LaggedStart", "AnimationGroup"])
        plan.quality_directives.extend(
            [
                "use_mathex_for_symbolic_labels",
                "avoid_backstroke_width_keyword",
                "avoid_nonexistent_axis_label_getters",
                "avoid_nonexistent_graph_area_getters",
            ]
        )
        if len(plan.sections) == 1 and plan.sections[0].name == "main":
            plan.sections = [
                ScenePlanSection(name="setup", goal="Establish the coordinate context"),
                ScenePlanSection(name="focus", goal=prompt),
            ]

    if any(keyword in text for keyword in geometry_keywords):
        plan.quality_directives.append("avoid_diagonal_corner_getters")

    if pace_hint in {"steady", "slow", "deliberate"}:
        plan.pacing_strategy = "measured"
        plan.transition_style = "lagged"
    elif pace_hint in {"brisk", "fast", "snappy", "quick"}:
        plan.pacing_strategy = "brisk"
        plan.transition_style = "succession"

    camera_hint = _as_text(style_hints.get("camera"))
    if camera_hint in {"static", "locked"}:
        plan.scene_class = "Scene"
        plan.camera_strategy = "static"
    elif camera_hint in {"auto_zoom", "dynamic", "follow", "moving"}:
        plan.scene_class = "MovingCameraScene"
        plan.camera_strategy = "auto_zoom"

    if quality_preset in {"preview", "production"}:
        plan.animation_recipes.append("FadeIn")
        plan.quality_directives.extend(
            [
                "avoid_blank_opening_frame",
                "prefer_light_background",
                "ensure_distinct_section_staging",
                "end_on_distinct_frame",
                "ensure_visible_motion_stage",
            ]
        )
    if quality_preset == "production":
        plan.quality_directives.extend(["favor_readable_spacing", "compose_for_single_focus"])
    if tone_hint in {"clean", "teaching", "educational"}:
        plan.quality_directives.append("favor_clear_labels")
    if tone_hint in {"teaching", "educational"}:
        plan.quality_directives.append("one_idea_per_section")
    if plan.formula_strategy == "mathtex_focus":
        plan.quality_directives.append("keep_formula_large_and_centered")
    if any(keyword in text for keyword in ("highlight", "focus", "discriminant")):
        plan.quality_directives.append("hold_focus_before_transition")

    plan.animation_recipes = list(dict.fromkeys(plan.animation_recipes))
    plan.quality_directives = list(dict.fromkeys(plan.quality_directives))
    return plan


def _as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()
