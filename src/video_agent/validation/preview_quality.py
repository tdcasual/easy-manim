from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageStat, UnidentifiedImageError

from video_agent.domain.enums import ValidationDecision
from video_agent.domain.validation_models import ValidationIssue, ValidationReport


class PreviewQualityValidator:
    STATIC_FIRST_LAST_THRESHOLD = 1.0
    STATIC_CONSECUTIVE_THRESHOLD = 0.75

    def validate(self, preview_paths: list[Path], profile: dict[str, object] | None = None) -> ValidationReport:
        issues: list[ValidationIssue] = []
        effective = profile or {}
        readable_images = self._readable_images(preview_paths)
        if not readable_images:
            return ValidationReport(
                decision=ValidationDecision.PASS,
                passed=True,
                issues=[],
                summary="Preview quality checks skipped",
            )

        first_brightness = sum(ImageStat.Stat(readable_images[0]).mean) / 3.0
        if effective.get("check_blank_previews", True) and first_brightness < 5.0:
            issues.append(ValidationIssue(code="near_blank_preview", message="Preview sequence starts effectively blank"))

        if effective.get("check_static_previews", True) and len(readable_images) >= 2:
            first_last_diff = self._mean_rgb_diff(readable_images[0], readable_images[-1])
            max_consecutive_diff = 0.0
            if len(readable_images) >= 3:
                max_consecutive_diff = max(
                    self._mean_rgb_diff(current, following)
                    for current, following in zip(readable_images, readable_images[1:])
                )

            if first_last_diff < self.STATIC_FIRST_LAST_THRESHOLD and max_consecutive_diff < self.STATIC_CONSECUTIVE_THRESHOLD:
                issues.append(ValidationIssue(code="static_previews", message="Preview sequence shows too little motion"))

        passed = not issues
        return ValidationReport(
            decision=ValidationDecision.PASS if passed else ValidationDecision.FAIL,
            passed=passed,
            issues=issues,
            summary="Preview quality passed" if passed else "Preview quality failed",
        )

    @staticmethod
    def _readable_images(preview_paths: list[Path]) -> list[Image.Image]:
        images: list[Image.Image] = []
        for path in preview_paths:
            try:
                with Image.open(path) as image:
                    images.append(image.convert("RGB").copy())
            except (UnidentifiedImageError, OSError):
                continue
        return images

    @staticmethod
    def _mean_rgb_diff(first: Image.Image, second: Image.Image) -> float:
        diff = ImageChops.difference(first, second)
        return sum(ImageStat.Stat(diff).mean) / 3.0
