from video_agent.adapters.storage.artifact_store import ArtifactStore
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.task_service import TaskService


def test_create_task_derives_display_title_from_prompt(temp_settings) -> None:
    store = SQLiteTaskStore(temp_settings.database_path)
    service = TaskService(
        store=store,
        artifact_store=ArtifactStore(temp_settings.artifact_root),
        settings=temp_settings,
    )

    created = service.create_video_task(
        prompt="做一个蓝色圆形开场动画，画面干净简洁",
        idempotency_key="title-derivation",
    )
    stored = store.get_task(created.task_id)

    assert created.task_id
    assert created.display_title == "蓝色圆形开场动画"
    assert created.title_source == "prompt"
    assert len(created.display_title) < len("做一个蓝色圆形开场动画，画面干净简洁")
    assert stored is not None
    assert stored.display_title == "蓝色圆形开场动画"
    assert stored.title_source == "prompt"
