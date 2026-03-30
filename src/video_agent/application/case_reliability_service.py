from __future__ import annotations

from pathlib import Path
from typing import Any

from video_agent.adapters.storage.artifact_store import ArtifactStore
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.lineage_graph import orphaned_lineage_tasks, reachable_lineage_tasks
from video_agent.application.runtime_service import RuntimeService
from video_agent.config import Settings
from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.domain.models import VideoTask
from video_agent.domain.validation_models import ValidationReport
from video_agent.observability.metrics import MetricsCollector


class CaseReliabilityService:
    def __init__(
        self,
        *,
        settings: Settings,
        store: SQLiteTaskStore,
        artifact_store: ArtifactStore,
        runtime_service: RuntimeService,
        workflow_engine: Any,
        metrics: MetricsCollector,
    ) -> None:
        self.settings = settings
        self.store = store
        self.artifact_store = artifact_store
        self.runtime_service = runtime_service
        self.workflow_engine = workflow_engine
        self.metrics = metrics

    def reconcile_startup(self) -> dict[str, int]:
        requeued = self.store.requeue_stale_tasks(recovery_grace_seconds=self.settings.worker_recovery_grace_seconds)
        self.metrics.increment("task_reliability_requeued", requeued)
        return self._reconcile_pending_roots(mark_runtime_unhealthy=False)

    def sweep_watchdog(self) -> dict[str, int]:
        return self._reconcile_pending_roots(
            mark_runtime_unhealthy=not self.runtime_service.inspect_task_processing().ready
        )

    def _reconcile_pending_roots(self, *, mark_runtime_unhealthy: bool) -> dict[str, int]:
        reconciled = 0
        failed = 0
        for root_task in self._iter_root_tasks():
            root_reconciled = self._sync_case_state(root_task.task_id)
            refreshed_root = self.store.get_task(root_task.task_id)
            if refreshed_root is not None:
                root_task = refreshed_root
            root_reconciled = self._reconcile_orphaned_branches(root_task) or root_reconciled
            root_reconciled = self._reconcile_stalled_agent_runs(root_task) or root_reconciled

            challenger_handled, challenger_reconciled = self._reconcile_completed_challenger(root_task)
            root_reconciled = root_reconciled or challenger_reconciled
            if challenger_handled:
                if root_reconciled:
                    reconciled += 1
                continue

            if root_reconciled and root_task.delivery_status == "failed":
                reconciled += 1
                continue
            if root_reconciled and root_task.delivery_status == "delivered" and self._resolved_delivery_has_valid_video(root_task):
                reconciled += 1
                continue

            delivered_descendant = self._find_delivered_descendant(root_task.root_task_id or root_task.task_id)
            if delivered_descendant is not None:
                self.workflow_engine._sync_root_delivery_resolution(delivered_descendant)
                self._append_reliability_event(
                    root_task.task_id,
                    action="sync_delivered_descendant",
                    resolved_task_id=delivered_descendant.task_id,
                )
                reconciled += 1
                continue

            if root_task.delivery_status == "failed":
                if root_reconciled:
                    reconciled += 1
                continue

            leaf_task = self._find_leaf_task(root_task.root_task_id or root_task.task_id)
            if leaf_task is None:
                if root_reconciled:
                    reconciled += 1
                continue

            missing_artifact_outcome = self._reconcile_missing_delivery_artifact(root_task, leaf_task)
            if missing_artifact_outcome == "reconciled":
                reconciled += 1
                continue
            if missing_artifact_outcome == "failed":
                failed += 1
                continue

            if leaf_task.status is TaskStatus.FAILED:
                if self._resume_failed_leaf(leaf_task):
                    reconciled += 1
                else:
                    failed += 1
                continue

            if mark_runtime_unhealthy and leaf_task.status in {
                TaskStatus.QUEUED,
                TaskStatus.REVISING,
                TaskStatus.RUNNING,
            }:
                self._mark_lineage_runtime_failed(leaf_task, stop_reason="runtime_unhealthy")
                failed += 1
                continue

            if root_reconciled:
                reconciled += 1

        if reconciled:
            self.metrics.increment("task_reliability_reconciled", reconciled)
        if failed:
            self.metrics.increment("task_reliability_failed", failed)
        return {"reconciled": reconciled, "failed": failed}

    def _reconcile_completed_challenger(self, root_task: VideoTask) -> tuple[bool, bool]:
        root_task_id = root_task.root_task_id or root_task.task_id
        leaf_task = self._find_leaf_task(root_task_id)
        if leaf_task is None:
            return False, False
        if leaf_task.task_id == root_task_id:
            return False, False
        if leaf_task.branch_kind != "challenger":
            return False, False
        if leaf_task.status is not TaskStatus.COMPLETED or leaf_task.delivery_status != "delivered":
            return False, False
        if root_task.resolved_task_id == leaf_task.task_id:
            return False, False

        delivery_case = self.store.get_delivery_case(root_task_id)
        arbitration_resumed = delivery_case is not None and delivery_case.status == "arbitrating"
        decision = self.workflow_engine._maybe_auto_promote_challenger(leaf_task)
        self.workflow_engine._record_auto_arbitration_decision(leaf_task, decision)
        if arbitration_resumed:
            self._append_reliability_event(
                root_task.task_id,
                action="case_arbitration_resumed",
                resolved_task_id=decision.get("selected_task_id") or root_task.resolved_task_id,
                recommended_task_id=decision.get("recommended_task_id"),
                recommended_action=decision.get("recommended_action"),
                promoted=bool(decision.get("promoted")),
                reason=decision.get("reason"),
            )
        if bool(decision.get("promoted")):
            self._append_reliability_event(
                root_task.task_id,
                action="auto_arbitration_promoted",
                resolved_task_id=leaf_task.task_id,
                recommended_action=decision.get("recommended_action"),
            )
            return True, True

        case_synced = self._sync_case_state(root_task.task_id)
        self._append_reliability_event(
            root_task.task_id,
            action="auto_arbitration_kept_incumbent",
            recommended_task_id=decision.get("recommended_task_id"),
            recommended_action=decision.get("recommended_action"),
            selected_task_id=decision.get("selected_task_id"),
            reason=decision.get("reason"),
        )
        return True, case_synced

    def _resume_failed_leaf(self, task: VideoTask) -> bool:
        latest_validation = self.store.get_latest_validation(task.task_id) or ValidationReport(
            passed=False,
            summary="Recovered after restart",
        )
        auto_repair_decision = self.workflow_engine.auto_repair_service.maybe_schedule_repair(task)
        self.workflow_engine._record_repair_state(task, latest_validation, auto_repair_decision)
        if auto_repair_decision.created:
            self._append_reliability_event(
                task.root_task_id or task.task_id,
                action="auto_repair_created",
                child_task_id=auto_repair_decision.child_task_id,
            )
            return True

        delivery_decision = self.workflow_engine._maybe_schedule_degraded_delivery(task)
        if delivery_decision is None:
            try:
                delivery_decision = self.workflow_engine.delivery_guarantee_service.maybe_deliver(task)
            except Exception:
                delivery_decision = None
        if delivery_decision is None:
            self.workflow_engine._mark_delivery_failed(task, stop_reason="delivery_exception")
            self._append_reliability_event(task.root_task_id or task.task_id, action="delivery_failed", reason="delivery_exception")
            return False
        if delivery_decision.delivered:
            self.workflow_engine._finalize_guaranteed_delivery(task, delivery_decision)
            self._append_reliability_event(
                task.root_task_id or task.task_id,
                action="delivery_completed",
                completion_mode=delivery_decision.completion_mode,
                delivery_tier=delivery_decision.delivery_tier,
            )
            return True
        if delivery_decision.scheduled:
            self._append_reliability_event(
                task.root_task_id or task.task_id,
                action="delivery_scheduled",
                child_task_id=delivery_decision.child_task_id,
                completion_mode=delivery_decision.completion_mode,
            )
            return True
        self.workflow_engine._mark_delivery_failed(task, stop_reason=delivery_decision.reason)
        self._append_reliability_event(
            task.root_task_id or task.task_id,
            action="delivery_failed",
            reason=delivery_decision.reason,
        )
        return False

    def _mark_lineage_runtime_failed(self, task: VideoTask, *, stop_reason: str) -> None:
        self._mark_task_runtime_failed(task, stop_reason=stop_reason)
        root_task_id = task.root_task_id or task.task_id
        if root_task_id != task.task_id:
            root_task = self.store.get_task(root_task_id)
            if root_task is not None:
                self._mark_task_runtime_failed(root_task, stop_reason=stop_reason)
        self._append_reliability_event(root_task_id, action="runtime_unhealthy_failed", reason=stop_reason)

    def _mark_task_runtime_failed(self, task: VideoTask, *, stop_reason: str) -> None:
        task.status = TaskStatus.FAILED
        task.phase = TaskPhase.FAILED
        task.delivery_status = "failed"
        task.delivery_stop_reason = stop_reason
        self.store.update_task(task)
        self.artifact_store.write_task_snapshot(task)

    def _reconcile_stalled_agent_runs(self, root_task: VideoTask) -> bool:
        root_task_id = root_task.root_task_id or root_task.task_id
        root_terminal = root_task.delivery_status in {"delivered", "failed"} or root_task.status in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }
        reconciled = False

        for run in self.store.list_agent_runs(root_task_id):
            if run.status not in {"queued", "running"}:
                continue

            related_task = self.store.get_task(run.task_id) if run.task_id else None
            next_status: str | None = None
            reason: str | None = None

            if run.task_id is not None and related_task is None:
                next_status = "failed"
                reason = "task_missing"
            elif root_terminal:
                next_status = "cancelled"
                reason = "case_terminal"
            elif related_task is not None and related_task.status in {
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            }:
                next_status = "cancelled"
                reason = "task_terminal"

            if next_status is None or reason is None:
                continue

            run.status = next_status
            run.metadata = {**run.metadata, "reliability_stop_reason": reason}
            run.summary = (
                "Stalled agent run cancelled during reconciliation"
                if next_status == "cancelled"
                else "Stalled agent run failed during reconciliation"
            )
            self.store.upsert_agent_run(run)
            self._append_reliability_event(
                root_task_id,
                action="stalled_agent_run_cancelled" if next_status == "cancelled" else "stalled_agent_run_failed",
                run_id=run.run_id,
                role=run.role,
                affected_task_id=run.task_id,
                reason=reason,
            )
            reconciled = True

        return reconciled

    def _reconcile_orphaned_branches(self, root_task: VideoTask) -> bool:
        root_task_id = root_task.root_task_id or root_task.task_id
        lineage = self.store.list_lineage_tasks(root_task_id)
        reconciled = False

        for task in orphaned_lineage_tasks(lineage_tasks=lineage, root_task_id=root_task_id):
            already_failed = (
                task.status is TaskStatus.FAILED
                and task.delivery_status == "failed"
                and task.delivery_stop_reason == "orphaned_branch"
            )
            if already_failed:
                continue

            task.status = TaskStatus.FAILED
            task.phase = TaskPhase.FAILED
            task.delivery_status = "failed"
            task.delivery_stop_reason = "orphaned_branch"
            self.store.update_task(task)
            self.artifact_store.write_task_snapshot(task)
            self._append_reliability_event(
                root_task_id,
                action="orphaned_branch_failed",
                affected_task_id=task.task_id,
                parent_task_id=task.parent_task_id,
            )
            reconciled = True

        if reconciled:
            self._sync_case_state(root_task_id)
        return reconciled

    def _append_reliability_event(self, task_id: str, **payload: object) -> None:
        self.store.append_event(task_id, "task_reliability_reconciled", dict(payload))

    def _sync_case_state(self, root_task_id: str) -> bool:
        delivery_case_service = getattr(self.workflow_engine, "delivery_case_service", None)
        if delivery_case_service is None:
            return False
        before = self.store.get_delivery_case(root_task_id)
        after = delivery_case_service.sync_case_for_root(root_task_id)
        if not self._delivery_case_changed(before, after):
            return False
        if after is not None:
            self._append_reliability_event(
                root_task_id,
                action="sync_case_state",
                case_status=after.status,
                active_task_id=after.active_task_id,
                selected_task_id=after.selected_task_id,
                delivery_status=after.delivery_status,
            )
        return True

    @staticmethod
    def _delivery_case_changed(before, after) -> bool:
        if before is None and after is None:
            return False
        if before is None or after is None:
            return True
        return any(
            getattr(before, field_name) != getattr(after, field_name)
            for field_name in (
                "status",
                "active_task_id",
                "selected_task_id",
                "delivery_status",
                "completion_mode",
                "stop_reason",
            )
        )

    def _iter_root_tasks(self) -> list[VideoTask]:
        roots: list[VideoTask] = []
        seen: set[str] = set()
        for row in self.store.list_tasks(limit=None, order_by="updated_at"):
            task = self.store.get_task(row["task_id"])
            if task is None or task.task_id in seen:
                continue
            if (task.root_task_id or task.task_id) != task.task_id:
                continue
            seen.add(task.task_id)
            roots.append(task)
        return roots

    def _find_leaf_task(self, root_task_id: str) -> VideoTask | None:
        lineage = reachable_lineage_tasks(
            lineage_tasks=self.store.list_lineage_tasks(root_task_id),
            root_task_id=root_task_id,
        )
        if not lineage:
            return None
        return lineage[-1]

    def _find_delivered_descendant(self, root_task_id: str) -> VideoTask | None:
        lineage = reachable_lineage_tasks(
            lineage_tasks=self.store.list_lineage_tasks(root_task_id),
            root_task_id=root_task_id,
        )
        for task in reversed(lineage):
            if task.delivery_status == "delivered" and self._task_has_valid_final_video(task):
                return task
            if task.status is TaskStatus.COMPLETED and self._task_has_valid_final_video(task):
                return task
        return None

    def _reconcile_missing_delivery_artifact(self, root_task: VideoTask, leaf_task: VideoTask) -> str | None:
        root_task_id = root_task.root_task_id or root_task.task_id
        candidate_task_ids: list[str] = []

        if root_task.delivery_status == "delivered":
            candidate_task_ids.append(root_task.resolved_task_id or root_task_id)
        if leaf_task.delivery_status == "delivered" and leaf_task.task_id not in candidate_task_ids:
            candidate_task_ids.append(leaf_task.task_id)

        for candidate_task_id in candidate_task_ids:
            candidate_task = self.store.get_task(candidate_task_id)
            if candidate_task is None or self._task_has_valid_final_video(candidate_task):
                continue

            self._append_reliability_event(
                root_task_id,
                action="missing_final_video_artifact_detected",
                affected_task_id=candidate_task.task_id,
            )
            candidate_task.status = TaskStatus.FAILED
            candidate_task.phase = TaskPhase.FAILED
            candidate_task.delivery_status = "failed"
            candidate_task.delivery_stop_reason = "missing_final_video_artifact"
            self.store.update_task(candidate_task)
            self.artifact_store.write_task_snapshot(candidate_task)

            if self._resume_failed_leaf(candidate_task):
                return "reconciled"
            return "failed"

        return None

    def _task_has_valid_final_video(self, task: VideoTask) -> bool:
        artifacts = self.store.list_artifacts(task.task_id, "final_video")
        for artifact in reversed(artifacts):
            if Path(artifact["path"]).exists():
                return True
        return self.artifact_store.final_video_path(task.task_id).exists()

    def _resolved_delivery_has_valid_video(self, root_task: VideoTask) -> bool:
        resolved_task_id = root_task.resolved_task_id or root_task.task_id
        resolved_task = self.store.get_task(resolved_task_id)
        if resolved_task is None:
            return False
        return self._task_has_valid_final_video(resolved_task)
