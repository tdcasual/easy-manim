from __future__ import annotations

import time
from contextlib import contextmanager
from uuid import uuid4

from pydantic import BaseModel, Field

from video_agent.adapters.llm.client import StubLLMClient
from video_agent.evaluation.corpus import load_prompt_suite
from video_agent.evaluation.live_reporting import build_live_report
from video_agent.evaluation.quality_reporting import build_quality_report
from video_agent.evaluation.repair_reporting import build_repair_report
from video_agent.evaluation.reviewer_digest import render_reviewer_digest
from video_agent.evaluation.reporting import build_eval_report, render_eval_report_markdown
from video_agent.server.app import AppContext


GOOD_REPAIR_SCRIPT = (
    "from manim import Circle, Create, Scene\n\n"
    "class RepairedScene(Scene):\n"
    "    def construct(self):\n"
    "        circle = Circle()\n"
    "        self.play(Create(circle))\n"
)
BROKEN_REPAIR_SCRIPT = "from manim import Circle\ncircle = Circle()\n"
QUALITY_ISSUE_CODES = {
    "near_blank_preview",
    "static_previews",
    "black_frames",
    "frozen_tail",
    "encoding_error",
    "min_width_not_met",
    "min_height_not_met",
    "min_duration_not_met",
}


class EvaluationCaseResult(BaseModel):
    case_id: str
    task_id: str
    root_task_id: str
    status: str
    duration_seconds: float
    tags: list[str] = Field(default_factory=list)
    issue_codes: list[str] = Field(default_factory=list)
    repair_attempted: bool = False
    repair_children: int = 0
    repair_success: bool = False
    repair_stop_reason: str | None = None
    quality_issue_codes: list[str] = Field(default_factory=list)
    quality_score: float = 0.0
    risk_domains: list[str] = Field(default_factory=list)
    review_focus: list[str] = Field(default_factory=list)
    baseline_group: str | None = None
    manual_review_required: bool = False


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

    def run_suite(
        self,
        suite_path: str,
        include_tags: set[str] | None = None,
        limit: int | None = None,
        match_all_tags: bool = False,
    ) -> EvaluationRunSummary:
        suite = load_prompt_suite(suite_path, include_tags=include_tags, match_all_tags=match_all_tags)
        cases = suite.cases[:limit] if limit is not None else suite.cases
        run_id = str(uuid4())
        items: list[EvaluationCaseResult] = []

        for case in cases:
            started = time.monotonic()
            with self._override_llm_client_for_case(case.tags):
                created = self.context.task_service.create_video_task(
                    prompt=case.prompt,
                    idempotency_key=f"eval:{run_id}:{case.case_id}",
                )
                root_snapshot, terminal_snapshot = self._wait_for_lineage(created.task_id)
            issues = [item["code"] for item in terminal_snapshot.latest_validation_summary.get("issues", [])]
            quality_issue_codes = [code for code in issues if code in QUALITY_ISSUE_CODES]
            items.append(
                EvaluationCaseResult(
                    case_id=case.case_id,
                    task_id=terminal_snapshot.task_id,
                    root_task_id=created.task_id,
                    status=terminal_snapshot.status,
                    duration_seconds=round(time.monotonic() - started, 4),
                    tags=list(case.tags),
                    issue_codes=issues,
                    repair_attempted=bool(root_snapshot.repair_state.get("attempted")),
                    repair_children=int(root_snapshot.repair_state.get("child_count", 0) or 0),
                    repair_success=bool(root_snapshot.repair_state.get("attempted")) and terminal_snapshot.status == "completed",
                    repair_stop_reason=root_snapshot.repair_state.get("stop_reason"),
                    quality_issue_codes=quality_issue_codes,
                    quality_score=self._quality_score(terminal_snapshot.status, quality_issue_codes),
                    risk_domains=list(case.risk_domains),
                    review_focus=list(case.review_focus),
                    baseline_group=case.baseline_group,
                    manual_review_required=case.manual_review_required,
                )
            )

        item_payloads = [item.model_dump(mode="json") for item in items]
        report = build_eval_report(item_payloads)
        report["repair"] = build_repair_report(item_payloads)
        report["quality"] = build_quality_report(item_payloads)
        report["live"] = build_live_report(item_payloads)
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
        self.context.artifact_store.write_eval_reviewer_digest(run_id, render_reviewer_digest(payload))
        return summary

    def _wait_for_lineage(self, root_task_id: str):
        terminal_statuses = {"completed", "failed", "cancelled"}
        while True:
            processed = self.context.worker.run_once()
            root_snapshot = self.context.task_service.get_video_task(root_task_id)
            latest_child_id = root_snapshot.auto_repair_summary.get("latest_child_task_id")
            terminal_task_id = latest_child_id or root_task_id
            terminal_snapshot = self.context.task_service.get_video_task(terminal_task_id)
            if terminal_snapshot.status in terminal_statuses:
                if latest_child_id is None or terminal_snapshot.task_id == latest_child_id:
                    return root_snapshot, terminal_snapshot
            if processed == 0:
                time.sleep(self.context.settings.worker_poll_interval_seconds)

    @contextmanager
    def _override_llm_client_for_case(self, tags: list[str]):
        if "repair" not in tags or self.context.settings.llm_provider != "stub":
            yield
            return

        original_client = self.context.workflow_engine.llm_client
        self.context.workflow_engine.llm_client = _SequenceLLMClient([BROKEN_REPAIR_SCRIPT, GOOD_REPAIR_SCRIPT])
        try:
            yield
        finally:
            self.context.workflow_engine.llm_client = original_client

    @staticmethod
    def _quality_score(status: str, quality_issue_codes: list[str]) -> float:
        score = 1.0
        if status != "completed":
            score -= 0.4
        score -= 0.2 * len(quality_issue_codes)
        return max(0.0, round(score, 4))


class _SequenceLLMClient(StubLLMClient):
    def __init__(self, scripts: list[str]) -> None:
        super().__init__(script=scripts[-1] if scripts else GOOD_REPAIR_SCRIPT)
        self._scripts = list(scripts)
        self._fallback = scripts[-1] if scripts else GOOD_REPAIR_SCRIPT

    def generate_script(self, prompt_text: str) -> str:
        if self._scripts:
            return self._scripts.pop(0)
        return self._fallback
