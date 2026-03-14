from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

LIVE_RISK_DOMAINS = {
    "formula",
    "layout",
    "camera",
    "motion",
    "labels",
    "annotation",
    "geometry",
    "graph",
    "provider",
}


class PromptCase(BaseModel):
    case_id: str
    prompt: str
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    risk_domains: list[str] = Field(default_factory=list)
    review_focus: list[str] = Field(default_factory=list)
    baseline_group: str | None = None
    manual_review_required: bool = False

    @field_validator("risk_domains")
    @classmethod
    def validate_risk_domains(cls, value: list[str]) -> list[str]:
        unknown = [item for item in value if item not in LIVE_RISK_DOMAINS]
        if unknown:
            raise ValueError(f"unknown risk_domains: {', '.join(sorted(unknown))}")
        return value


class PromptSuite(BaseModel):
    suite_id: str
    cases: list[PromptCase] = Field(default_factory=list)
