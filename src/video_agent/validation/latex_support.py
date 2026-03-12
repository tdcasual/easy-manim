from __future__ import annotations

import ast


LATEX_MOBJECT_NAMES = frozenset({"MathTex", "Tex", "SingleStringMathTex"})


def script_uses_latex(script_text: str) -> bool:
    try:
        tree = ast.parse(script_text)
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _call_name(node.func)
        if call_name in LATEX_MOBJECT_NAMES:
            return True
    return False


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None
