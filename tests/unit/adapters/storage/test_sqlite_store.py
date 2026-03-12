from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.domain.models import VideoTask


def test_store_can_insert_and_fetch_task(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    task = VideoTask(prompt="draw a circle")
    store.create_task(task, idempotency_key="abc")

    loaded = store.get_task(task.task_id)
    assert loaded is not None
    assert loaded.prompt == "draw a circle"


def test_idempotency_key_returns_existing_task(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    first = VideoTask(prompt="draw a circle")
    second = VideoTask(prompt="draw another circle")

    created = store.create_task(first, idempotency_key="same")
    duplicate = store.create_task(second, idempotency_key="same")
    assert duplicate.task_id == created.task_id
