from __future__ import annotations

import time
from uuid import uuid4

from pydantic import BaseModel, Field

from video_agent.evaluation.corpus import load_prompt_suite
from video_agent.evaluation.reporting import build_eval_report, render_eval_report_markdown
from video_agent.server.app import AppContext


class EvaluationCaseResult(BaseModel):
    case_id: str
    task_id: str
    status: str
    duration_seconds: float
    issue_codes: list[str] = Field(default_factory=list)


class EvaluationRunSummary(BaseModel):
    run_id: str
    suite_id: str
    provider: str
    total_cases: int
    items: list[EvaluationCaseResult] = Field(default_factory=list)
    report: dict[str, object] = Field(default_factory=dict)


class EvaluationService:
    def __init__(self, context: AppContext) -> None:
        self.context = context

    def run_suite(self, suite_path: str, include_tags: set[str] | None = None, limit: int | None = None) -> EvaluationRunSummary:
        suite = load_prompt_suite(suite_path, include_tags=include_tags)
        cases = suite.cases[:limit] if limit is not None else suite.cases
        run_id = str(uuid4())
        items: list[EvaluationCaseResult] = []

        for case in cases:
            started = time.monotonic()
            created = self.context.task_service.create_video_task(
                prompt=case.prompt,
                idempotency_key=f"eval:{run_id}:{case.case_id}",
            )
            while True:
                processed = self.context.worker.run_once()
                snapshot = self.context.task_service.get_video_task(created.task_id)
                if snapshot.status in {"completed", "failed", "cancelled"}:
                    break
                if processed == 0:
                    time.sleep(self.context.settings.worker_poll_interval_seconds)
            issues = [item["code"] for item in snapshot.latest_validation_summary.get("issues", [])]
            items.append(
                EvaluationCaseResult(
                    case_id=case.case_id,
                    task_id=created.task_id,
                    status=snapshot.status,
                    duration_seconds=round(time.monotonic() - started, 4),
                    issue_codes=issues,
                )
            )

        report = build_eval_report([item.model_dump(mode="json") for item in items])
        summary = EvaluationRunSummary(
            run_id=run_id,
            suite_id=suite.suite_id,
            provider=self.context.settings.llm_provider,
            total_cases=len(items),
            items=items,
            report=report,
        )
        payload = summary.model_dump(mode="json")
        self.context.artifact_store.write_eval_summary(run_id, payload)
        self.context.artifact_store.write_eval_summary_markdown(run_id, render_eval_report_markdown(payload))
        return summary
