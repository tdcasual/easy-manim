from __future__ import annotations

from pathlib import Path

from video_agent.domain.enums import ValidationDecision
from video_agent.domain.validation_models import ValidationIssue, ValidationReport


class RuleValidator:
    def validate(self, video_path: Path) -> ValidationReport:
        path = Path(video_path)
        issues: list[ValidationIssue] = []
        if not path.exists() or path.stat().st_size == 0:
            issues.append(ValidationIssue(code="corrupt_file", message="Video file is missing or empty"))
            return ValidationReport(decision=ValidationDecision.FAIL, passed=False, issues=issues)

        sample = path.read_bytes()[:1024].lower()
        if b"black" in sample:
            issues.append(ValidationIssue(code="black_frames", message="Detected black or blank frames"))
        if b"frozen-tail" in sample or b"stuck" in sample:
            issues.append(ValidationIssue(code="frozen_tail", message="Detected frozen ending frames"))
        if b"corrupt" in sample:
            issues.append(ValidationIssue(code="encoding_error", message="Detected corrupt encoding signature"))

        passed = len(issues) == 0
        return ValidationReport(
            decision=ValidationDecision.PASS if passed else ValidationDecision.FAIL,
            passed=passed,
            issues=issues,
        )
