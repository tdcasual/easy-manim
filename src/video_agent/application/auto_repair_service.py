from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from video_agent.adapters.storage.artifact_store import ArtifactStore
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.errors import AdmissionControlError
from video_agent.application.recovery_policy_service import RecoveryPolicyService
from video_agent.application.repair_prompt_builder import build_targeted_repair_feedback
from video_agent.application.task_service import TaskService
from video_agent.config import Settings
from video_agent.domain.enums import TaskStatus
from video_agent.domain.models import VideoTask


class AutoRepairDecision(BaseModel):
    created: bool
    reason: str
    issue_code: str | None = None
    child_task_id: str | None = None
    feedback: str | None = None


class AutoRepairService:
    def __init__(
        self,
        store: SQLiteTaskStore,
        artifact_store: ArtifactStore,
        settings: Settings,
        task_service: TaskService | None = None,
        recovery_policy_service: RecoveryPolicyService | None = None,
    ) -> None:
        self.store = store
        self.artifact_store = artifact_store
        self.settings = settings
        self.task_service = task_service or TaskService(store=store, artifact_store=artifact_store, settings=settings)
        self.recovery_policy_service = recovery_policy_service

    def maybe_schedule_repair(self, task: VideoTask) -> AutoRepairDecision:
        if not self.settings.auto_repair_enabled:
            return AutoRepairDecision(created=False, reason="disabled")
        if task.status is not TaskStatus.FAILED:
            return AutoRepairDecision(created=False, reason="task_not_failed")

        report = self.store.get_latest_validation(task.task_id)
        if report is None:
            return AutoRepairDecision(created=False, reason="missing_validation_report")

        issue_code = report.issues[0].code if report.issues else None
        if issue_code is None:
            return AutoRepairDecision(created=False, reason="missing_issue_code")
        if issue_code not in self.settings.auto_repair_retryable_issue_codes:
            return AutoRepairDecision(created=False, reason="non_retryable_issue", issue_code=issue_code)
        if not self._within_budget(task.root_task_id):
            return AutoRepairDecision(created=False, reason="budget_exhausted", issue_code=issue_code)

        feedback = self._build_feedback(task, issue_code)
        try:
            child = self.task_service.create_auto_repair_task(task.task_id, feedback=feedback)
        except AdmissionControlError as exc:
            return AutoRepairDecision(created=False, reason=exc.code, issue_code=issue_code, feedback=feedback)
        except ValueError:
            return AutoRepairDecision(created=False, reason="invalid_parent", issue_code=issue_code, feedback=feedback)

        return AutoRepairDecision(
            created=True,
            reason="created",
            issue_code=issue_code,
            child_task_id=child.task_id,
            feedback=feedback,
        )

    def _within_budget(self, root_task_id: str | None) -> bool:
        if root_task_id is None:
            return False

        lineage_count = self.store.count_lineage_tasks(root_task_id)
        child_count = max(0, lineage_count - 1)
        if child_count >= self.settings.auto_repair_max_children_per_root:
            return False
        if lineage_count >= self.settings.max_attempts_per_root_task:
            return False
        return True

    def _build_feedback(self, task: VideoTask, issue_code: str) -> str:
        failure_context = self._load_failure_context(task.task_id)
        memory_context_summary = None
        if self.task_service.session_memory_service is not None and task.session_id is not None:
            summary = self.task_service.session_memory_service.summarize_session_memory(task.session_id)
            memory_context_summary = summary.summary_text or None

        feedback = build_targeted_repair_feedback(
            issue_code=issue_code,
            failure_context=failure_context,
            memory_context_summary=memory_context_summary,
        )
        feedback = self._append_preserved_constraint_feedback(task, feedback, current_issue_code=issue_code)
        if self.recovery_policy_service is None:
            return feedback

        plan = self.recovery_policy_service.build(
            issue_code=issue_code,
            failure_contract=self.artifact_store.read_failure_contract(task.task_id),
        )
        if plan.selected_action:
            return f"Recovery policy: {plan.selected_action}\n\n{feedback}"
        return feedback

    def _load_failure_context(self, task_id: str) -> dict[str, Any]:
        path = self.artifact_store.failure_context_path(task_id)
        if not path.exists():
            return {}
        return json.loads(path.read_text())

    def _append_preserved_constraint_feedback(self, task: VideoTask, feedback: str, current_issue_code: str) -> str:
        guardrails = self._ancestor_semantic_guardrails(task, current_issue_code=current_issue_code)
        if not guardrails:
            return feedback

        lines = [feedback, "Preserve previously fixed constraints."]
        for item in guardrails[:3]:
            lines.append(self._format_preserved_constraint(item))
        return " ".join(lines)

    def _ancestor_semantic_guardrails(self, task: VideoTask, *, current_issue_code: str) -> list[dict[str, Any]]:
        guardrails: list[dict[str, Any]] = []
        seen: set[tuple[str | None, int | None, str | None]] = set()
        parent_task_id = task.parent_task_id

        while parent_task_id is not None:
            failure_context = self._load_failure_context(parent_task_id)
            for item in failure_context.get("semantic_diagnostics") or []:
                code = item.get("code")
                marker = (
                    str(code) if code is not None else None,
                    item.get("line"),
                    item.get("call_name"),
                )
                if code == current_issue_code or marker in seen:
                    continue
                seen.add(marker)
                guardrails.append(item)

            parent_task = self.store.get_task(parent_task_id)
            if parent_task is None:
                break
            parent_task_id = parent_task.parent_task_id

        return guardrails

    @staticmethod
    def _format_preserved_constraint(item: dict[str, Any]) -> str:
        code = item.get("code") or "unknown_issue"
        call_name = item.get("call_name")
        line = item.get("line")
        message = item.get("message")

        parts = [f"Previously fixed constraint: {code}"]
        if call_name:
            parts.append(f"on {call_name}")
        if line:
            parts.append(f"at line {line}")
        detail = " ".join(parts) + "."
        if message:
            detail = f"{detail} {str(message).strip()}."
        return detail
