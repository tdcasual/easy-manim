from __future__ import annotations

from pydantic import BaseModel, Field


class PromptCase(BaseModel):
    case_id: str
    prompt: str
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


class PromptSuite(BaseModel):
    suite_id: str
    cases: list[PromptCase] = Field(default_factory=list)
