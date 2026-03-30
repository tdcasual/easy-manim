from __future__ import annotations

from typing import Any

from video_agent.adapters.storage.artifact_store import ArtifactStore
from video_agent.domain.case_memory_models import CaseMemorySnapshot
from video_agent.domain.models import VideoTask
from video_agent.domain.quality_models import QualityScorecard


class CaseMemoryService:
    def __init__(self, *, artifact_store: ArtifactStore) -> None:
        self.artifact_store = artifact_store

    def get_case_memory(self, root_task_id: str) -> dict[str, Any]:
        payload = self.artifact_store.read_case_memory(root_task_id)
        if payload is None:
            return CaseMemorySnapshot(root_task_id=root_task_id).model_dump(mode="json")
        return CaseMemorySnapshot.model_validate(payload).model_dump(mode="json")

    def record_planner_state(self, task: VideoTask) -> dict[str, Any]:
        root_task_id = task.root_task_id or task.task_id
        snapshot = self._load(root_task_id)
        planner_note = {
            "task_id": task.task_id,
            "scene_spec_id": task.scene_spec_id,
            "generation_mode": task.generation_mode,
            "risk_level": task.risk_level,
            "display_title": task.display_title,
        }
        snapshot.planner_notes = [planner_note]
        snapshot.delivery_invariants = self._build_delivery_invariants(task)
        self._write(snapshot)
        return snapshot.model_dump(mode="json")

    def record_review_outcome(
        self,
        task: VideoTask,
        *,
        summary: str | None,
        quality_gate_status: str | None,
        quality_scorecard: QualityScorecard | None,
        failure_contract: dict[str, Any] | None,
        recovery_plan: dict[str, Any] | None,
    ) -> dict[str, Any]:
        root_task_id = task.root_task_id or task.task_id
        snapshot = self._load(root_task_id)
        scorecard_json = None if quality_scorecard is None else quality_scorecard.model_dump(mode="json")
        finding = {
            "task_id": task.task_id,
            "branch_kind": task.branch_kind or ("primary" if task.task_id == root_task_id else "revision"),
            "quality_gate_status": quality_gate_status,
            "summary": summary,
            "accepted": None if scorecard_json is None else bool(scorecard_json.get("accepted")),
            "overall_score": None
            if scorecard_json is None
            else scorecard_json.get("total_score", scorecard_json.get("overall_score")),
            "must_fix_issue_codes": []
            if scorecard_json is None
            else list(scorecard_json.get("must_fix_issues", []) or []),
            "warning_codes": [] if scorecard_json is None else list(scorecard_json.get("warning_codes", []) or []),
        }
        snapshot.review_findings = self._upsert_by_task_id(snapshot.review_findings, finding)

        repair_constraint = {
            "task_id": task.task_id,
            "quality_gate_status": quality_gate_status,
            "must_fix_issue_codes": finding["must_fix_issue_codes"],
            "recommended_action": None
            if not isinstance(failure_contract, dict)
            else str(failure_contract.get("recommended_action") or "").strip() or None,
            "repair_strategy": None
            if not isinstance(failure_contract, dict)
            else str(failure_contract.get("repair_strategy") or "").strip() or None,
            "recovery_selected_action": None
            if not isinstance(recovery_plan, dict)
            else str(recovery_plan.get("selected_action") or "").strip() or None,
            "summary": summary,
        }
        if self._has_useful_constraint(repair_constraint):
            snapshot.repair_constraints = self._upsert_by_task_id(snapshot.repair_constraints, repair_constraint)

        self._write(snapshot)
        return snapshot.model_dump(mode="json")

    def record_branch_state(
        self,
        root_task_id: str,
        *,
        branch_scoreboard: list[dict[str, Any]],
        arbitration_summary: dict[str, Any],
    ) -> dict[str, Any]:
        snapshot = self._load(root_task_id)
        snapshot.branch_comparisons = [
            {
                "task_id": entry.get("task_id"),
                "branch_kind": entry.get("branch_kind"),
                "comparison_label": entry.get("comparison_label"),
                "overall_score": entry.get("overall_score"),
                "quality_gate_status": entry.get("quality_gate_status"),
                "is_selected": entry.get("is_selected"),
                "recommended_action": arbitration_summary.get("recommended_action"),
                "recommended_task_id": arbitration_summary.get("recommended_task_id"),
            }
            for entry in branch_scoreboard
        ]
        self._write(snapshot)
        return snapshot.model_dump(mode="json")

    def record_decision(
        self,
        root_task_id: str,
        *,
        action: str,
        task_id: str | None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        snapshot = self._load(root_task_id)
        decision = {"action": action, "task_id": task_id, **dict(details or {})}
        snapshot.decision_log.append(decision)
        snapshot.decision_log = snapshot.decision_log[-20:]
        self._write(snapshot)
        return snapshot.model_dump(mode="json")

    def augment_feedback(self, root_task_id: str, base_feedback: str) -> str:
        snapshot = self._load(root_task_id)
        lines: list[str] = []
        if snapshot.delivery_invariants:
            lines.append("Shared case constraints.")
            lines.extend(snapshot.delivery_invariants[:2])
        latest_constraint = snapshot.repair_constraints[-1] if snapshot.repair_constraints else None
        if latest_constraint is not None:
            must_fix = list(latest_constraint.get("must_fix_issue_codes", []) or [])
            if must_fix:
                lines.append(f"Must fix issues: {', '.join(str(item) for item in must_fix[:3])}.")
            recovery_action = str(latest_constraint.get("recovery_selected_action") or "").strip()
            if recovery_action:
                lines.append(f"Latest recovery action: {recovery_action}.")
            recommended_action = str(latest_constraint.get("recommended_action") or "").strip()
            if recommended_action:
                lines.append(f"Failure contract action: {recommended_action}.")
        prefix = " ".join(part.strip() for part in lines if str(part).strip())
        if not prefix:
            return base_feedback
        return f"{prefix} {base_feedback}".strip()

    def _load(self, root_task_id: str) -> CaseMemorySnapshot:
        payload = self.artifact_store.read_case_memory(root_task_id)
        if payload is None:
            return CaseMemorySnapshot(root_task_id=root_task_id)
        return CaseMemorySnapshot.model_validate(payload)

    def _write(self, snapshot: CaseMemorySnapshot) -> None:
        self.artifact_store.write_case_memory(snapshot.root_task_id, snapshot)

    @staticmethod
    def _build_delivery_invariants(task: VideoTask) -> list[str]:
        invariants = [f"Preserve core prompt intent: {task.prompt}."]
        if task.display_title:
            invariants.append(f"Keep title direction aligned with: {task.display_title}.")
        return invariants

    @staticmethod
    def _upsert_by_task_id(items: list[dict[str, Any]], payload: dict[str, Any]) -> list[dict[str, Any]]:
        task_id = payload.get("task_id")
        updated = [dict(item) for item in items if item.get("task_id") != task_id]
        updated.append(dict(payload))
        return updated[-20:]

    @staticmethod
    def _has_useful_constraint(payload: dict[str, Any]) -> bool:
        if list(payload.get("must_fix_issue_codes", []) or []):
            return True
        if str(payload.get("recommended_action") or "").strip():
            return True
        if str(payload.get("repair_strategy") or "").strip():
            return True
        if str(payload.get("recovery_selected_action") or "").strip():
            return True
        return str(payload.get("quality_gate_status") or "").strip() == "needs_revision"
