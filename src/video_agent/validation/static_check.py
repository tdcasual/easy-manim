from __future__ import annotations

import ast

from video_agent.domain.enums import ValidationDecision
from video_agent.domain.validation_models import ValidationIssue, ValidationReport


class StaticCheckValidator:
    FORBIDDEN_IMPORTS = {"subprocess", "socket", "requests"}
    FORBIDDEN_CALLS = {"eval", "exec"}

    def validate(self, code: str) -> ValidationReport:
        issues: list[ValidationIssue] = []
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            issues.append(ValidationIssue(code="syntax_error", message=str(exc)))
            return ValidationReport(decision=ValidationDecision.FAIL, passed=False, issues=issues)

        has_scene = False
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
                func_name = getattr(node.func, "id", None)
                if func_name in self.FORBIDDEN_CALLS:
                    issues.append(ValidationIssue(code="forbidden_call", message=f"Forbidden call: {func_name}"))
            elif isinstance(node, ast.ClassDef):
                base_names = [getattr(base, "id", None) for base in node.bases]
                if "Scene" in base_names:
                    has_scene = True

        if not has_scene:
            issues.append(ValidationIssue(code="missing_scene", message="Script must define a Scene subclass"))

        passed = len(issues) == 0
        return ValidationReport(
            decision=ValidationDecision.PASS if passed else ValidationDecision.FAIL,
            passed=passed,
            issues=issues,
        )
