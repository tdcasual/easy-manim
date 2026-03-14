from __future__ import annotations

import ast
import re

from pydantic import BaseModel, Field


UNSUPPORTED_HELPER_KWARGS: dict[str, frozenset[str]] = {
    "get_v_line": frozenset({"color", "opacity", "fill_opacity", "stroke_opacity"}),
    "get_h_line": frozenset({"color", "opacity", "fill_opacity", "stroke_opacity"}),
}
COORDINATE_HELPERS = frozenset({"c2p", "coords_to_point", "point_from_proportion"})
SUSPICIOUS_PLAY_METHODS = frozenset(
    {
        "align_to",
        "arrange",
        "arrange_in_grid",
        "flip",
        "move_to",
        "next_to",
        "rotate",
        "scale",
        "shift",
        "stretch",
        "stretch_to_fit_height",
        "stretch_to_fit_width",
        "to_corner",
        "to_edge",
    }
)
MATH_TEX_PATTERN = re.compile(
    r"(\\(?:alpha|beta|cdot|cos|frac|gamma|geq|infty|int|leq|ln|log|neq|pi|pm|right|sin|sqrt|sum|tan|theta|times|to))|[_^]"
)
BARE_TEX_CONTROL_SEQUENCE_PATTERN = re.compile(r"^\\+[A-Za-z]+$")
UNSUPPORTED_DIAGONAL_CORNER_GETTERS = frozenset(
    {"get_bottom_right", "get_bottom_left", "get_top_right", "get_top_left"}
)
NON_ANIMATION_PLAY_CONSTRUCTORS = frozenset({"SurroundingRectangle"})


class ScriptDiagnostic(BaseModel):
    code: str
    message: str
    line: int | None = None
    call_name: str | None = None
    helper_name: str | None = None
    keywords: list[str] = Field(default_factory=list)


def collect_script_diagnostics(script_text: str) -> list[ScriptDiagnostic]:
    try:
        tree = ast.parse(script_text)
    except SyntaxError:
        return []

    diagnostics: list[ScriptDiagnostic] = []
    has_scene_subclass = False
    unsafe_tex_fragment_aliases = _bare_tex_fragment_aliases(tree)

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and _is_scene_subclass(node):
            has_scene_subclass = True
            continue
        if not isinstance(node, ast.Call):
            continue

        if unsupported_helper_diagnostic := _unsupported_helper_kwargs_diagnostic(node):
            diagnostics.append(unsupported_helper_diagnostic)
        if coordinate_method_diagnostic := _coordinate_object_method_call_diagnostic(node):
            diagnostics.append(coordinate_method_diagnostic)
        if unsafe_transform_diagnostic := _unsafe_transformmatchingtex_slice_diagnostic(node):
            diagnostics.append(unsafe_transform_diagnostic)
        if non_animation_play_diagnostic := _non_animation_play_argument_diagnostic(node):
            diagnostics.append(non_animation_play_diagnostic)
        if tex_math_label_diagnostic := _tex_math_label_diagnostic(node):
            diagnostics.append(tex_math_label_diagnostic)
        if set_backstroke_diagnostic := _set_backstroke_width_keyword_diagnostic(node):
            diagnostics.append(set_backstroke_diagnostic)
        if bare_tex_highlight_diagnostic := _unsafe_bare_tex_highlight_diagnostic(node, unsafe_tex_fragment_aliases):
            diagnostics.append(bare_tex_highlight_diagnostic)
        if bare_tex_selection_diagnostic := _unsafe_bare_tex_selection_diagnostic(node):
            diagnostics.append(bare_tex_selection_diagnostic)
        if nonexistent_axis_label_diagnostic := _nonexistent_axis_label_getter_diagnostic(node):
            diagnostics.append(nonexistent_axis_label_diagnostic)
        if nonexistent_graph_area_diagnostic := _nonexistent_graph_area_getter_diagnostic(node):
            diagnostics.append(nonexistent_graph_area_diagnostic)
        if diagonal_corner_diagnostic := _unsupported_diagonal_corner_getter_diagnostic(node):
            diagnostics.append(diagonal_corner_diagnostic)

    if not has_scene_subclass:
        diagnostics.append(
            ScriptDiagnostic(
                code="missing_scene_subclass",
                message="Script is missing a Scene subclass with a construct() method.",
            )
        )

    return _dedupe_diagnostics(diagnostics)


def _is_scene_subclass(node: ast.ClassDef) -> bool:
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id.endswith("Scene"):
            return True
        if isinstance(base, ast.Attribute) and base.attr.endswith("Scene"):
            return True
    return False


