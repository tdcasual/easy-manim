import json
from pathlib import Path

import video_agent.server.app as app_module
from video_agent.adapters.llm.openai_compatible_client import ProviderAuthError
from video_agent.config import Settings
from video_agent.server.app import create_app_context


class FailingLLMClient:
    def generate_script(self, prompt_text: str) -> str:
        raise ProviderAuthError("bad key")


class HelperKwargLLMClient:
    def generate_script(self, prompt_text: str) -> str:
        return (
            "from manim import Axes, RED, Scene\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        axes = Axes()\n"
            "        point_a = axes.c2p(1, 2)\n"
            "        helper = axes.get_v_line(point_a, color=RED, opacity=0.5)\n"
            "        self.add(axes, helper)\n"
        )


class BareTexSelectionLLMClient:
    def generate_script(self, prompt_text: str) -> str:
        return (
            "from manim import BLUE, MathTex, MovingCameraScene, SurroundingRectangle\n\n"
            "class GeneratedScene(MovingCameraScene):\n"
            "    def construct(self):\n"
            "        formula = MathTex(r'd = \\\\sqrt{(x_2 - x_1)^2 + (y_2 - y_1)^2}')\n"
            "        sqrt_part = formula.get_part_by_tex(r'\\\\sqrt')\n"
            "        marker = SurroundingRectangle(sqrt_part, color=BLUE)\n"
            "        self.add(formula, marker)\n"
        )


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _build_failing_render_settings(tmp_path: Path, **overrides) -> Settings:
    data_dir = tmp_path / "data"

    fake_manim = tmp_path / "fake_manim_fail.sh"
    _write_executable(
        fake_manim,
        "#!/bin/sh\n"
        "printf 'simulated render failure\\n' >&2\n"
        "exit 17\n",
    )

    fake_ffprobe = tmp_path / "fake_ffprobe.sh"
    probe_json = json.dumps(
        {
            "streams": [{"codec_type": "video", "width": 1280, "height": 720}],
            "format": {"duration": "2.5"},
        }
    )
    _write_executable(fake_ffprobe, f"#!/bin/sh\nprintf '%s' '{probe_json}'\n")

    fake_ffmpeg = tmp_path / "fake_ffmpeg.sh"
    _write_executable(
        fake_ffmpeg,
        "#!/bin/sh\n"
        "mkdir -p \"$2\"\n"
        "printf 'frame1' > \"$2/frame_001.png\"\n",
    )

    values = {
        "data_dir": data_dir,
        "database_path": data_dir / "video_agent.db",
        "artifact_root": data_dir / "tasks",
        "manim_command": str(fake_manim),
        "ffmpeg_command": str(fake_ffmpeg),
        "ffprobe_command": str(fake_ffprobe),
        "run_embedded_worker": False,
        "auto_repair_enabled": True,
        "auto_repair_max_children_per_root": 1,
        "auto_repair_retryable_issue_codes": ["render_failed"],
    }
    values.update(overrides)
    return Settings(**values)


def test_failed_task_can_spawn_auto_revision_within_budget(tmp_path: Path) -> None:
    app = create_app_context(_build_failing_render_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()

    tasks = app.store.list_tasks(limit=10)
    child_ids = [item["task_id"] for item in tasks if item["task_id"] != created.task_id]
    child_task = app.store.get_task(child_ids[0])

    assert len(child_ids) == 1
    assert child_task is not None
    assert child_task.parent_task_id == created.task_id
    assert child_task.status == "queued"
    assert "render_failed" in (child_task.feedback or "")


def test_auto_repair_feedback_includes_semantic_diagnostics(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "_build_llm_client", lambda settings: HelperKwargLLMClient(), raising=False)
    app = create_app_context(_build_failing_render_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()

    tasks = app.store.list_tasks(limit=10)
    child_ids = [item["task_id"] for item in tasks if item["task_id"] != created.task_id]
    child_task = app.store.get_task(child_ids[0])

    assert child_task is not None
    assert "unsupported_helper_kwargs" in (child_task.feedback or "")
    assert "get_v_line" in (child_task.feedback or "")
    assert "color, opacity" in (child_task.feedback or "")


def test_auto_repair_feedback_is_patch_oriented(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "_build_llm_client", lambda settings: HelperKwargLLMClient(), raising=False)
    app = create_app_context(_build_failing_render_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()

    tasks = app.store.list_tasks(limit=10)
    child_ids = [item["task_id"] for item in tasks if item["task_id"] != created.task_id]
    child_task = app.store.get_task(child_ids[0])
    feedback = child_task.feedback or ""

    assert child_task is not None
    assert "Targeted repair only." in feedback
    assert "Preserve working code outside the failing region." in feedback
    assert "Revise only the minimal failing region or behavior." in feedback
    assert "Return a full updated Python script." in feedback
    assert f"video-task://{created.task_id}/artifacts/current_script.py" in feedback


def test_auto_repair_does_not_retry_non_repairable_failure(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "_build_llm_client", lambda settings: FailingLLMClient(), raising=False)
    settings = _build_failing_render_settings(
        tmp_path,
        llm_provider="openai_compatible",
        llm_model="gpt-4.1-mini",
        llm_base_url="https://example.test/v1",
        llm_api_key="secret",
    )
    app = create_app_context(settings)
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()

    tasks = app.store.list_tasks(limit=10)

    assert len(tasks) == 1
    assert tasks[0]["task_id"] == created.task_id


def test_auto_repair_stops_after_child_budget_is_exhausted(tmp_path: Path) -> None:
    app = create_app_context(_build_failing_render_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()
    app.worker.run_once()

    assert app.store.count_lineage_tasks(created.task_id) == 2


def test_auto_repair_retries_bare_tex_selection_failures(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "_build_llm_client", lambda settings: BareTexSelectionLLMClient(), raising=False)
    retryable_codes = Settings().auto_repair_retryable_issue_codes
    app = create_app_context(
        _build_failing_render_settings(
            tmp_path,
            auto_repair_retryable_issue_codes=retryable_codes,
        )
    )
    created = app.task_service.create_video_task(prompt="show the distance formula")

    app.worker.run_once()

    tasks = app.store.list_tasks(limit=10)
    child_ids = [item["task_id"] for item in tasks if item["task_id"] != created.task_id]
    child_task = app.store.get_task(child_ids[0])

    assert len(child_ids) == 1
    assert child_task is not None
    assert child_task.parent_task_id == created.task_id
    assert child_task.status == "queued"
    assert "unsafe_bare_tex_selection" in (child_task.feedback or "")
