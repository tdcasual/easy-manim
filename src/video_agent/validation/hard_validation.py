from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from video_agent.domain.enums import ValidationDecision
from video_agent.domain.validation_models import ValidationIssue, ValidationReport, VideoMetadata


class HardValidator:
    def __init__(self, command: str = "ffprobe") -> None:
        self.command = command

    def validate(self, video_path: Path, profile: dict[str, Any] | None = None) -> ValidationReport:
        issues: list[ValidationIssue] = []
        effective_profile = profile or {}
        path = Path(video_path)
        if not path.exists():
            issues.append(ValidationIssue(code="missing_output", message="Video file does not exist"))
            return ValidationReport(decision=ValidationDecision.FAIL, passed=False, issues=issues)

        completed = subprocess.run(
            [
                self.command,
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type,width,height",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            issues.append(ValidationIssue(code="probe_failed", message=completed.stderr or "ffprobe failed"))
            return ValidationReport(decision=ValidationDecision.FAIL, passed=False, issues=issues)

        payload = json.loads(completed.stdout or "{}")
        video_stream = next((stream for stream in payload.get("streams", []) if stream.get("codec_type") == "video"), {})
        metadata = VideoMetadata(
            width=int(video_stream.get("width") or 0),
            height=int(video_stream.get("height") or 0),
            duration_seconds=float(payload.get("format", {}).get("duration") or 0.0),
        )

        if metadata.width <= 0 or metadata.height <= 0:
            issues.append(ValidationIssue(code="invalid_dimensions", message="Video dimensions must be positive"))
        if metadata.duration_seconds <= 0:
            issues.append(ValidationIssue(code="invalid_duration", message="Video duration must be positive"))
        min_width = effective_profile.get("min_width")
        if min_width is not None and metadata.width < int(min_width):
            issues.append(
                ValidationIssue(
                    code="min_width_not_met",
                    message=f"Video width {metadata.width} is below required minimum {int(min_width)}",
                )
            )
        min_height = effective_profile.get("min_height")
        if min_height is not None and metadata.height < int(min_height):
            issues.append(
                ValidationIssue(
                    code="min_height_not_met",
                    message=f"Video height {metadata.height} is below required minimum {int(min_height)}",
                )
            )
        min_duration = effective_profile.get("min_duration_seconds")
        if min_duration is not None and metadata.duration_seconds < float(min_duration):
            issues.append(
                ValidationIssue(
                    code="min_duration_not_met",
                    message=(
                        f"Video duration {metadata.duration_seconds} is below required minimum {float(min_duration)}"
                    ),
                )
            )

        passed = len(issues) == 0
        return ValidationReport(
            decision=ValidationDecision.PASS if passed else ValidationDecision.FAIL,
            passed=passed,
            issues=issues,
            video_metadata=metadata,
        )
