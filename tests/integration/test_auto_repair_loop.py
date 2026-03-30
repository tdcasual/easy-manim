import json
import sys
from pathlib import Path

import video_agent.server.app as app_module
from video_agent.adapters.llm.client import ProviderAuthError
from video_agent.config import Settings
from video_agent.server.app import create_app_context
from tests.support import bootstrapped_settings


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


class SequenceLLMClient:
    def __init__(self, scripts: list[str]) -> None:
        self._scripts = list(scripts)
        self._fallback = scripts[-1] if scripts else ""

    def generate_script(self, prompt_text: str) -> str:
        return self._scripts.pop(0) if self._scripts else self._fallback


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
        "delivery_guarantee_enabled": False,
        "auto_repair_max_children_per_root": 1,
        "auto_repair_retryable_issue_codes": ["render_failed"],
    }
    values.update(overrides)
    return bootstrapped_settings(Settings(**values))


def _build_preview_sensitive_settings(tmp_path: Path, **overrides) -> Settings:
    data_dir = tmp_path / "data"

    fake_manim = tmp_path / "fake_manim_preview.sh"
    _write_executable(
        fake_manim,
        "#!/bin/sh\n"
        "if [ \"$1\" != \"-ql\" ]; then exit 11; fi\n"
        "if [ \"$4\" != \"--media_dir\" ]; then exit 12; fi\n"
        "if [ \"$6\" != \"-o\" ]; then exit 13; fi\n"
        "script_name=$(basename \"$2\" .py)\n"
        "mkdir -p \"$5/videos/$script_name/480p15\"\n"
        "if grep -q \"MOTION_MARKER\" \"$2\"; then\n"
        "  printf 'animated-video' > \"$5/videos/$script_name/480p15/$7\"\n"
        "elif grep -q \"config.background_color = '#F7F4EA'\" \"$2\"; then\n"
        "  printf 'bright-video' > \"$5/videos/$script_name/480p15/$7\"\n"
        "else\n"
        "  printf 'dark-video' > \"$5/videos/$script_name/480p15/$7\"\n"
        "fi\n",
    )

    fake_ffprobe = tmp_path / "fake_ffprobe_preview.sh"
    probe_json = json.dumps(
        {
            "streams": [{"codec_type": "video", "width": 1280, "height": 720}],
            "format": {"duration": "2.5"},
        }
    )
    _write_executable(
        fake_ffprobe,
        "#!/bin/sh\n"
        "if [ \"$1\" != \"-v\" ]; then exit 31; fi\n"
        f"printf '%s' '{probe_json}'\n",
    )

    fake_ffmpeg = tmp_path / "fake_ffmpeg_preview.sh"
    _write_executable(
        fake_ffmpeg,
        "#!/bin/sh\n"
        "if [ \"$1\" != \"-y\" ]; then exit 20; fi\n"
        "if [ \"$2\" != \"-i\" ]; then exit 21; fi\n"
        "if [ \"$4\" != \"-vf\" ]; then exit 22; fi\n"
        f"\"{sys.executable}\" - \"$3\" \"$6\" <<'PY'\n"
        "from pathlib import Path\n"
        "from PIL import Image\n"
        "import sys\n"
        "\n"
        "video_path = Path(sys.argv[1])\n"
        "output_pattern = Path(sys.argv[2])\n"
        "output_dir = output_pattern.parent\n"
        "output_dir.mkdir(parents=True, exist_ok=True)\n"
        "video_marker = video_path.read_bytes()\n"
        "if b'animated-video' in video_marker:\n"
        "    colors = [(247, 244, 234), (220, 235, 255), (255, 230, 210)]\n"
        "elif b'bright-video' in video_marker:\n"
        "    colors = [(247, 244, 234), (247, 244, 234), (247, 244, 234)]\n"
        "else:\n"
        "    colors = [(0, 0, 0), (0, 0, 0), (0, 0, 0)]\n"
        "for index, rgb in enumerate(colors, start=1):\n"
        "    Image.new('RGB', (320, 180), rgb).save(output_dir / f'frame_{index:03d}.png')\n"
        "PY\n",
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
        "delivery_guarantee_enabled": False,
        "auto_repair_retryable_issue_codes": Settings().auto_repair_retryable_issue_codes,
    }
    values.update(overrides)
    return bootstrapped_settings(Settings(**values))


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
        llm_provider="litellm",
        llm_model="gpt-4.1-mini",
        llm_api_base="https://example.test/v1",
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


