from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EvalCaseState(BaseModel):
    status: str = "pending"
    root_task_id: str | None = None
    terminal_task_id: str | None = None
    issue_codes: list[str] = Field(default_factory=list)
    attempt_count: int = 0
    result: dict[str, Any] | None = None


class EvalRunManifest(BaseModel):
    run_id: str
    suite_id: str
    provider: str
    include_tags: list[str] = Field(default_factory=list)
    match_all_tags: bool = False
    cases: dict[str, EvalCaseState] = Field(default_factory=dict)
