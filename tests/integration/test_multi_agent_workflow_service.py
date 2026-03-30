import json
from pathlib import Path
import sys
import types
from collections.abc import Callable

import pytest

from video_agent.application.errors import AdmissionControlError
from video_agent.config import Settings
from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.domain.quality_models import QualityScorecard
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


def _mark_task_completed(app_context, task_id: str) -> None:
    task = app_context.store.get_task(task_id)
    assert task is not None
    task.status = TaskStatus.COMPLETED
    task.phase = TaskPhase.COMPLETED
    task.quality_gate_status = "accepted"
    task.delivery_status = "delivered"
    task.resolved_task_id = task.task_id
    task.completion_mode = "primary" if task.parent_task_id is None else "repaired"
    task.delivery_stop_reason = None
    app_context.store.update_task(task)
    app_context.artifact_store.write_task_snapshot(task)

    root_task_id = task.root_task_id or task.task_id
    root_task = app_context.store.get_task(root_task_id)
    assert root_task is not None
    root_task.status = TaskStatus.COMPLETED
    root_task.phase = TaskPhase.COMPLETED
    root_task.quality_gate_status = "accepted"
    root_task.delivery_status = "delivered"
    root_task.resolved_task_id = task.task_id
    root_task.completion_mode = task.completion_mode
    root_task.delivery_stop_reason = None
    app_context.store.update_task(root_task)
    app_context.artifact_store.write_task_snapshot(root_task)
    app_context.delivery_case_service.sync_case_for_root(root_task_id)


def _set_completed_delivery_outcome(
    app_context,
    task_id: str,
    *,
    quality_gate_status: str,
    total_score: float,
    accepted: bool,
    completion_mode: str,
) -> None:
    task = app_context.store.get_task(task_id)
    assert task is not None
    task.status = TaskStatus.COMPLETED
    task.phase = TaskPhase.COMPLETED
    task.quality_gate_status = quality_gate_status
    task.delivery_status = "delivered"
    task.resolved_task_id = task.task_id
    task.completion_mode = completion_mode
    task.delivery_stop_reason = None
    app_context.store.update_task(task)
    app_context.artifact_store.write_task_snapshot(task)
    app_context.store.upsert_task_quality_score(
        task_id,
        QualityScorecard(
            task_id=task_id,
            total_score=total_score,
            accepted=accepted,
            decision="accept" if accepted else "revise",
            summary="quality accepted" if accepted else "needs revision",
        ),
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
    assert outcome.reason == "revision_created"


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
    assert outcome.reason == "workflow_budget_exhausted"


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
    assert bundle.case_status == "queued"
    assert bundle.active_task_id == created.task_id
    assert bundle.selected_task_id is None
    assert [candidate["task_id"] for candidate in bundle.branch_candidates] == [created.task_id]
    assert any(
        run["role"] == "orchestrator" and run["decision"].get("action") == "case_created"
        for run in bundle.recent_agent_runs
    )


def test_workflow_service_blocks_accept_with_explicit_reason(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_fake_pipeline_settings(tmp_path)))
    created = app_context.task_service.create_video_task(prompt="draw a circle", session_id="session-1")

    outcome = app_context.multi_agent_workflow_service.apply_review_decision(
        task_id=created.task_id,
        review_decision=ReviewDecision(
            decision="accept",
            summary="looks good",
        ),
        session_id="session-1",
        agent_principal=None,
    )

    assert outcome.action == "escalate"
    assert outcome.reason == "acceptance_blocked"


def test_workflow_service_creates_challenger_branch_for_completed_task(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_fake_pipeline_settings(tmp_path)))
    created = app_context.task_service.create_video_task(prompt="draw a circle", session_id="session-1")
    _mark_task_completed(app_context, created.task_id)

    outcome = app_context.multi_agent_workflow_service.apply_review_decision(
        task_id=created.task_id,
        review_decision=ReviewDecision(
            decision="revise",
            summary="Try a stronger alternative",
            feedback="Keep the delivered version, but create a more cinematic challenger",
        ),
        session_id="session-1",
        agent_principal=None,
    )

    case = app_context.store.get_delivery_case(created.task_id)
    runs = app_context.store.list_agent_runs(created.task_id, role="orchestrator")

    assert outcome.action == "revise"
    assert outcome.created_task_id is not None
    assert outcome.reason == "challenger_created"
    assert case is not None
    assert case.status == "branching"
    assert case.selected_task_id == created.task_id
    assert case.active_task_id == outcome.created_task_id
    assert any(
        run.decision.get("action") == "challenger_created"
        and run.decision.get("challenger_task_id") == outcome.created_task_id
        and run.decision.get("incumbent_task_id") == created.task_id
        for run in runs
    )


