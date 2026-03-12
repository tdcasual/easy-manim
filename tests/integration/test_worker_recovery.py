from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.server.app import create_app_context



def test_worker_renews_lease_for_long_running_task(temp_settings) -> None:
    app = create_app_context(temp_settings)
    created = app.task_service.create_video_task(prompt="draw a circle")

    claimed = app.store.claim_next_task(worker_id="worker-a", lease_seconds=1)
    assert claimed is not None
    app.store.renew_lease(claimed.task_id, worker_id="worker-a", lease_seconds=30)

    leased = app.store.claim_next_task(worker_id="worker-b", lease_seconds=1)
    assert leased is None
    assert created.task_id == claimed.task_id



def test_stale_running_task_can_be_recovered(temp_settings) -> None:
    app = create_app_context(temp_settings)
    created = app.task_service.create_video_task(prompt="draw a circle")

    claimed = app.store.claim_next_task(worker_id="worker-a", lease_seconds=0)
    assert claimed is not None
    claimed.status = TaskStatus.RUNNING
    claimed.phase = TaskPhase.RENDERING
    app.store.update_task(claimed)

    app.store.requeue_stale_tasks()
    recovered = app.store.claim_next_task(worker_id="worker-b", lease_seconds=30)

    assert recovered is not None
    assert recovered.task_id == created.task_id
