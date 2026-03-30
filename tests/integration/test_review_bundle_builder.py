import json
from pathlib import Path
import sys
import types
from collections.abc import Callable

import pytest

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.application.review_bundle_builder import ReviewBundleBuilder
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.domain.quality_models import QualityScorecard
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
        )
    )


def _build_required_auth_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            run_embedded_worker=False,
            auth_mode="required",
        )
    )


def _seed_required_agent(app_context, agent_id: str, secret: str) -> None:
    app_context.store.upsert_agent_profile(AgentProfile(agent_id=agent_id, name=agent_id))
    app_context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token(secret),
            agent_id=agent_id,
        )
    )


def test_review_bundle_builder_collects_task_result_and_memory(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_fake_pipeline_settings(tmp_path)))
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        session_id="session-1",
    )

    builder = ReviewBundleBuilder(
        task_service=app_context.task_service,
        store=app_context.store,
        session_memory_service=app_context.session_memory_service,
    )
    bundle = builder.build(task_id=created.task_id, agent_principal=None)

    assert bundle.task_id == created.task_id
    assert bundle.root_task_id == created.task_id
    assert bundle.attempt_count == 0
    assert bundle.child_attempt_count == 0
    assert bundle.prompt == "draw a circle"
    assert bundle.feedback is None
    assert bundle.display_title is not None
    assert bundle.status == "queued"
    assert bundle.phase == "queued"
    assert bundle.latest_validation_summary == {}
    assert bundle.failure_contract is None
    assert bundle.task_events
    assert bundle.task_events[0]["event_type"] == "task_created"
    assert bundle.session_memory_summary
    assert "Goal: draw a circle" in bundle.session_memory_summary
    assert bundle.video_resource is None
    assert bundle.preview_frame_resources == []
    assert bundle.script_resource is None
    assert bundle.validation_report_resource is None


def test_review_bundle_builder_respects_agent_scoping(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_required_auth_settings(tmp_path)))
    _seed_required_agent(app_context, "agent-a", "agent-a-secret")
    _seed_required_agent(app_context, "agent-b", "agent-b-secret")
    agent_a = app_context.agent_identity_service.authenticate("agent-a-secret")
    agent_b = app_context.agent_identity_service.authenticate("agent-b-secret")
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        session_id="session-1",
        agent_principal=agent_a,
    )

    builder = ReviewBundleBuilder(
        task_service=app_context.task_service,
        store=app_context.store,
        session_memory_service=app_context.session_memory_service,
    )

    bundle = builder.build(task_id=created.task_id, agent_principal=agent_a)
    assert bundle.task_id == created.task_id

    with pytest.raises(PermissionError):
        builder.build(task_id=created.task_id, agent_principal=agent_b)


def test_review_bundle_builder_derives_acceptance_blockers_and_trace(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_fake_pipeline_settings(tmp_path)))
    created = app_context.task_service.create_video_task(prompt="draw a circle", session_id="session-1")
    task = app_context.store.get_task(created.task_id)
    assert task is not None
    task.status = TaskStatus.FAILED
    task.phase = TaskPhase.FAILED
    task.quality_gate_status = "needs_revision"
    app_context.store.update_task(task)
    app_context.store.upsert_task_quality_score(
        created.task_id,
        QualityScorecard(
            task_id=created.task_id,
            accepted=False,
            must_fix_issues=["timing_overlap"],
        ),
    )
    app_context.artifact_store.write_recovery_plan(
        created.task_id,
        {
            "selected_action": "repair",
            "repair_recipe": "tighten timing and layout",
        },
    )

    builder = ReviewBundleBuilder(
        task_service=app_context.task_service,
        store=app_context.store,
        session_memory_service=app_context.session_memory_service,
    )
    bundle = builder.build(task_id=created.task_id, agent_principal=None)

    assert bundle.must_fix_issue_codes == ["timing_overlap"]
    assert "quality_gate_not_accepted" in bundle.acceptance_blockers
    assert "must_fix_issue_codes" in bundle.acceptance_blockers
    assert bundle.decision_trace["quality_gate_status"] == "needs_revision"
    assert bundle.decision_trace["recovery_selected_action"] == "repair"


def test_review_bundle_builder_exposes_shared_case_memory(tmp_path: Path) -> None:
    settings = _build_fake_pipeline_settings(tmp_path)
    settings.quality_gate_min_score = 0.95
    settings.multi_agent_workflow_enabled = True
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(settings))
    created = app_context.task_service.create_video_task(prompt="draw a circle", session_id="session-1")

    app_context.worker.run_once()

    builder = ReviewBundleBuilder(
        task_service=app_context.task_service,
        store=app_context.store,
        session_memory_service=app_context.session_memory_service,
    )
    bundle = builder.build(task_id=created.task_id, agent_principal=None)

    assert bundle.case_memory["planner_notes"]
    assert bundle.case_memory["review_findings"]
    assert bundle.case_memory["repair_constraints"]
    assert bundle.case_memory["delivery_invariants"]
