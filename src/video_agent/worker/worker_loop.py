from __future__ import annotations

from typing import Protocol

from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.workflow_engine import WorkflowEngine


class ReliabilitySweepService(Protocol):
    def sweep_watchdog(self) -> dict[str, int]:
        ...


class WorkerLoop:
    def __init__(
        self,
        store: SQLiteTaskStore,
        workflow_engine: WorkflowEngine,
        task_reliability_service: ReliabilitySweepService | None = None,
        worker_id: str = "worker-1",
        lease_seconds: int = 30,
        recovery_grace_seconds: int = 5,
    ) -> None:
        self.store = store
        self.workflow_engine = workflow_engine
        self.task_reliability_service = task_reliability_service
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds
        self.recovery_grace_seconds = recovery_grace_seconds

    def run_once(self) -> int:
        self._record_heartbeat(processed_count=0)
        if self.task_reliability_service is not None:
            self.task_reliability_service.sweep_watchdog()
        task_processing = self.workflow_engine.runtime_service.inspect_task_processing()
        if not task_processing.ready:
            self.workflow_engine.metrics.increment("task_processing_blocked")
            self._record_heartbeat(
                processed_count=0,
                task_processing_ready=False,
                task_processing_reasons=list(task_processing.reasons),
            )
            return 0
        self.store.requeue_stale_tasks(recovery_grace_seconds=self.recovery_grace_seconds)
        task = self.store.claim_next_task(worker_id=self.worker_id, lease_seconds=self.lease_seconds)
        if task is None:
            self._record_heartbeat(processed_count=0)
            return 0
        try:
            self.store.renew_lease(task.task_id, self.worker_id, self.lease_seconds)
            self._record_heartbeat(last_processed_task_id=task.task_id, processed_count=0)
            self.workflow_engine.run_task(task.task_id)
        finally:
            self.store.release_lease(task.task_id, self.worker_id)
            self._record_heartbeat(last_processed_task_id=task.task_id, processed_count=1)
        return 1

    def _record_heartbeat(
        self,
        last_processed_task_id: str | None = None,
        processed_count: int = 0,
        **extra: object,
    ) -> None:
        details = {"processed_count": processed_count, "worker_identity": self.worker_id}
        if last_processed_task_id is not None:
            details["last_processed_task_id"] = last_processed_task_id
        details.update(extra)
        self.store.record_worker_heartbeat(self.worker_id, details)
