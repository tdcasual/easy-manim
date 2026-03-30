from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any

from video_agent.adapters.storage.artifact_store import ArtifactStore
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.branch_arbitration import build_arbitration_summary, build_branch_scoreboard
from video_agent.application.task_service import TaskService
from video_agent.config import Settings
from video_agent.domain.enums import TaskStatus
from video_agent.worker.worker_loop import WorkerLoop

DEFAULT_DELIVERY_CANARY_PROMPT = "draw a circle"
DEFAULT_DELIVERY_CANARY_MODE = "single-branch"
DELIVERY_CANARY_MODES = {"single-branch", "native-multi-agent"}
NATIVE_MULTI_AGENT_ROOT_MIN_SCORE = 0.95
NATIVE_MULTI_AGENT_CHALLENGER_MIN_SCORE = 0.90


class DeliveryCanaryService:
    def __init__(
        self,
        *,
        settings: Settings,
        store: SQLiteTaskStore,
        artifact_store: ArtifactStore,
        task_service: TaskService,
        worker: WorkerLoop,
    ) -> None:
        self.settings = settings
        self.store = store
        self.artifact_store = artifact_store
        self.task_service = task_service
        self.worker = worker

    def run(
        self,
        *,
        prompt: str = DEFAULT_DELIVERY_CANARY_PROMPT,
        max_worker_iterations: int | None = None,
        mode: str = DEFAULT_DELIVERY_CANARY_MODE,
    ) -> dict[str, Any]:
        effective_mode = str(mode).strip().lower()
        if effective_mode not in DELIVERY_CANARY_MODES:
            supported = ", ".join(sorted(DELIVERY_CANARY_MODES))
            raise ValueError(f"Unsupported delivery canary mode '{mode}'. Expected one of: {supported}")
        checked_at = datetime.now(timezone.utc).isoformat()
        started = monotonic()
        task_processing = self.worker.workflow_engine.runtime_service.inspect_task_processing()
        effective_max_iterations = max_worker_iterations or self._default_max_iterations()
        payload_defaults = self._default_mode_payload(mode=effective_mode)

        if not task_processing.ready:
            payload = {
                **payload_defaults,
                "checked_at": checked_at,
                "prompt": prompt,
                "delivered": False,
                "task_id": None,
                "status": "blocked",
                "delivery_status": None,
                "resolved_task_id": None,
                "completion_mode": None,
                "delivery_tier": None,
                "processed_iterations": 0,
                "run_duration_seconds": round(monotonic() - started, 3),
                "video_resource": None,
                "final_video_path": None,
                "artifact_size_bytes": None,
                "video_metadata": None,
                "summary": None,
                "stop_reason": "runtime_unhealthy",
                "task_processing_ready": False,
                "task_processing_reasons": list(task_processing.reasons),
            }
            self._write_latest(payload)
            return payload

        if effective_mode == "native-multi-agent":
            blocked_reason = self._native_multi_agent_blocked_reason()
            if blocked_reason is not None:
                payload = {
                    **payload_defaults,
                    "checked_at": checked_at,
                    "prompt": prompt,
                    "delivered": False,
                    "task_id": None,
                    "status": "blocked",
                    "delivery_status": None,
                    "resolved_task_id": None,
                    "completion_mode": None,
                    "delivery_tier": None,
                    "processed_iterations": 0,
                    "run_duration_seconds": round(monotonic() - started, 3),
                    "video_resource": None,
                    "final_video_path": None,
                    "artifact_size_bytes": None,
                    "video_metadata": None,
                    "summary": None,
                    "stop_reason": blocked_reason,
                    "task_processing_ready": True,
                    "task_processing_reasons": [],
                }
                self._write_latest(payload)
                return payload

        original_guarded_rollout = self.settings.multi_agent_workflow_guarded_rollout_enabled
        original_min_score = self.worker.workflow_engine.quality_judge_service.min_score
        root_task = None
        created = None
        processed_iterations = 0
        lowered_native_threshold = False

        try:
            if effective_mode == "native-multi-agent":
                self.settings.multi_agent_workflow_guarded_rollout_enabled = False
                self.worker.workflow_engine.quality_judge_service.min_score = max(
                    original_min_score,
                    NATIVE_MULTI_AGENT_ROOT_MIN_SCORE,
                )

            created = self.task_service.create_video_task(prompt=prompt)
            root_task = self.store.get_task(created.task_id)

            while processed_iterations < effective_max_iterations:
                processed_iterations += 1
                processed = self.worker.run_once()
                root_task = self.store.get_task(created.task_id)
                if root_task is None:
                    break
                if effective_mode == "native-multi-agent" and not lowered_native_threshold:
                    if self._native_multi_agent_path_started(created.task_id, root_task_id=created.task_id):
                        self.worker.workflow_engine.quality_judge_service.min_score = min(
                            original_min_score,
                            NATIVE_MULTI_AGENT_CHALLENGER_MIN_SCORE,
                        )
                        lowered_native_threshold = True
                if self._can_stop_canary(root_task_id=created.task_id, root_task=root_task, mode=effective_mode):
                    break
                if processed == 0:
                    break
        finally:
            self.worker.workflow_engine.quality_judge_service.min_score = original_min_score
            self.settings.multi_agent_workflow_guarded_rollout_enabled = original_guarded_rollout

        if created is None or root_task is None:
            task_id = None if created is None else created.task_id
            payload = {
                **payload_defaults,
                "checked_at": checked_at,
                "prompt": prompt,
                "delivered": False,
                "task_id": task_id,
                "status": "missing",
                "delivery_status": None,
                "resolved_task_id": None,
                "completion_mode": None,
                "delivery_tier": None,
                "processed_iterations": processed_iterations,
                "run_duration_seconds": round(monotonic() - started, 3),
                "video_resource": None,
                "final_video_path": None,
                "artifact_size_bytes": None,
                "video_metadata": None,
                "summary": None,
                "stop_reason": "task_not_found",
                "task_processing_ready": True,
                "task_processing_reasons": [],
            }
            self._write_latest(payload)
            return payload

        result = self.task_service.get_video_result(created.task_id)
        resolved_task_id = result.resolved_task_id or root_task.resolved_task_id
        final_video_path = None
        artifact_size_bytes = None
        if resolved_task_id is not None:
            candidate = self._final_video_path(resolved_task_id)
            if candidate.exists():
                final_video_path = str(candidate)
                artifact_size_bytes = candidate.stat().st_size

        validation = self.store.get_latest_validation(resolved_task_id) if resolved_task_id is not None else None
        native_details = self._native_multi_agent_details(created.task_id) if effective_mode == "native-multi-agent" else payload_defaults
        delivered = bool(root_task.delivery_status == "delivered" and result.ready and final_video_path is not None)
        if effective_mode == "native-multi-agent":
            delivered = delivered and bool(native_details.get("challenger_created")) and bool(native_details.get("arbitration_promoted"))
        payload = {
            **(native_details if effective_mode == "native-multi-agent" else payload_defaults),
            "checked_at": checked_at,
            "prompt": prompt,
            "delivered": delivered,
            "task_id": created.task_id,
            "status": root_task.status.value,
            "delivery_status": root_task.delivery_status,
            "resolved_task_id": resolved_task_id,
            "completion_mode": root_task.completion_mode,
            "delivery_tier": root_task.delivery_tier,
            "processed_iterations": processed_iterations,
            "run_duration_seconds": round(monotonic() - started, 3),
            "video_resource": result.video_resource,
            "final_video_path": final_video_path,
            "artifact_size_bytes": artifact_size_bytes,
            "video_metadata": None if validation is None or validation.video_metadata is None else validation.video_metadata.model_dump(mode="json"),
            "summary": result.summary,
            "stop_reason": None if delivered else (root_task.delivery_stop_reason or self._mode_specific_stop_reason(effective_mode, native_details)),
            "task_processing_ready": True,
            "task_processing_reasons": [],
        }
        self._write_latest(payload)
        return payload

    def _default_max_iterations(self) -> int:
        return max(3, self.settings.max_attempts_per_root_task + 2)

    @staticmethod
    def _default_mode_payload(*, mode: str) -> dict[str, Any]:
        return {
            "mode": mode,
            "challenger_created": False,
            "challenger_task_id": None,
            "arbitration_evaluated": False,
            "arbitration_promoted": False,
            "lineage_count": 1 if mode == "single-branch" else 0,
            "case_status": None,
            "branch_scoreboard": None,
            "arbitration_summary": None,
        }

    def _native_multi_agent_blocked_reason(self) -> str | None:
        if not self.settings.multi_agent_workflow_enabled:
            return "multi_agent_workflow_disabled"
        if not self.settings.multi_agent_workflow_auto_challenger_enabled:
            return "auto_challenger_disabled"
        if not self.settings.multi_agent_workflow_auto_arbitration_enabled:
            return "auto_arbitration_disabled"
        return None

    def _can_stop_canary(self, *, root_task_id: str, root_task, mode: str) -> bool:
        if root_task.delivery_status == "failed":
            return True
        if mode == "single-branch":
            return root_task.delivery_status == "delivered"
        if root_task.delivery_status != "delivered":
            return False
        delivery_case = self.store.get_delivery_case(root_task_id)
        return delivery_case is None or delivery_case.status == "completed"

    def _native_multi_agent_path_started(self, task_id: str, *, root_task_id: str) -> bool:
        lineage = self.store.list_lineage_tasks(root_task_id)
        if any(task.branch_kind == "challenger" for task in lineage):
            return True
        return any(
            run.decision.get("action") == "challenger_created"
            for run in self.store.list_agent_runs(task_id, role="orchestrator")
        )

    def _native_multi_agent_details(self, root_task_id: str) -> dict[str, Any]:
        delivery_case = self.store.get_delivery_case(root_task_id)
        lineage = self.store.list_lineage_tasks(root_task_id)
        challenger = next((task for task in reversed(lineage) if task.branch_kind == "challenger"), None)
        selected_task_id = None if delivery_case is None else delivery_case.selected_task_id
        active_task_id = None if delivery_case is None else delivery_case.active_task_id
        branch_scoreboard = build_branch_scoreboard(
            lineage_tasks=lineage,
            scorecards_by_task_id={task.task_id: self.task_service.get_quality_score(task.task_id) for task in lineage},
            selected_task_id=selected_task_id,
            active_task_id=active_task_id,
        )
        orchestrator_runs = self.store.list_agent_runs(root_task_id, role="orchestrator")
        arbitration_run = next(
            (run for run in reversed(orchestrator_runs) if run.decision.get("action") == "auto_arbitration_evaluated"),
            None,
        )
        arbitration_summary = None
        if arbitration_run is not None:
            arbitration_summary = dict(arbitration_run.decision)
        elif branch_scoreboard:
            arbitration_summary = build_arbitration_summary(
                branch_scoreboard=branch_scoreboard,
                selected_task_id=selected_task_id,
                active_task_id=active_task_id,
            )
        return {
            "mode": "native-multi-agent",
            "challenger_created": challenger is not None,
            "challenger_task_id": None if challenger is None else challenger.task_id,
            "arbitration_evaluated": arbitration_run is not None,
            "arbitration_promoted": False if arbitration_run is None else bool(arbitration_run.decision.get("promoted")),
            "lineage_count": len(lineage),
            "case_status": None if delivery_case is None else delivery_case.status,
            "branch_scoreboard": branch_scoreboard,
            "arbitration_summary": arbitration_summary,
        }

    @staticmethod
    def _mode_specific_stop_reason(mode: str, details: dict[str, Any]) -> str:
        if mode != "native-multi-agent":
            return "canary_not_delivered"
        if not details.get("challenger_created"):
            return "native_multi_agent_challenger_not_created"
        if not details.get("arbitration_evaluated"):
            return "native_multi_agent_arbitration_not_evaluated"
        if not details.get("arbitration_promoted"):
            return "native_multi_agent_not_promoted"
        return "canary_not_delivered"

    def _final_video_path(self, task_id: str) -> Path:
        return self.artifact_store.task_dir(task_id) / "artifacts" / "final_video.mp4"

    def _write_latest(self, payload: dict[str, Any]) -> Path:
        target = self.settings.eval_root / "delivery-canary" / "latest.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2))
        return target
