import asyncio
import json
from pathlib import Path

import video_agent.server.app as app_module
from video_agent.config import Settings
from video_agent.server.app import create_app_context
from video_agent.server.fastmcp_server import create_mcp_server


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _build_failing_render_settings(tmp_path: Path) -> Settings:
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

    return Settings(
        data_dir=data_dir,
        database_path=data_dir / "video_agent.db",
        artifact_root=data_dir / "tasks",
        manim_command=str(fake_manim),
        ffmpeg_command=str(fake_ffmpeg),
        ffprobe_command=str(fake_ffprobe),
        run_embedded_worker=False,
    )


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


def test_failed_task_writes_failure_context_artifact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "_build_llm_client", lambda settings: HelperKwargLLMClient(), raising=False)
    app = create_app_context(_build_failing_render_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()

    failure_context_path = app.artifact_store.task_dir(created.task_id) / "artifacts" / "failure_context.json"
    payload = json.loads(failure_context_path.read_text())

    assert payload["task_id"] == created.task_id
    assert payload["failure_code"] == "render_failed"
    assert payload["phase"] == "failed"
    assert payload["summary"] == "Render failed"
    assert "simulated render failure" in payload["stderr"]
    assert payload["failure_contract"]["retryable"] is True
    assert payload["failure_contract"]["blocking_layer"] == "render"
    assert payload["failure_contract"]["recommended_action"] == "auto_repair"
    assert payload["current_script_resource"] == f"video-task://{created.task_id}/artifacts/current_script.py"
    assert any(
        item["code"] == "unsupported_helper_kwargs"
        and item["call_name"] == "get_v_line"
        and item["keywords"] == ["color", "opacity"]
        for item in payload["semantic_diagnostics"]
    )


def test_failure_context_artifact_is_available_as_mcp_resource(tmp_path: Path) -> None:
    settings = _build_failing_render_settings(tmp_path)
    app = create_app_context(settings)
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()

    async def run() -> None:
        mcp = create_mcp_server(settings)
        resource = list(await mcp.read_resource(f"video-task://{created.task_id}/artifacts/failure_context.json"))

        assert resource
        payload = json.loads(resource[0].content)
        assert payload["task_id"] == created.task_id
        assert payload["failure_code"] == "render_failed"
        assert payload["failure_contract"]["retryable"] is True
        assert payload["failure_contract"]["blocking_layer"] == "render"

    asyncio.run(run())
