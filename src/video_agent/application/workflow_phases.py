from __future__ import annotations

from video_agent.domain.enums import TaskPhase, TaskStatus, ValidationDecision
from video_agent.domain.validation_models import ValidationIssue, ValidationReport


def provider_failure_report(code: str, summary: str, message: str) -> ValidationReport:
    return ValidationReport(
        decision=ValidationDecision.FAIL,
        passed=False,
        issues=[ValidationIssue(code=code, message=message)],
        summary=summary,
    )


def latex_dependency_report(message: str, missing_checks: list[str]) -> ValidationReport:
    return ValidationReport(
        decision=ValidationDecision.FAIL,
        passed=False,
        issues=[
            ValidationIssue(
                code="latex_dependency_missing",
                message=f"{message}: {', '.join(missing_checks)}",
            )
        ],
        summary="Missing LaTeX runtime dependencies",
        details={
            "feature": "mathtex",
            "missing_checks": missing_checks,
        },
    )


def render_failure_report(stderr: str) -> ValidationReport:
    return ValidationReport(
        decision=ValidationDecision.FAIL,
        passed=False,
        issues=[ValidationIssue(code="render_failed", message=stderr or "Render failed")],
        summary="Render failed",
    )


def combined_validation_report(hard_report: ValidationReport, rule_report: ValidationReport) -> ValidationReport:
    issues = [*hard_report.issues, *rule_report.issues]
    passed = hard_report.passed and rule_report.passed
    return ValidationReport(
        decision=ValidationDecision.PASS if passed else ValidationDecision.FAIL,
        passed=passed,
        issues=issues,
        summary="Validation passed" if passed else "Validation failed",
        video_metadata=hard_report.video_metadata,
        details={
            "hard": hard_report.model_dump(mode="json"),
            "rule": rule_report.model_dump(mode="json"),
        },
    )


def terminal_task_state(report: ValidationReport) -> tuple[TaskStatus, TaskPhase]:
    if report.passed:
        return TaskStatus.COMPLETED, TaskPhase.COMPLETED
    return TaskStatus.FAILED, TaskPhase.FAILED