def test_auto_repair_child_keeps_parent_session_scope(tmp_path: Path) -> None:
    app = create_app_context(_build_failing_render_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a circle", session_id="session-1")

    app.worker.run_once()

    tasks = app.store.list_tasks(limit=10)
    child_ids = [item["task_id"] for item in tasks if item["task_id"] != created.task_id]
    child_task = app.store.get_task(child_ids[0])

    assert child_task is not None
    assert child_task.session_id == "session-1"
    assert child_task.memory_context_summary is not None


def test_auto_repair_feedback_carries_session_memory_summary(tmp_path: Path) -> None:
    app = create_app_context(
        _build_failing_render_settings(
            tmp_path,
            auto_repair_max_children_per_root=2,
        )
    )
    created = app.task_service.create_video_task(prompt="draw a circle", session_id="session-1")
    app.task_service.revise_video_task(created.task_id, feedback="keep the light background")

    app.worker.run_once()

    tasks = app.store.list_tasks(limit=10)
    auto_repair_task = next(
        (
            candidate
            for item in tasks
            if (candidate := app.store.get_task(item["task_id"])) is not None
            and item["task_id"] != created.task_id
            and "Targeted repair only." in (candidate.feedback or "")
        ),
        None,
    )

    assert auto_repair_task is not None
    assert "Session memory context:" in (auto_repair_task.feedback or "")


def test_auto_repair_default_budget_allows_preview_fix_after_formula_repair(tmp_path: Path, monkeypatch) -> None:
    static_preview_repair_script = (
        "from manim import BLACK, BLUE, Circle, Create, Scene, Text, UP, config\n\n"
        "config.background_color = '#F7F4EA'\n\n"
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        "        title = Text('Distance formula', font_size=30, color=BLACK).to_edge(UP)\n"
        "        circle = Circle(color=BLUE)\n"
        "        self.add(title)\n"
        "        self.play(Create(circle))\n"
    )
    animated_preview_repair_script = (
        "from manim import BLACK, BLUE, Circle, Create, Scene, Text, UP, config\n\n"
        "config.background_color = '#F7F4EA'\n\n"
        "# MOTION_MARKER\n"
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        "        title = Text('Distance formula', font_size=30, color=BLACK).to_edge(UP)\n"
        "        circle = Circle(color=BLUE)\n"
        "        self.add(title)\n"
        "        self.play(Create(circle))\n"
    )
    monkeypatch.setattr(
        app_module,
        "_build_llm_client",
        lambda settings: SequenceLLMClient(
            [
                BareTexSelectionLLMClient().generate_script(""),
                static_preview_repair_script,
                animated_preview_repair_script,
            ]
        ),
        raising=False,
    )
    app = create_app_context(_build_preview_sensitive_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="show the distance formula")

    for _ in range(3):
        app.worker.run_once()

    root_snapshot = app.task_service.get_video_task(created.task_id)
    latest_child_id = root_snapshot.auto_repair_summary["latest_child_task_id"]
    terminal_snapshot = app.task_service.get_video_task(latest_child_id)

    assert app.store.count_lineage_tasks(created.task_id) == 3
    assert root_snapshot.repair_state["child_count"] == 2
    assert terminal_snapshot.status == "completed"
    assert terminal_snapshot.latest_validation_summary["passed"] is True


def test_preview_repair_feedback_preserves_formula_guardrails(tmp_path: Path, monkeypatch) -> None:
    static_preview_repair_script = (
        "from manim import BLACK, BLUE, Circle, Create, Scene, Text, UP, config\n\n"
        "config.background_color = '#F7F4EA'\n\n"
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        "        title = Text('Distance formula', font_size=30, color=BLACK).to_edge(UP)\n"
        "        circle = Circle(color=BLUE)\n"
        "        self.add(title)\n"
        "        self.play(Create(circle))\n"
    )
    monkeypatch.setattr(
        app_module,
        "_build_llm_client",
        lambda settings: SequenceLLMClient(
            [
                BareTexSelectionLLMClient().generate_script(""),
                static_preview_repair_script,
                static_preview_repair_script,
            ]
        ),
        raising=False,
    )
    app = create_app_context(_build_preview_sensitive_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="show the distance formula")

    app.worker.run_once()
    app.worker.run_once()

    root_snapshot = app.task_service.get_video_task(created.task_id)
    child_task_id = root_snapshot.auto_repair_summary["latest_child_task_id"]
    child_task = app.store.get_task(child_task_id)

    assert child_task is not None
    assert "Preserve previously fixed constraints." in (child_task.feedback or "")
    assert "unsafe_bare_tex_selection" in (child_task.feedback or "")
    assert "Do not call get_part_by_tex on a bare TeX control sequence" in (child_task.feedback or "")
