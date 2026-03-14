from __future__ import annotations

import ast
import re

from video_agent.domain.enums import ValidationDecision
from video_agent.domain.validation_models import ValidationIssue, ValidationReport


class StaticCheckValidator:
    FORBIDDEN_IMPORTS = {"subprocess", "socket", "requests"}
    FORBIDDEN_CALLS = {"eval", "exec"}
    UNSUPPORTED_DIAGONAL_CORNER_GETTERS = frozenset(
        {"get_bottom_right", "get_bottom_left", "get_top_right", "get_top_left"}
    )
    NON_ANIMATION_PLAY_CONSTRUCTORS = frozenset({"SurroundingRectangle"})
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

    def validate(self, code: str) -> ValidationReport:
        issues: list[ValidationIssue] = []
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            issues.append(ValidationIssue(code="syntax_error", message=str(exc)))
            return ValidationReport(decision=ValidationDecision.FAIL, passed=False, issues=issues)

        has_scene = False
        unsafe_tex_fragment_aliases = self._bare_tex_fragment_aliases(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_name = alias.name.split(".")[0]
                    if root_name in self.FORBIDDEN_IMPORTS:
                        issues.append(
                            ValidationIssue(code="forbidden_import", message=f"Forbidden import: {root_name}")
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in self.FORBIDDEN_IMPORTS:
                    issues.append(
                        ValidationIssue(code="forbidden_import", message=f"Forbidden import: {node.module}")
                    )
            elif isinstance(node, ast.Call):
                func_name = self._call_name(node.func)
                if func_name in self.FORBIDDEN_CALLS:
                    issues.append(ValidationIssue(code="forbidden_call", message=f"Forbidden call: {func_name}"))
                if func_name == "TransformMatchingTex" and node.args and self._contains_numeric_subscript(node.args[0]):
                    issues.append(
                        ValidationIssue(
                            code="unsafe_transformmatchingtex_slice",
                            message=(
                                "TransformMatchingTex source should not be built from numeric subscript or slice "
                                "access. Prefer full MathTex expressions or symbolic tex selection helpers."
                            ),
                        )
                    )
                if func_name == "play":
                    issues.extend(self._non_animation_play_argument_issues(node))
                if func_name == "Tex" and any(
                    self._looks_like_math_tex_label(value) for value in self._string_literal_args(node)
                ):
                    issues.append(
                        ValidationIssue(
                            code="tex_math_label",
                            message=(
                                "Tex is being used with symbolic math content. Prefer MathTex for pi/fraction/"
                                "superscript/subscript labels."
                            ),
                        )
                    )
                if func_name == "set_backstroke" and any(keyword.arg == "width" for keyword in node.keywords):
                    issues.append(
                        ValidationIssue(
                            code="set_backstroke_width_keyword",
                            message="set_backstroke does not accept width=... here. Use stroke_width=... or omit it.",
                        )
                    )
                if func_name == "SurroundingRectangle" and self._uses_bare_tex_control_sequence(node):
                    issues.append(
                        ValidationIssue(
                            code="unsafe_bare_tex_highlight",
                            message=(
                                "SurroundingRectangle is targeting a bare TeX control sequence. Highlight a full "
                                "rendered term instead."
                            ),
                        )
                    )
                if func_name == "get_part_by_tex" and self._uses_bare_tex_control_sequence_selector(node):
                    issues.append(
                        ValidationIssue(
                            code="unsafe_bare_tex_selection",
                            message=(
                                "Do not call get_part_by_tex on a bare TeX control sequence such as \\sqrt. "
                                "Select or isolate a full rendered term instead."
                            ),
                        )
                    )
                if func_name == "get_area_under_graph":
                    issues.append(
                        ValidationIssue(
                            code="nonexistent_graph_area_getter",
                            message=(
                                "'get_area_under_graph' is not a valid Axes API. Use `axes.get_area(...)` or "
                                "another supported graph-area helper instead."
                            ),
                        )
                    )
                if func_name in self.UNSUPPORTED_DIAGONAL_CORNER_GETTERS:
                    issues.append(
                        ValidationIssue(
                            code="unsupported_diagonal_corner_getter",
                            message=(
                                f"'{func_name}()' is a brittle diagonal corner getter. Use `get_corner(...)` with "
                                "a direction constant like `DR`/`UL` or explicit vertices instead."
                            ),
                        )
                    )
                if (
                    func_name == "SurroundingRectangle"
                    and node.args
                    and isinstance(node.args[0], ast.Name)
                    and node.args[0].id in unsafe_tex_fragment_aliases
                ):
                    issues.append(
                        ValidationIssue(
                            code="unsafe_bare_tex_highlight",
                            message=(
                                "SurroundingRectangle is targeting a bare TeX control sequence via an alias. "
                                "Highlight a full rendered term instead."
                            ),
                        )
                    )
                if func_name in {"get_x_axis_labels", "get_y_axis_labels"}:
                    issues.append(
                        ValidationIssue(
                            code="nonexistent_axis_label_getter",
                            message=(
                                f"'{func_name}' is not a valid Axes API. Use add_labels(...), get_axis_labels(...), "
                                "or the singular axis-label helpers instead."
                            ),
                        )
                    )
            elif isinstance(node, ast.ClassDef):
                base_names = [self._base_name(base) for base in node.bases]
                if any(name.endswith("Scene") for name in base_names if name):
                    has_scene = True

        if not has_scene:
            issues.append(ValidationIssue(code="missing_scene", message="Script must define a Scene subclass"))

        passed = len(issues) == 0
        return ValidationReport(
            decision=ValidationDecision.PASS if passed else ValidationDecision.FAIL,
            passed=passed,
            issues=issues,
        )

    @staticmethod
    def _base_name(node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    @classmethod
    def _call_name(cls, node: ast.AST) -> str | None:
        return cls._base_name(node) if isinstance(node, ast.expr) else None

    @classmethod
    def _contains_numeric_subscript(cls, node: ast.AST) -> bool:
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "copy" and not node.args and not node.keywords:
                return cls._contains_numeric_subscript(node.func.value)
            return False

        if isinstance(node, ast.Subscript):
            if cls._is_numeric_subscript_slice(node.slice):
                return True
            return cls._contains_numeric_subscript(node.value)

        if isinstance(node, ast.Attribute):
            return cls._contains_numeric_subscript(node.value)

        return False

    @staticmethod
    def _is_numeric_subscript_slice(node: ast.AST) -> bool:
        if isinstance(node, ast.Slice):
            return True
        if isinstance(node, ast.Constant):
            return isinstance(node.value, int)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return isinstance(node.operand, ast.Constant) and isinstance(node.operand.value, int)
        return False

    @classmethod
    def _non_animation_play_argument_issues(cls, node: ast.Call) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for arg in node.args:
            if not isinstance(arg, ast.Call):
                continue
            if cls._contains_animate_attribute(arg):
                continue

            call_name = cls._call_name(arg.func)
            if isinstance(arg.func, ast.Attribute):
                if not cls._is_plain_mobject_method(call_name):
                    continue
            elif call_name not in cls.NON_ANIMATION_PLAY_CONSTRUCTORS:
                continue

            issues.append(
                ValidationIssue(
                    code="non_animation_play_argument",
                    message=(
                        f"self.play received '{call_name}(...)', which looks like a plain mobject operation rather "
                        "than an animation. Wrap it in an animation or use the .animate interface."
                    ),
                )
            )
        return issues

    @classmethod
    def _contains_animate_attribute(cls, node: ast.AST) -> bool:
        if isinstance(node, ast.Attribute):
            return node.attr == "animate" or cls._contains_animate_attribute(node.value)
        if isinstance(node, ast.Call):
            return cls._contains_animate_attribute(node.func)
        if isinstance(node, ast.Subscript):
            return cls._contains_animate_attribute(node.value)
        return False

    @classmethod
    def _is_plain_mobject_method(cls, call_name: str | None) -> bool:
        if call_name is None:
            return False
        return call_name.startswith("set_") or call_name in cls.SUSPICIOUS_PLAY_METHODS

    @staticmethod
    def _string_literal_args(node: ast.Call) -> list[str]:
        values: list[str] = []
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                values.append(arg.value)
        return values

    @classmethod
    def _looks_like_math_tex_label(cls, value: str) -> bool:
        return bool(cls.MATH_TEX_PATTERN.search(value))

    @classmethod
    def _uses_bare_tex_control_sequence(cls, node: ast.Call) -> bool:
        if not node.args:
            return False
        target = node.args[0]
        if not isinstance(target, ast.Call):
            return False
        if not isinstance(target.func, ast.Attribute) or target.func.attr != "get_part_by_tex":
            return False

        for arg in target.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return bool(cls.BARE_TEX_CONTROL_SEQUENCE_PATTERN.fullmatch(arg.value))
        return False

    @classmethod
    def _uses_bare_tex_control_sequence_selector(cls, node: ast.Call) -> bool:
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return bool(cls.BARE_TEX_CONTROL_SEQUENCE_PATTERN.fullmatch(arg.value))
        return False

    @classmethod
    def _bare_tex_fragment_aliases(cls, tree: ast.AST) -> set[str]:
        aliases: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            if cls._extract_bare_tex_fragment(node.value) is None:
                continue
            aliases.add(target.id)
        return aliases

    @classmethod
    def _extract_bare_tex_fragment(cls, node: ast.AST) -> str | None:
        if not isinstance(node, ast.Call):
            return None
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "get_part_by_tex":
            return None

        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if cls.BARE_TEX_CONTROL_SEQUENCE_PATTERN.fullmatch(arg.value):
                    return arg.value
        return None
