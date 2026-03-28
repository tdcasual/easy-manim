from video_agent.domain.enums import TaskPhase
from video_agent.domain.models import VideoTask
from video_agent.domain.scene_spec_models import SceneSpec, TaskRiskProfile


def test_scene_spec_preserves_summary_and_scenes() -> None:
    spec = SceneSpec(
        task_id="task-1",
        summary="teach a blue circle",
        scene_count=1,
        scenes=[{"name": "intro", "goal": "show the circle"}],
    )

    assert spec.summary == "teach a blue circle"
    assert spec.scene_count == 1
    assert spec.scenes[0]["name"] == "intro"


def test_task_risk_profile_tracks_generation_mode() -> None:
    profile = TaskRiskProfile(
        task_id="task-1",
        risk_level="medium",
        generation_mode="guided_generate",
    )

    assert profile.risk_level == "medium"
    assert profile.generation_mode == "guided_generate"


def test_task_phase_exposes_reliability_phases() -> None:
    assert TaskPhase.RISK_ROUTING == "risk_routing"
    assert TaskPhase.SCENE_PLANNING == "scene_planning"
    assert TaskPhase.PREVIEW_RENDER == "preview_render"
    assert TaskPhase.QUALITY_JUDGING == "quality_judging"


def test_video_task_tracks_reliability_metadata() -> None:
    task = VideoTask(
        prompt="draw a circle",
        risk_level="medium",
        generation_mode="guided_generate",
    )

    assert task.risk_level == "medium"
    assert task.generation_mode == "guided_generate"
    assert task.accepted_as_best is False
