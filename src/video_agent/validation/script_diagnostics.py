from __future__ import annotations

import ast

from pydantic import BaseModel, Field


UNSUPPORTED_HELPER_KWARGS: dict[str, frozenset[str]] = {
    "get_v_line": frozenset({"color", "opacity", "fill_opacity", "stroke_opacity"}),
    "get_h_line": frozenset({"color", "opacity", "fill_opacity", "stroke_opacity"}),
}
COORDINATE_HELPERS = frozenset({"c2p", "coords_to_point", "point_from_proportion"})


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
        if isinstance(base, ast.Name) and base.id == "Scene":
            return True
        if isinstance(base, ast.Attribute) and base.attr == "Scene":
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


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


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
