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


def combined_validation_report(
    hard_report: ValidationReport,
    rule_report: ValidationReport,
    preview_report: ValidationReport | None = None,
) -> ValidationReport:
    reports = [hard_report, rule_report]
    if preview_report is not None:
        reports.append(preview_report)
    issues = [issue for report in reports for issue in report.issues]
    passed = all(report.passed for report in reports)
    details = {
        "hard": hard_report.model_dump(mode="json"),
        "rule": rule_report.model_dump(mode="json"),
    }
    if preview_report is not None:
        details["preview"] = preview_report.model_dump(mode="json")
    return ValidationReport(
        decision=ValidationDecision.PASS if passed else ValidationDecision.FAIL,
        passed=passed,
        issues=issues,
        summary="Validation passed" if passed else "Validation failed",
        video_metadata=hard_report.video_metadata,
        details=details,
    )


def terminal_task_state(report: ValidationReport) -> tuple[TaskStatus, TaskPhase]:
    if report.passed:
        return TaskStatus.COMPLETED, TaskPhase.COMPLETED
    return TaskStatus.FAILED, TaskPhase.FAILED
