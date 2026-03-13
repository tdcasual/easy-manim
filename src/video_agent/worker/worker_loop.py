from __future__ import annotations

from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.workflow_engine import WorkflowEngine


class WorkerLoop:
    def __init__(
        self,
        store: SQLiteTaskStore,
        workflow_engine: WorkflowEngine,
        worker_id: str = "worker-1",
        lease_seconds: int = 30,
        recovery_grace_seconds: int = 5,
    ) -> None:
        self.store = store
        self.workflow_engine = workflow_engine
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds
        self.recovery_grace_seconds = recovery_grace_seconds

    def run_once(self) -> int:
        self._record_heartbeat(processed_count=0)
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

    def _record_heartbeat(self, last_processed_task_id: str | None = None, processed_count: int = 0) -> None:
        details = {"processed_count": processed_count, "worker_identity": self.worker_id}
        if last_processed_task_id is not None:
            details["last_processed_task_id"] = last_processed_task_id
        self.store.record_worker_heartbeat(self.worker_id, details)
