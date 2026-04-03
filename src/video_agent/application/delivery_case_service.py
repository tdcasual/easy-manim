from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from video_agent.adapters.storage.artifact_store import ArtifactStore
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.lineage_graph import reachable_lineage_tasks
from video_agent.application.video_run_binding_service import VideoRunBindingService
from video_agent.domain.delivery_case_models import AgentRun, DeliveryCase
from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.domain.models import VideoTask
from video_agent.domain.validation_models import ValidationReport


class DeliveryCaseService:
    def __init__(
        self,
        *,
        store: SQLiteTaskStore,
        artifact_store: ArtifactStore,
        video_run_binding_service: VideoRunBindingService | None = None,
    ) -> None:
        self.store = store
        self.artifact_store = artifact_store
        self.video_run_binding_service = video_run_binding_service

    def ensure_case_for_task(self, task: VideoTask) -> tuple[DeliveryCase, bool]:
        case_id = task.root_task_id or task.task_id
        existing = self.store.get_delivery_case(case_id)
        if existing is not None:
            return existing, False
        delivery_case = DeliveryCase(
            case_id=case_id,
            root_task_id=case_id,
            active_task_id=task.task_id,
            delivery_status=task.delivery_status or "pending",
            completion_mode=task.completion_mode,
            stop_reason=task.delivery_stop_reason,
        )
        self.store.upsert_delivery_case(delivery_case)
        return delivery_case, True

    def sync_case_for_root(self, root_task_id: str) -> DeliveryCase | None:
        root_task = self.store.get_task(root_task_id)
        if root_task is None:
            return None
        lineage = self.store.list_lineage_tasks(root_task_id)
        reachable_lineage = reachable_lineage_tasks(lineage_tasks=lineage, root_task_id=root_task_id)
        active_task = reachable_lineage[-1] if reachable_lineage else root_task
        delivery_case, _ = self.ensure_case_for_task(root_task)
        delivery_case.root_task_id = root_task_id
        delivery_case.active_task_id = active_task.task_id
        delivery_case.selected_task_id = root_task.resolved_task_id
        delivery_case.selected_branch_id = root_task.resolved_task_id
        delivery_case.delivery_status = root_task.delivery_status or "pending"
        delivery_case.completion_mode = root_task.completion_mode
        delivery_case.stop_reason = root_task.delivery_stop_reason
        delivery_case.status = self._derive_case_status(
            root_task=root_task,
            active_task=active_task,
        )
        return self.store.upsert_delivery_case(delivery_case)

    def record_case_created(self, task: VideoTask) -> None:
        self.append_agent_run(
            task=task,
            role="orchestrator",
            status="completed",
            phase=task.phase.value,
            summary="Delivery case created",
            decision={"action": "case_created"},
        )

    def queue_generator_run(self, *, task: VideoTask) -> AgentRun:
        return self._upsert_lifecycle_run(
            task=task,
            role="generator",
            status="queued",
            phase=task.phase.value,
            summary="Generator queued",
        )

    def mark_planner_running(self, *, task: VideoTask) -> AgentRun:
        return self._upsert_lifecycle_run(
            task=task,
            role="planner",
            status="running",
            phase=TaskPhase.SCENE_PLANNING.value,
            summary="Scene planning running",
        )

    def mark_generator_running(self, *, task: VideoTask) -> AgentRun:
        return self._upsert_lifecycle_run(
            task=task,
            role="generator",
            status="running",
            phase=TaskPhase.GENERATING_CODE.value,
            summary="Generation running",
        )

    def mark_reviewer_running(self, *, task: VideoTask) -> AgentRun:
        return self._upsert_lifecycle_run(
            task=task,
            role="reviewer",
            status="running",
            phase=TaskPhase.VALIDATION.value,
            summary="Review running",
        )

    def mark_repairer_running(self, *, task: VideoTask) -> AgentRun:
        return self._upsert_lifecycle_run(
            task=task,
            role="repairer",
            status="running",
            phase=TaskPhase.FAILED.value,
            summary="Auto repair running",
        )

    def record_planner_run(
        self,
        *,
        task: VideoTask,
        scene_spec_path: Path,
        scene_plan_path: Path,
    ) -> None:
        self._upsert_lifecycle_run(
            task=task,
            role="planner",
            status="completed",
            phase=TaskPhase.SCENE_PLANNING.value,
            summary="Scene planning completed",
            output_refs=[
                self._resource_ref(task.task_id, scene_spec_path),
                self._resource_ref(task.task_id, scene_plan_path),
            ],
            decision={
                "risk_level": task.risk_level,
                "generation_mode": task.generation_mode,
                "scene_spec_id": task.scene_spec_id,
            },
        )

    def record_generator_run(
        self,
        *,
        task: VideoTask,
            status: str,
            summary: str,
            phase: str,
            script_path: Path | None = None,
            video_path: Path | None = None,
            stop_reason: str | None = None,
            decision: dict[str, Any] | None = None,
    ) -> None:
        output_refs: list[str] = []
        if script_path is not None and script_path.exists():
            output_refs.append(self._resource_ref(task.task_id, script_path))
        if video_path is not None and video_path.exists():
            output_refs.append(self._resource_ref(task.task_id, video_path))
        self._upsert_lifecycle_run(
            task=task,
            role="generator",
            status=status,
            phase=phase,
            summary=summary,
            output_refs=output_refs,
            stop_reason=stop_reason,
            decision=decision or {},
        )

    def record_reviewer_run(
        self,
        *,
        task: VideoTask,
        report: ValidationReport,
        summary: str,
        quality_gate_status: str | None = None,
        failure_contract: dict[str, Any] | None = None,
        recovery_plan: dict[str, Any] | None = None,
        validation_report_path: Path | None = None,
        quality_score_path: Path | None = None,
    ) -> None:
        output_refs: list[str] = []
        if validation_report_path is not None and validation_report_path.exists():
            output_refs.append(self._resource_ref(task.task_id, validation_report_path))
        if quality_score_path is not None and quality_score_path.exists():
            output_refs.append(self._resource_ref(task.task_id, quality_score_path))
        self._upsert_lifecycle_run(
            task=task,
            role="reviewer",
            status="completed",
            phase=task.phase.value,
            summary=summary,
            output_refs=output_refs,
            decision={
                "passed": report.passed,
                "issues": [issue.code for issue in report.issues],
                "quality_gate_status": quality_gate_status,
                "failure_recommended_action": None
                if not isinstance(failure_contract, dict)
                else failure_contract.get("recommended_action"),
                "recovery_selected_action": None
                if not isinstance(recovery_plan, dict)
                else recovery_plan.get("selected_action"),
            },
        )

    def record_repairer_run(
        self,
        *,
        task: VideoTask,
        auto_repair_decision: Any,
        report: ValidationReport,
    ) -> None:
        self._upsert_lifecycle_run(
            task=task,
            role="repairer",
            status="completed",
            phase=TaskPhase.FAILED.value,
            summary="Auto repair evaluated",
            decision={
                "created": auto_repair_decision.created,
                "reason": auto_repair_decision.reason,
                "issue_code": auto_repair_decision.issue_code or (report.issues[0].code if report.issues else None),
                "child_task_id": auto_repair_decision.child_task_id,
            },
        )

    def record_branch_spawned(
        self,
        *,
        incumbent_task: VideoTask,
        challenger_task: VideoTask,
    ) -> None:
        self.append_agent_run(
            task=challenger_task,
            role="orchestrator",
            status="completed",
            phase=challenger_task.phase.value,
            summary="Challenger branch created",
            decision={
                "action": "challenger_created",
                "incumbent_task_id": incumbent_task.task_id,
                "challenger_task_id": challenger_task.task_id,
                "root_task_id": challenger_task.root_task_id or challenger_task.task_id,
            },
        )

    def record_winner_selected(
        self,
        *,
        selected_task: VideoTask,
        previous_selected_task_id: str | None = None,
        arbitration_summary: dict[str, Any] | None = None,
    ) -> None:
        decision = {
            "action": "winner_selected",
            "selected_task_id": selected_task.task_id,
            "root_task_id": selected_task.root_task_id or selected_task.task_id,
            "completion_mode": selected_task.completion_mode,
        }
        if previous_selected_task_id is not None:
            decision["previous_selected_task_id"] = previous_selected_task_id
        if arbitration_summary:
            decision["arbitration_summary"] = dict(arbitration_summary)
        self.append_agent_run(
            task=selected_task,
            role="orchestrator",
            status="completed",
            phase=selected_task.phase.value,
            summary="Winner selected",
            decision=decision,
        )

    def record_auto_arbitration_evaluated(
        self,
        *,
        task: VideoTask,
        arbitration_summary: dict[str, Any],
        promoted: bool,
    ) -> None:
        self.append_agent_run(
            task=task,
            role="orchestrator",
            status="completed",
            phase=task.phase.value,
            summary="Automatic arbitration evaluated",
            decision={
                "action": "auto_arbitration_evaluated",
                "recommended_task_id": arbitration_summary.get("recommended_task_id"),
                "recommended_action": arbitration_summary.get("recommended_action"),
                "reason": arbitration_summary.get("reason"),
                "selected_task_id": arbitration_summary.get("selected_task_id"),
                "candidate_count": arbitration_summary.get("candidate_count"),
                "promoted": promoted,
            },
        )

    def append_agent_run(
        self,
        *,
        task: VideoTask,
        role: str,
        status: str,
        phase: str | None,
        summary: str,
        decision: dict[str, Any] | None = None,
        input_refs: list[str] | None = None,
        output_refs: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentRun:
        delivery_case, _ = self.ensure_case_for_task(task)
        return self.store.create_agent_run(
            AgentRun(
                case_id=delivery_case.case_id,
                root_task_id=delivery_case.root_task_id,
                task_id=task.task_id,
                role=role,
                status=status,
                phase=phase,
                summary=summary,
                input_refs=list(input_refs or []),
                output_refs=list(output_refs or []),
                decision=dict(decision or {}),
                metadata=dict(metadata or {}),
            )
        )

    def _upsert_lifecycle_run(
        self,
        *,
        task: VideoTask,
        role: str,
        status: str,
        phase: str | None,
        summary: str,
        decision: dict[str, Any] | None = None,
        input_refs: list[str] | None = None,
        output_refs: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        stop_reason: str | None = None,
    ) -> AgentRun:
        delivery_case, _ = self.ensure_case_for_task(task)
        run_id = self._lifecycle_run_id(task.task_id, role)
        existing = next(
            (
                run
                for run in self.store.list_agent_runs(delivery_case.case_id, role=role, task_id=task.task_id)
                if run.run_id == run_id
            ),
            None,
        )
        now = _utcnow()
        started_at = None if existing is None else existing.started_at
        finished_at = None if existing is None else existing.finished_at
        if status == "running":
            started_at = started_at or now
            finished_at = None
        elif status in {"completed", "failed", "cancelled"}:
            started_at = started_at or now
            finished_at = now
        elif status == "queued":
            finished_at = None

        run = self.store.upsert_agent_run(
            AgentRun(
                run_id=run_id,
                case_id=delivery_case.case_id,
                root_task_id=delivery_case.root_task_id,
                task_id=task.task_id,
                role=role,
                status=status,
                phase=phase,
                summary=summary,
                input_refs=list(input_refs or []),
                output_refs=list(output_refs or []),
                decision=dict(decision or {}),
                metadata={"lifecycle": True, **dict(metadata or {})},
                stop_reason=stop_reason,
                started_at=started_at,
                finished_at=finished_at,
            )
        )
        if self.video_run_binding_service is not None and status != "queued":
            self.video_run_binding_service.sync_task_lifecycle_run(
                task=task,
                status=status,
                phase=phase,
                summary=summary,
            )
        return run

    @staticmethod
    def _lifecycle_run_id(task_id: str, role: str) -> str:
        return f"{task_id}:{role}"

    def _derive_case_status(self, *, root_task: VideoTask, active_task: VideoTask) -> str:
        if root_task.delivery_status == "failed":
            return "failed"
        if root_task.delivery_status == "delivered":
            if self._is_arbitrating_candidate(root_task=root_task, active_task=active_task):
                return "arbitrating"
            if active_task.task_id != (root_task.resolved_task_id or root_task.task_id) and active_task.status in {
                TaskStatus.QUEUED,
                TaskStatus.REVISING,
                TaskStatus.RUNNING,
            }:
                return "branching"
            return "completed"
        if active_task.task_id != root_task.task_id and active_task.status in {
            TaskStatus.QUEUED,
            TaskStatus.REVISING,
            TaskStatus.RUNNING,
        }:
            return "repairing"
        if active_task.phase in {TaskPhase.PREVIEW_VALIDATION, TaskPhase.VALIDATION, TaskPhase.QUALITY_JUDGING}:
            return "reviewing"
        if active_task.status is TaskStatus.RUNNING:
            return "running"
        if active_task.phase in {TaskPhase.SCENE_PLANNING, TaskPhase.PLANNING}:
            return "planning"
        return "queued"

    @staticmethod
    def _is_arbitrating_candidate(*, root_task: VideoTask, active_task: VideoTask) -> bool:
        selected_task_id = root_task.resolved_task_id or root_task.task_id
        if active_task.task_id == selected_task_id:
            return False
        if active_task.branch_kind != "challenger":
            return False
        if active_task.status is not TaskStatus.COMPLETED:
            return False
        if active_task.delivery_status != "delivered":
            return False
        return active_task.quality_gate_status == "accepted"

    def _resource_ref(self, task_id: str, path: Path) -> str:
        return self.artifact_store.resource_uri(task_id, path)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