def test_workflow_service_accepts_completed_task_and_records_winner(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_fake_pipeline_settings(tmp_path)))
    created = app_context.task_service.create_video_task(prompt="draw a circle", session_id="session-1")
    _mark_task_completed(app_context, created.task_id)

    outcome = app_context.multi_agent_workflow_service.apply_review_decision(
        task_id=created.task_id,
        review_decision=ReviewDecision(
            decision="accept",
            summary="This delivered version is the winner",
        ),
        session_id="session-1",
        agent_principal=None,
    )

    accepted = app_context.store.get_task(created.task_id)
    case = app_context.store.get_delivery_case(created.task_id)
    runs = app_context.store.list_agent_runs(created.task_id, role="orchestrator")

    assert outcome.action == "accept"
    assert outcome.reason == "winner_selected"
    assert accepted is not None
    assert accepted.accepted_as_best is True
    assert accepted.accepted_version_rank == 1
    assert case is not None
    assert case.selected_task_id == created.task_id
    assert any(
        run.decision.get("action") == "winner_selected" and run.decision.get("selected_task_id") == created.task_id
        for run in runs
    )


def test_review_bundle_exposes_branch_scoreboard_and_arbitration_summary(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_fake_pipeline_settings(tmp_path)))
    created = app_context.task_service.create_video_task(prompt="draw a circle", session_id="session-1")
    _mark_task_completed(app_context, created.task_id)
    _set_completed_delivery_outcome(
        app_context,
        created.task_id,
        quality_gate_status="needs_revision",
        total_score=0.61,
        accepted=False,
        completion_mode="primary",
    )
    app_context.delivery_case_service.sync_case_for_root(created.task_id)

    challenger = app_context.task_service.revise_video_task(
        created.task_id,
        feedback="Produce a more cinematic challenger version",
        session_id="session-1",
    )
    _set_completed_delivery_outcome(
        app_context,
        challenger.task_id,
        quality_gate_status="accepted",
        total_score=0.94,
        accepted=True,
        completion_mode="repaired",
    )
    app_context.delivery_case_service.sync_case_for_root(created.task_id)

    bundle = app_context.multi_agent_workflow_service.get_review_bundle(created.task_id)

    assert bundle.selected_task_id == created.task_id
    assert [entry["task_id"] for entry in bundle.branch_scoreboard] == [created.task_id, challenger.task_id]
    assert bundle.branch_scoreboard[0]["comparison_label"] == "incumbent"
    assert bundle.branch_scoreboard[0]["overall_score"] == pytest.approx(0.61)
    assert bundle.branch_scoreboard[1]["branch_kind"] == "challenger"
    assert bundle.branch_scoreboard[1]["overall_score"] == pytest.approx(0.94)
    assert bundle.arbitration_summary["recommended_task_id"] == challenger.task_id
    assert bundle.arbitration_summary["recommended_action"] == "promote_challenger"
    assert bundle.arbitration_summary["selected_task_id"] == created.task_id
    assert bundle.arbitration_summary["candidate_count"] == 2


def test_accepting_completed_challenger_records_arbitration_context(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_fake_pipeline_settings(tmp_path)))
    created = app_context.task_service.create_video_task(prompt="draw a circle", session_id="session-1")
    _mark_task_completed(app_context, created.task_id)
    _set_completed_delivery_outcome(
        app_context,
        created.task_id,
        quality_gate_status="needs_revision",
        total_score=0.58,
        accepted=False,
        completion_mode="primary",
    )
    app_context.delivery_case_service.sync_case_for_root(created.task_id)

    challenger = app_context.task_service.revise_video_task(
        created.task_id,
        feedback="Make the result more cinematic and polished",
        session_id="session-1",
    )
    _set_completed_delivery_outcome(
        app_context,
        challenger.task_id,
        quality_gate_status="accepted",
        total_score=0.96,
        accepted=True,
        completion_mode="repaired",
    )
    app_context.delivery_case_service.sync_case_for_root(created.task_id)

    outcome = app_context.multi_agent_workflow_service.apply_review_decision(
        task_id=challenger.task_id,
        review_decision=ReviewDecision(
            decision="accept",
            summary="Promote the stronger challenger",
        ),
        session_id="session-1",
        agent_principal=None,
    )

    case = app_context.store.get_delivery_case(created.task_id)
    root_task = app_context.store.get_task(created.task_id)
    runs = app_context.store.list_agent_runs(created.task_id, role="orchestrator")
    winner_run = runs[-1]

    assert outcome.action == "accept"
    assert outcome.reason == "winner_selected"
    assert case is not None
    assert case.selected_task_id == challenger.task_id
    assert root_task is not None
    assert root_task.resolved_task_id == challenger.task_id
    assert winner_run.decision["action"] == "winner_selected"
    assert winner_run.decision["selected_task_id"] == challenger.task_id
    assert winner_run.decision["previous_selected_task_id"] == created.task_id
    assert winner_run.decision["arbitration_summary"]["recommended_action"] == "promote_challenger"
    assert winner_run.decision["arbitration_summary"]["recommended_task_id"] == challenger.task_id
