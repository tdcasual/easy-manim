import json
from pathlib import Path
import sys
import types
from collections.abc import Callable

import pytest

from video_agent.application.errors import AdmissionControlError
from video_agent.config import Settings
from video_agent.domain.review_workflow_models import ReviewDecision
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

    class _Context:  # pragma: no cover - test import shim
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
    from video_agent.server.app import create_app_context

    return create_app_context(settings)


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _build_fake_pipeline_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"

    fake_manim = tmp_path / "fake_manim.sh"
    _write_executable(
        fake_manim,
        "#!/bin/sh\n"
        "mkdir -p \"$2\"\n"
        "printf 'normal-video' > \"$2/final_video.mp4\"\n",
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

    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            manim_command=str(fake_manim),
            ffmpeg_command=str(fake_ffmpeg),
            ffprobe_command=str(fake_ffprobe),
            multi_agent_workflow_enabled=True,
        )
    )


def test_workflow_service_routes_revision_decision_to_child_task(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_fake_pipeline_settings(tmp_path)))
    created = app_context.task_service.create_video_task(prompt="draw a circle", session_id="session-1")

    outcome = app_context.multi_agent_workflow_service.apply_review_decision(
        task_id=created.task_id,
        review_decision=ReviewDecision(
            decision="revise",
            summary="Needs stronger visual emphasis",
            feedback="Make the circle blue and add a title card",
        ),
        session_id="session-1",
        agent_principal=None,
    )

    assert outcome.action == "revise"
    assert outcome.created_task_id is not None


def test_workflow_service_escalates_when_child_budget_is_exhausted(tmp_path: Path) -> None:
    settings = _build_fake_pipeline_settings(tmp_path)
    settings.multi_agent_workflow_max_child_attempts = 0
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(settings))
    created = app_context.task_service.create_video_task(prompt="draw a circle")

    outcome = app_context.multi_agent_workflow_service.apply_review_decision(
        task_id=created.task_id,
        review_decision=ReviewDecision(
            decision="revise",
            summary="One more pass",
            feedback="Make it blue",
        ),
        session_id=None,
        agent_principal=None,
    )

    assert outcome.action == "escalate"
    assert outcome.created_task_id is None


def test_workflow_service_raises_when_disabled(tmp_path: Path) -> None:
    settings = _build_fake_pipeline_settings(tmp_path)
    settings.multi_agent_workflow_enabled = False
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(settings))
    created = app_context.task_service.create_video_task(prompt="draw a circle")

    with pytest.raises(AdmissionControlError) as exc:
        app_context.multi_agent_workflow_service.apply_review_decision(
            task_id=created.task_id,
            review_decision=ReviewDecision(
                decision="revise",
                summary="needs update",
                feedback="make it blue",
            ),
        )

    assert exc.value.code == "multi_agent_workflow_disabled"


def test_workflow_service_get_review_bundle(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_fake_pipeline_settings(tmp_path)))
    created = app_context.task_service.create_video_task(prompt="draw a circle", session_id="session-1")

    bundle = app_context.multi_agent_workflow_service.get_review_bundle(created.task_id)

    assert bundle.task_id == created.task_id
    assert bundle.root_task_id == created.task_id
    assert bundle.collaboration.planner_recommendation.role == "planner"
    assert bundle.collaboration.reviewer_decision.role == "reviewer"
    assert bundle.collaboration.repairer_execution_hint.role == "repairer"