def _unsupported_helper_kwargs_diagnostic(node: ast.Call) -> ScriptDiagnostic | None:
    call_name = _call_name(node.func)
    if call_name not in UNSUPPORTED_HELPER_KWARGS:
        return None

    blocked_keywords = UNSUPPORTED_HELPER_KWARGS[call_name]
    keywords = [keyword.arg for keyword in node.keywords if keyword.arg in blocked_keywords]
    if not keywords:
        return None

    return ScriptDiagnostic(
        code="unsupported_helper_kwargs",
        message=(
            f"Helper '{call_name}' may not accept style keywords directly. "
            f"Revise the helper usage or style the returned mobject after creation."
        ),
        line=getattr(node, "lineno", None),
        call_name=call_name,
        keywords=keywords,
    )


def _coordinate_object_method_call_diagnostic(node: ast.Call) -> ScriptDiagnostic | None:
    if not isinstance(node.func, ast.Attribute):
        return None
    if not isinstance(node.func.value, ast.Call):
        return None

    helper_name = _call_name(node.func.value.func)
    if helper_name not in COORDINATE_HELPERS:
        return None

    call_name = node.func.attr
    return ScriptDiagnostic(
        code="coordinate_object_method_call",
        message=(
            f"Helper '{helper_name}' likely returns coordinates, so calling '{call_name}' on the result is suspicious."
        ),
        line=getattr(node, "lineno", None),
        call_name=call_name,
        helper_name=helper_name,
    )


def _unsafe_transformmatchingtex_slice_diagnostic(node: ast.Call) -> ScriptDiagnostic | None:
    if _call_name(node.func) != "TransformMatchingTex" or not node.args:
        return None
    if not _contains_numeric_subscript(node.args[0]):
        return None

    return ScriptDiagnostic(
        code="unsafe_transformmatchingtex_slice",
        message=(
            "TransformMatchingTex is using a numerically indexed tex slice as its source. "
            "Prefer full MathTex expressions or symbolic tex selection helpers."
        ),
        line=getattr(node, "lineno", None),
        call_name="TransformMatchingTex",
    )


def _non_animation_play_argument_diagnostic(node: ast.Call) -> ScriptDiagnostic | None:
    if _call_name(node.func) != "play":
        return None

    for arg in node.args:
        if not isinstance(arg, ast.Call):
            continue
        if _contains_animate_attribute(arg):
            continue

        call_name = _call_name(arg.func)
        if isinstance(arg.func, ast.Attribute):
            if not _is_plain_mobject_method(call_name):
                continue
        elif call_name not in NON_ANIMATION_PLAY_CONSTRUCTORS:
            continue

        return ScriptDiagnostic(
            code="non_animation_play_argument",
            message=(
                f"self.play received '{call_name}(...)', which looks like a plain mobject operation rather than "
                "an animation. Wrap it in an animation or use the .animate interface."
            ),
            line=getattr(arg, "lineno", None),
            call_name=call_name,
        )

    return None


def _tex_math_label_diagnostic(node: ast.Call) -> ScriptDiagnostic | None:
    if _call_name(node.func) != "Tex":
        return None

    if not any(_looks_like_math_tex_label(value) for value in _string_literal_args(node)):
        return None

    return ScriptDiagnostic(
        code="tex_math_label",
        message=(
            "Tex is being used with symbolic math content. Prefer MathTex for pi/fraction/superscript/subscript labels."
        ),
        line=getattr(node, "lineno", None),
        call_name="Tex",
    )


def _set_backstroke_width_keyword_diagnostic(node: ast.Call) -> ScriptDiagnostic | None:
    if _call_name(node.func) != "set_backstroke":
        return None

    keywords = [keyword.arg for keyword in node.keywords if keyword.arg == "width"]
    if not keywords:
        return None

    return ScriptDiagnostic(
        code="set_backstroke_width_keyword",
        message="set_backstroke does not accept width=... here. Use stroke_width=... or omit the keyword.",
        line=getattr(node, "lineno", None),
        call_name="set_backstroke",
        keywords=keywords,
    )


def _unsafe_bare_tex_highlight_diagnostic(
    node: ast.Call, unsafe_tex_fragment_aliases: set[str]
) -> ScriptDiagnostic | None:
    if _call_name(node.func) != "SurroundingRectangle" or not node.args:
        return None

    target = node.args[0]
    if not _is_unsafe_bare_tex_target(target, unsafe_tex_fragment_aliases):
        return None

    return ScriptDiagnostic(
        code="unsafe_bare_tex_highlight",
        message=(
            "SurroundingRectangle is targeting a bare TeX control sequence. Highlight a full rendered term instead."
        ),
        line=getattr(node, "lineno", None),
        call_name="SurroundingRectangle",
    )


def _nonexistent_axis_label_getter_diagnostic(node: ast.Call) -> ScriptDiagnostic | None:
    call_name = _call_name(node.func)
    if call_name not in {"get_x_axis_labels", "get_y_axis_labels"}:
        return None

    return ScriptDiagnostic(
        code="nonexistent_axis_label_getter",
        message=(
            f"'{call_name}' is not a valid Axes API. Use add_labels(...), get_axis_labels(...), "
            "or the singular axis-label helpers instead."
        ),
        line=getattr(node, "lineno", None),
        call_name=call_name,
    )


