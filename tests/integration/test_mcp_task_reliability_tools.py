import json
from collections.abc import Callable
from pathlib import Path
import sys
import types

from video_agent.config import Settings
from tests.support import bootstrapped_settings


def _with_temporary_mcp_shim(fn: Callable[[], object]) -> object:
    if "mcp.server.fastmcp" in sys.modules:
        return fn()

    injected: dict[str, types.ModuleType] = {}
    original: dict[str, types.ModuleType] = {}
    module_names = ("mcp", "mcp.server", "mcp.server.fastmcp")
    for name in module_names:
        module = sys.modules.get(name)
        if module is not None:
            original[name] = module

    mcp_module = types.ModuleType("mcp")
    mcp_server_module = types.ModuleType("mcp.server")
    mcp_fastmcp_module = types.ModuleType("mcp.server.fastmcp")

    class _Context:  # pragma: no cover - import shim
        pass

    mcp_fastmcp_module.Context = _Context
    mcp_server_module.fastmcp = mcp_fastmcp_module
    mcp_module.server = mcp_server_module

    injected["mcp"] = mcp_module
    injected["mcp.server"] = mcp_server_module
    injected["mcp.server.fastmcp"] = mcp_fastmcp_module

    try:
        sys.modules.update(injected)
        return fn()
    finally:
        for name in module_names:
            previous = original.get(name)
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


def _create_app_context(settings: Settings):
    def _load():
        from video_agent.server.app import create_app_context

        return create_app_context(settings)

    return _with_temporary_mcp_shim(_load)


def _load_mcp_tools():
    def _load():
        from video_agent.server.mcp_tools import (
            create_video_task_tool,
            get_quality_score_tool,
            get_recovery_plan_tool,
            get_review_bundle_tool,
            get_scene_spec_tool,
        )

        return (
            create_video_task_tool,
            get_scene_spec_tool,
            get_quality_score_tool,
            get_recovery_plan_tool,
            get_review_bundle_tool,
        )

    return _with_temporary_mcp_shim(_load)


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _build_fake_pipeline_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"

    fake_manim = tmp_path / "fake_manim.sh"
    _write_executable(
        fake_manim,
        "#!/bin/sh\n"
        "script_name=$(basename \"$2\" .py)\n"
        "mkdir -p \"$5/videos/$script_name/480p15\"\n"
        "printf 'normal-video' > \"$5/videos/$script_name/480p15/$7\"\n",
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
        "mkdir -p \"$(dirname \"$6\")\"\n"
        "printf 'frame1' > \"$(dirname \"$6\")/frame_001.png\"\n",
    )

    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            manim_command=str(fake_manim),
            ffmpeg_command=str(fake_ffmpeg),
            ffprobe_command=str(fake_ffprobe),
            run_embedded_worker=False,
            multi_agent_workflow_enabled=True,
        )
    )


def _build_preview_failure_settings(tmp_path: Path) -> Settings:
    settings = _build_fake_pipeline_settings(tmp_path)

    fake_ffmpeg = tmp_path / "fake_ffmpeg_blank.sh"
    _write_executable(
        fake_ffmpeg,
        "#!/bin/sh\n"
        "python3 - \"$6\" <<'PY'\n"
        "from pathlib import Path\n"
        "from PIL import Image\n"
        "import sys\n"
        "pattern = Path(sys.argv[1])\n"
        "pattern.parent.mkdir(parents=True, exist_ok=True)\n"
        "for index in (1, 2):\n"
        "    Image.new('RGB', (320, 180), (0, 0, 0)).save(pattern.parent / f'frame_{index:03d}.png')\n"
        "PY\n",
    )
    settings.ffmpeg_command = str(fake_ffmpeg)
    return settings


def test_mcp_reliability_tools_return_scene_spec_quality_and_bundle(tmp_path: Path) -> None:
    app_context = _create_app_context(_build_fake_pipeline_settings(tmp_path))
    create_video_task_tool, get_scene_spec_tool, get_quality_score_tool, _, get_review_bundle_tool = _load_mcp_tools()

    created = create_video_task_tool(app_context, {"prompt": "draw a blue circle and label the radius"})
    app_context.worker.run_once()

    scene_spec = get_scene_spec_tool(app_context, {"task_id": created["task_id"]})
    quality = get_quality_score_tool(app_context, {"task_id": created["task_id"]})
    bundle = get_review_bundle_tool(app_context, {"task_id": created["task_id"]})

    assert scene_spec["scene_spec"]["summary"]
    assert "total_score" in quality["quality_score"]
    assert bundle["scene_spec"] is not None
    assert bundle["quality_scorecard"] is not None
    assert bundle["quality_gate_status"] == "accepted"


def test_mcp_reliability_tools_return_recovery_plan(tmp_path: Path) -> None:
    app_context = _create_app_context(_build_preview_failure_settings(tmp_path))
    create_video_task_tool, _, _, get_recovery_plan_tool, get_review_bundle_tool = _load_mcp_tools()

    created = create_video_task_tool(app_context, {"prompt": "draw a circle"})
    app_context.worker.run_once()

    recovery = get_recovery_plan_tool(app_context, {"task_id": created["task_id"]})
    bundle = get_review_bundle_tool(app_context, {"task_id": created["task_id"]})

    assert recovery["recovery_plan"]["selected_action"] == "preview_repair"
    assert bundle["recovery_plan"] is not None
    assert bundle["recovery_plan"]["selected_action"] == "preview_repair"
