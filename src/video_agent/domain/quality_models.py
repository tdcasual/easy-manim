from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class QualityScorecard(BaseModel):
    task_id: str = ""
    overall_score: float | None = None
    dimensions: dict[str, float] = Field(default_factory=dict)
    total_score: float | None = None
    dimension_scores: dict[str, float] = Field(default_factory=dict)
    must_fix_issues: list[str] = Field(default_factory=list)
    accepted: bool = False
    summary: str | None = None
    decision: str | None = None
    warning_codes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def sync_score_fields(self) -> "QualityScorecard":
        if self.total_score is None and self.overall_score is not None:
            self.total_score = self.overall_score
        if self.overall_score is None and self.total_score is not None:
            self.overall_score = self.total_score

        if not self.dimension_scores and self.dimensions:
            self.dimension_scores = dict(self.dimensions)
        if not self.dimensions and self.dimension_scores:
            self.dimensions = dict(self.dimension_scores)
        return self