def _nonexistent_graph_area_getter_diagnostic(node: ast.Call) -> ScriptDiagnostic | None:
    call_name = _call_name(node.func)
    if call_name != "get_area_under_graph":
        return None

    return ScriptDiagnostic(
        code="nonexistent_graph_area_getter",
        message=(
            "'get_area_under_graph' is not a valid Axes API. Use `axes.get_area(...)` or another supported "
            "graph-area helper instead."
        ),
        line=getattr(node, "lineno", None),
        call_name=call_name,
    )


def _unsafe_bare_tex_selection_diagnostic(node: ast.Call) -> ScriptDiagnostic | None:
    if _call_name(node.func) != "get_part_by_tex":
        return None

    tex_fragment = _first_string_literal_arg(node)
    if tex_fragment is None or not BARE_TEX_CONTROL_SEQUENCE_PATTERN.fullmatch(tex_fragment):
        return None

    return ScriptDiagnostic(
        code="unsafe_bare_tex_selection",
        message=(
            "Do not call get_part_by_tex on a bare TeX control sequence such as \\sqrt. "
            "Select or isolate a full rendered term instead."
        ),
        line=getattr(node, "lineno", None),
        call_name="get_part_by_tex",
    )


def _unsupported_diagonal_corner_getter_diagnostic(node: ast.Call) -> ScriptDiagnostic | None:
    call_name = _call_name(node.func)
    if call_name not in UNSUPPORTED_DIAGONAL_CORNER_GETTERS:
        return None

    return ScriptDiagnostic(
        code="unsupported_diagonal_corner_getter",
        message=(
            f"'{call_name}()' is a brittle diagonal corner getter. Use `get_corner(...)` with a direction "
            "constant like `DR`/`UL` or explicit vertices instead."
        ),
        line=getattr(node, "lineno", None),
        call_name=call_name,
    )


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _contains_numeric_subscript(node: ast.AST) -> bool:
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute) and node.func.attr == "copy" and not node.args and not node.keywords:
            return _contains_numeric_subscript(node.func.value)
        return False

    if isinstance(node, ast.Subscript):
        if _is_numeric_subscript_slice(node.slice):
            return True
        return _contains_numeric_subscript(node.value)

    if isinstance(node, ast.Attribute):
        return _contains_numeric_subscript(node.value)

    return False


def _is_numeric_subscript_slice(node: ast.AST) -> bool:
    if isinstance(node, ast.Slice):
        return True
    if isinstance(node, ast.Constant):
        return isinstance(node.value, int)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        return isinstance(node.operand, ast.Constant) and isinstance(node.operand.value, int)
    return False


def _contains_animate_attribute(node: ast.AST) -> bool:
    if isinstance(node, ast.Attribute):
        return node.attr == "animate" or _contains_animate_attribute(node.value)
    if isinstance(node, ast.Call):
        return _contains_animate_attribute(node.func)
    if isinstance(node, ast.Subscript):
        return _contains_animate_attribute(node.value)
    return False


def _is_plain_mobject_method(call_name: str | None) -> bool:
    if call_name is None:
        return False
    return call_name.startswith("set_") or call_name in SUSPICIOUS_PLAY_METHODS


def _string_literal_args(node: ast.Call) -> list[str]:
    values: list[str] = []
    for arg in node.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            values.append(arg.value)
    return values


def _first_string_literal_arg(node: ast.Call) -> str | None:
    for arg in node.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
    return None


def _looks_like_math_tex_label(value: str) -> bool:
    return bool(MATH_TEX_PATTERN.search(value))


def _bare_tex_fragment_aliases(tree: ast.AST) -> set[str]:
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        if _extract_bare_tex_fragment(node.value) is None:
            continue
        aliases.add(target.id)
    return aliases


def _is_unsafe_bare_tex_target(node: ast.AST, unsafe_tex_fragment_aliases: set[str]) -> bool:
    if _extract_bare_tex_fragment(node) is not None:
        return True
    return isinstance(node, ast.Name) and node.id in unsafe_tex_fragment_aliases


def _extract_bare_tex_fragment(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    if not isinstance(node.func, ast.Attribute) or node.func.attr != "get_part_by_tex":
        return None

    tex_fragment = _first_string_literal_arg(node)
    if tex_fragment is None or not BARE_TEX_CONTROL_SEQUENCE_PATTERN.fullmatch(tex_fragment):
        return None
    return tex_fragment


def _dedupe_diagnostics(diagnostics: list[ScriptDiagnostic]) -> list[ScriptDiagnostic]:
    seen: set[tuple[str, int | None, str | None, str | None, tuple[str, ...]]] = set()
    unique: list[ScriptDiagnostic] = []
    for item in diagnostics:
        marker = (
            item.code,
            item.line,
            item.call_name,
            item.helper_name,
            tuple(item.keywords),
        )
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(item)
    return unique
