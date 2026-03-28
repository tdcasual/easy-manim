from video_agent.adapters.storage.artifact_store import ArtifactStore
from video_agent.domain.scene_spec_models import SceneSpec


def test_artifact_store_roundtrips_scene_spec(tmp_path) -> None:
    store = ArtifactStore(tmp_path / "tasks")
    spec = SceneSpec(task_id="task-1", summary="teach a blue circle", scene_count=1, scenes=[])

    store.write_scene_spec("task-1", spec.model_dump(mode="json"))

    assert store.read_scene_spec("task-1")["summary"] == "teach a blue circle"
