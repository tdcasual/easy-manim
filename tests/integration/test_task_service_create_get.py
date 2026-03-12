from video_agent.application.task_service import TaskService
from video_agent.adapters.storage.artifact_store import ArtifactStore
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore



def test_create_task_returns_poll_metadata(temp_settings) -> None:
    store = SQLiteTaskStore(temp_settings.database_path)
    store.initialize()
    service = TaskService(store=store, artifact_store=ArtifactStore(temp_settings.artifact_root), settings=temp_settings)

    result = service.create_video_task(prompt="draw a circle", idempotency_key="k1")
    assert result.task_id
    assert result.status == "queued"
    assert result.poll_after_ms == 2000



def test_get_task_returns_snapshot(temp_settings) -> None:
    store = SQLiteTaskStore(temp_settings.database_path)
    store.initialize()
    service = TaskService(store=store, artifact_store=ArtifactStore(temp_settings.artifact_root), settings=temp_settings)

    created = service.create_video_task(prompt="draw a circle", idempotency_key="k2")
    snapshot = service.get_video_task(created.task_id)
    assert snapshot.task_id == created.task_id
    assert snapshot.phase == "queued"
