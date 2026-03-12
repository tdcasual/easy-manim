from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from video_agent.domain.enums import ValidationDecision


class ValidationIssue(BaseModel):
    code: str
    message: str
    severity: str = "error"


class VideoMetadata(BaseModel):
    width: int = 0
    height: int = 0
    duration_seconds: float = 0.0


class ValidationReport(BaseModel):
    decision: ValidationDecision = ValidationDecision.FAIL
    passed: bool = False
    issues: list[ValidationIssue] = Field(default_factory=list)
    summary: Optional[str] = None
    video_metadata: Optional[VideoMetadata] = None
    details: dict[str, Any] = Field(default_factory=dict)
