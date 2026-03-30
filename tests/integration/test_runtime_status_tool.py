from pathlib import Path

from fastapi.testclient import TestClient

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.domain.validation_models import ValidationReport
from video_agent.server.app import create_app_context
from video_agent.server.http_api import create_http_api
from video_agent.server.mcp_tools import get_runtime_status_tool
from tests.support import bootstrapped_settings


def _write_executable(path: Path) -> None:
    path.write_text("#!/bin/sh\nexit 0\n")
    path.chmod(0o755)


def test_runtime_status_tool_reports_binary_and_provider_state(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    fake_latex = tmp_path / "fake_latex.sh"
    fake_dvisvgm = tmp_path / "fake_dvisvgm.sh"
    _write_executable(fake_latex)
    _write_executable(fake_dvisvgm)
    settings = Settings(
        data_dir=data_dir,
        database_path=data_dir / "video_agent.db",
        artifact_root=data_dir / "tasks",
        manim_command="manim",
        ffmpeg_command="ffmpeg",
        ffprobe_command="ffprobe",
        latex_command=str(fake_latex),
        dvisvgm_command=str(fake_dvisvgm),
        llm_provider="stub",
        run_embedded_worker=False,
    )
    SQLiteBootstrapper(settings.database_path).bootstrap()
    context = create_app_context(settings)

    payload = get_runtime_status_tool(context, {})

    assert payload["provider"]["mode"] == "stub"
    assert payload["provider"]["api_base_present"] is False
    assert payload["storage"]["data_dir"].endswith("data")
    assert set(payload["checks"]).issuperset({"manim", "ffmpeg", "ffprobe", "latex", "dvisvgm"})
    assert payload["features"]["mathtex"]["available"] is True
    assert payload["features"]["mathtex"]["checked"] is False
    assert payload["features"]["mathtex"]["missing_checks"] == []
    assert payload["features"]["mathtex"]["smoke_error"] is None
    assert payload["worker"]["embedded"] is False
    assert payload["sandbox"]["network_disabled"] is False
    assert payload["sandbox"]["temp_root_allowed"] is True
    assert payload["sandbox"]["process_limit"] is None
    assert payload["sandbox"]["memory_limit_mb"] is None
    assert payload["release"]["version"]
    assert payload["release"]["channel"] == "beta"
    assert payload["task_processing"]["ready"] is True
    assert payload["task_processing"]["reasons"] == []
    assert payload["task_processing"]["artifact_root_writable"] is True
    assert payload["task_processing"]["database_writable"] is True
    assert payload["task_processing"]["core_binaries_available"] is True
    assert payload["capabilities"]["rollout_profile"] == "supervised"
    assert payload["capabilities"]["effective"] == {
        "agent_learning_auto_apply_enabled": False,
        "auto_repair_enabled": True,
        "delivery_guarantee_enabled": True,
        "multi_agent_workflow_enabled": True,
        "multi_agent_workflow_auto_challenger_enabled": True,
        "multi_agent_workflow_auto_arbitration_enabled": True,
        "multi_agent_workflow_guarded_rollout_enabled": False,
        "strategy_promotion_enabled": False,
        "strategy_promotion_guarded_auto_apply_enabled": False,
    }
    assert payload["autonomy_guard"]["enabled"] is False
    assert payload["autonomy_guard"]["allowed"] is True
    assert payload["autonomy_guard"]["reasons"] == []


def test_http_runtime_status_returns_payload_when_auth_optional(tmp_path: Path) -> None:
    settings = bootstrapped_settings(
        Settings(
            data_dir=tmp_path / "data",
            database_path=tmp_path / "data" / "video_agent.db",
            artifact_root=tmp_path / "data" / "tasks",
            auth_mode="optional",
            capability_rollout_profile="supervised",
            run_embedded_worker=False,
        )
    )
    client = TestClient(create_http_api(settings))

    response = client.get("/api/runtime/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["capabilities"]["rollout_profile"] == "supervised"
    assert payload["task_processing"]["ready"] is True
    assert payload["capabilities"]["effective"] == {
        "agent_learning_auto_apply_enabled": False,
        "auto_repair_enabled": True,
        "delivery_guarantee_enabled": True,
        "multi_agent_workflow_enabled": True,
        "multi_agent_workflow_auto_challenger_enabled": True,
        "multi_agent_workflow_auto_arbitration_enabled": True,
        "multi_agent_workflow_guarded_rollout_enabled": False,
        "strategy_promotion_enabled": False,
        "strategy_promotion_guarded_auto_apply_enabled": False,
    }


def test_http_runtime_status_requires_auth_when_mode_required(tmp_path: Path) -> None:
    settings = bootstrapped_settings(
        Settings(
            data_dir=tmp_path / "data",
            database_path=tmp_path / "data" / "video_agent.db",
            artifact_root=tmp_path / "data" / "tasks",
            auth_mode="required",
            run_embedded_worker=False,
        )
    )
    client = TestClient(create_http_api(settings))

    response = client.get("/api/runtime/status")

    assert response.status_code == 401
    assert response.json()["detail"] == "missing_session_token"


def test_http_runtime_status_allows_authenticated_read_scope(tmp_path: Path) -> None:
    settings = bootstrapped_settings(
        Settings(
            data_dir=tmp_path / "data",
            database_path=tmp_path / "data" / "video_agent.db",
            artifact_root=tmp_path / "data" / "tasks",
            auth_mode="required",
            run_embedded_worker=False,
        )
    )
    client = TestClient(create_http_api(settings))
    context = client.app.state.app_context
    context.store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A",
            profile_json={"style_hints": {"tone": "patient"}},
        )
    )
    context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token("agent-a-secret"),
            agent_id="agent-a",
            scopes_json={"allow": ["task:read"]},
        )
    )

    login = client.post("/api/sessions", json={"agent_token": "agent-a-secret"})
    session_token = login.json()["session_token"]

    response = client.get("/api/runtime/status", headers={"Authorization": f"Bearer {session_token}"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["capabilities"]["rollout_profile"] == "supervised"
    assert payload["capabilities"]["effective"]["auto_repair_enabled"] is True
    assert payload["capabilities"]["effective"]["delivery_guarantee_enabled"] is True
    assert payload["capabilities"]["effective"]["multi_agent_workflow_auto_challenger_enabled"] is True
    assert payload["capabilities"]["effective"]["multi_agent_workflow_auto_arbitration_enabled"] is True
    assert payload["capabilities"]["effective"]["multi_agent_workflow_guarded_rollout_enabled"] is False
    assert payload["task_processing"]["ready"] is True


def test_runtime_status_reports_blocked_autonomy_guard_when_canary_missing(tmp_path: Path) -> None:
    settings = bootstrapped_settings(
        Settings(
            data_dir=tmp_path / "data",
            database_path=tmp_path / "data" / "video_agent.db",
            artifact_root=tmp_path / "data" / "tasks",
            capability_rollout_profile="autonomy-guarded",
            run_embedded_worker=False,
        )
    )
    context = create_app_context(settings)

    payload = get_runtime_status_tool(context, {})

    assert payload["capabilities"]["rollout_profile"] == "autonomy-guarded"
    assert payload["capabilities"]["effective"]["multi_agent_workflow_guarded_rollout_enabled"] is True
    assert payload["autonomy_guard"]["enabled"] is True
    assert payload["autonomy_guard"]["allowed"] is False
    assert payload["autonomy_guard"]["reasons"] == ["delivery_canary_unavailable"]


def test_runtime_status_reports_task_processing_unready_when_artifact_root_is_not_writable(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    artifact_root = tmp_path / "artifact-root-file"
    artifact_root.write_text("not-a-directory")
    settings = Settings(
        data_dir=data_dir,
        database_path=data_dir / "video_agent.db",
        artifact_root=artifact_root,
        manim_command="manim",
        ffmpeg_command="ffmpeg",
        ffprobe_command="ffprobe",
        run_embedded_worker=False,
    )
    SQLiteBootstrapper(settings.database_path).bootstrap()
    context = create_app_context(settings)

    payload = get_runtime_status_tool(context, {})

    assert payload["task_processing"]["ready"] is False
    assert payload["task_processing"]["artifact_root_writable"] is False
    assert "artifact_root_not_writable" in payload["task_processing"]["reasons"]


def test_runtime_status_reports_task_processing_unready_when_core_binaries_are_missing(tmp_path: Path) -> None:
    settings = bootstrapped_settings(
        Settings(
            data_dir=tmp_path / "data",
            database_path=tmp_path / "data" / "video_agent.db",
            artifact_root=tmp_path / "data" / "tasks",
            manim_command="definitely-missing-manim-binary",
            ffprobe_command="definitely-missing-ffprobe-binary",
            run_embedded_worker=False,
        )
    )
    context = create_app_context(settings)

    payload = get_runtime_status_tool(context, {})

    assert payload["task_processing"]["ready"] is False
    assert payload["task_processing"]["core_binaries_available"] is False
    assert "missing_core_binary:manim" in payload["task_processing"]["reasons"]
    assert "missing_core_binary:ffprobe" in payload["task_processing"]["reasons"]


def test_runtime_status_reports_delivery_summary_for_root_tasks(tmp_path: Path) -> None:
    settings = bootstrapped_settings(
        Settings(
            data_dir=tmp_path / "data",
            database_path=tmp_path / "data" / "video_agent.db",
            artifact_root=tmp_path / "data" / "tasks",
            run_embedded_worker=False,
        )
    )
    context = create_app_context(settings)

    delivered = context.task_service.create_video_task(prompt="draw a circle")
    failed = context.task_service.create_video_task(prompt="draw a square")
    emergency = context.task_service.create_video_task(prompt="draw a triangle")

    delivered_task = context.store.get_task(delivered.task_id)
    failed_task = context.store.get_task(failed.task_id)
    emergency_task = context.store.get_task(emergency.task_id)
    assert delivered_task is not None and failed_task is not None and emergency_task is not None

    delivered_task.status = TaskStatus.COMPLETED
    delivered_task.phase = TaskPhase.COMPLETED
    delivered_task.delivery_status = "delivered"
    delivered_task.completion_mode = "primary"
    context.store.update_task(delivered_task)

    failed_task.status = TaskStatus.FAILED
    failed_task.phase = TaskPhase.FAILED
    failed_task.delivery_status = "failed"
    failed_task.delivery_stop_reason = "runtime_unhealthy"
    context.store.update_task(failed_task)

    emergency_task.status = TaskStatus.COMPLETED
    emergency_task.phase = TaskPhase.COMPLETED
    emergency_task.delivery_status = "delivered"
    emergency_task.completion_mode = "emergency_fallback"
    context.store.update_task(emergency_task)

    payload = get_runtime_status_tool(context, {})

    assert payload["delivery_summary"]["total_roots"] == 3
    assert payload["delivery_summary"]["delivered_roots"] == 2
    assert payload["delivery_summary"]["failed_roots"] == 1
    assert payload["delivery_summary"]["pending_roots"] == 0
    assert payload["delivery_summary"]["delivery_rate"] == 2 / 3
    assert payload["delivery_summary"]["emergency_fallback_rate"] == 1 / 3
    assert payload["delivery_summary"]["completion_modes"] == {
        "emergency_fallback": 1,
        "primary": 1,
    }
    assert payload["delivery_summary"]["branch_rejection_rate"] == 0.0
    assert payload["delivery_summary"]["arbitration_success_rate"] == 0.0
    assert payload["delivery_summary"]["repair_loop_saturation_rate"] == 0.0
    assert payload["delivery_summary"]["top_stop_reasons"][0] == {
        "reason": "runtime_unhealthy",
        "count": 1,
    }


def test_runtime_status_delivery_summary_exposes_multi_agent_slo_metrics(tmp_path: Path) -> None:
    settings = bootstrapped_settings(
        Settings(
            data_dir=tmp_path / "data",
            database_path=tmp_path / "data" / "video_agent.db",
            artifact_root=tmp_path / "data" / "tasks",
            run_embedded_worker=False,
        )
    )
    context = create_app_context(settings)

    primary = context.task_service.create_video_task(prompt="draw a circle")
    primary_task = context.store.get_task(primary.task_id)
    assert primary_task is not None
    primary_task.status = TaskStatus.COMPLETED
    primary_task.phase = TaskPhase.COMPLETED
    primary_task.delivery_status = "delivered"
    primary_task.completion_mode = "primary"
    primary_task.resolved_task_id = primary_task.task_id
    context.store.update_task(primary_task)

    promoted_root = context.task_service.create_video_task(prompt="draw a square")
    promoted_root_task = context.store.get_task(promoted_root.task_id)
    assert promoted_root_task is not None
    promoted_root_task.status = TaskStatus.COMPLETED
    promoted_root_task.phase = TaskPhase.COMPLETED
    promoted_root_task.delivery_status = "delivered"
    promoted_root_task.completion_mode = "primary"
    promoted_root_task.resolved_task_id = promoted_root_task.task_id
    context.store.update_task(promoted_root_task)
    promoted_child = context.task_service.create_challenger_task(
        promoted_root.task_id,
        feedback="raise quality",
    )
    promoted_child_task = context.store.get_task(promoted_child.task_id)
    assert promoted_child_task is not None
    promoted_child_task.status = TaskStatus.COMPLETED
    promoted_child_task.phase = TaskPhase.COMPLETED
    promoted_child_task.delivery_status = "delivered"
    promoted_child_task.quality_gate_status = "accepted"
    promoted_child_task.completion_mode = "repaired"
    context.store.update_task(promoted_child_task)
    context.delivery_case_service.record_auto_arbitration_evaluated(
        task=promoted_child_task,
        arbitration_summary={
            "recommended_task_id": promoted_child_task.task_id,
            "recommended_action": "promote_challenger",
            "selected_task_id": promoted_child_task.task_id,
            "candidate_count": 2,
            "reason": "challenger_has_best_accepted_score",
        },
        promoted=True,
    )
    context.task_service.accept_best_version(promoted_child.task_id)

    rejected_root = context.task_service.create_video_task(prompt="draw a triangle")
    rejected_root_task = context.store.get_task(rejected_root.task_id)
    assert rejected_root_task is not None
    rejected_root_task.status = TaskStatus.COMPLETED
    rejected_root_task.phase = TaskPhase.COMPLETED
    rejected_root_task.delivery_status = "delivered"
    rejected_root_task.completion_mode = "primary"
    rejected_root_task.resolved_task_id = rejected_root_task.task_id
    context.store.update_task(rejected_root_task)
    rejected_child = context.task_service.create_challenger_task(
        rejected_root.task_id,
        feedback="improve clarity",
    )
    rejected_child_task = context.store.get_task(rejected_child.task_id)
    assert rejected_child_task is not None
    rejected_child_task.status = TaskStatus.COMPLETED
    rejected_child_task.phase = TaskPhase.COMPLETED
    rejected_child_task.delivery_status = "delivered"
    rejected_child_task.quality_gate_status = "accepted"
    rejected_child_task.completion_mode = "repaired"
    context.store.update_task(rejected_child_task)
    context.delivery_case_service.record_auto_arbitration_evaluated(
        task=rejected_child_task,
        arbitration_summary={
            "recommended_task_id": rejected_root.task_id,
            "recommended_action": "keep_incumbent",
            "selected_task_id": rejected_root.task_id,
            "candidate_count": 2,
            "reason": "incumbent_has_best_accepted_score",
        },
        promoted=False,
    )

    repair_saturated = context.task_service.create_video_task(prompt="draw a pentagon")
    repair_saturated_task = context.store.get_task(repair_saturated.task_id)
    assert repair_saturated_task is not None
    repair_saturated_task.status = TaskStatus.FAILED
    repair_saturated_task.phase = TaskPhase.FAILED
    repair_saturated_task.delivery_status = "failed"
    repair_saturated_task.delivery_stop_reason = "runtime_unhealthy"
    repair_saturated_task.repair_attempted = True
    repair_saturated_task.repair_stop_reason = "budget_exhausted"
    context.store.update_task(repair_saturated_task)

    payload = get_runtime_status_tool(context, {})

    assert payload["delivery_summary"]["total_roots"] == 4
    assert payload["delivery_summary"]["completion_modes"] == {
        "primary": 2,
        "repaired": 1,
    }
    assert payload["delivery_summary"]["challenger_branches_completed"] == 2
    assert payload["delivery_summary"]["challenger_branches_rejected"] == 1
    assert payload["delivery_summary"]["arbitration_attempts"] == 2
    assert payload["delivery_summary"]["arbitration_successes"] == 1
    assert payload["delivery_summary"]["repair_loop_saturation_count"] == 1
    assert payload["delivery_summary"]["branch_rejection_rate"] == 0.5
    assert payload["delivery_summary"]["arbitration_success_rate"] == 0.5
    assert payload["delivery_summary"]["repair_loop_saturation_rate"] == 0.25


def test_runtime_status_delivery_summary_exposes_case_status_counts(tmp_path: Path) -> None:
    settings = bootstrapped_settings(
        Settings(
            data_dir=tmp_path / "data",
            database_path=tmp_path / "data" / "video_agent.db",
            artifact_root=tmp_path / "data" / "tasks",
            run_embedded_worker=False,
            multi_agent_workflow_enabled=True,
        )
    )
    context = create_app_context(settings)

    completed = context.task_service.create_video_task(prompt="draw a circle")
    completed_task = context.store.get_task(completed.task_id)
    assert completed_task is not None
    completed_task.status = TaskStatus.COMPLETED
    completed_task.phase = TaskPhase.COMPLETED
    completed_task.delivery_status = "delivered"
    completed_task.completion_mode = "primary"
    completed_task.resolved_task_id = completed_task.task_id
    context.store.update_task(completed_task)
    context.delivery_case_service.sync_case_for_root(completed.task_id)

    branching = context.task_service.create_video_task(prompt="draw a square")
    branching_task = context.store.get_task(branching.task_id)
    assert branching_task is not None
    branching_task.status = TaskStatus.COMPLETED
    branching_task.phase = TaskPhase.COMPLETED
    branching_task.delivery_status = "delivered"
    branching_task.completion_mode = "primary"
    branching_task.resolved_task_id = branching_task.task_id
    context.store.update_task(branching_task)
    branching_child = context.task_service.create_challenger_task(branching.task_id, feedback="try alt")
    context.delivery_case_service.sync_case_for_root(branching.task_id)

    arbitrating = context.task_service.create_video_task(prompt="draw a triangle")
    arbitrating_task = context.store.get_task(arbitrating.task_id)
    assert arbitrating_task is not None
    arbitrating_task.status = TaskStatus.COMPLETED
    arbitrating_task.phase = TaskPhase.COMPLETED
    arbitrating_task.delivery_status = "delivered"
    arbitrating_task.completion_mode = "primary"
    arbitrating_task.resolved_task_id = arbitrating_task.task_id
    context.store.update_task(arbitrating_task)
    arbitrating_child = context.task_service.create_challenger_task(arbitrating.task_id, feedback="push quality")
    arbitrating_child_task = context.store.get_task(arbitrating_child.task_id)
    assert arbitrating_child_task is not None
    arbitrating_child_task.status = TaskStatus.COMPLETED
    arbitrating_child_task.phase = TaskPhase.COMPLETED
    arbitrating_child_task.branch_kind = "challenger"
    arbitrating_child_task.delivery_status = "delivered"
    arbitrating_child_task.quality_gate_status = "accepted"
    arbitrating_child_task.completion_mode = "repaired"
    context.store.update_task(arbitrating_child_task)
    context.delivery_case_service.sync_case_for_root(arbitrating.task_id)

    reviewing = context.task_service.create_video_task(prompt="draw an ellipse")
    reviewing_task = context.store.get_task(reviewing.task_id)
    assert reviewing_task is not None
    reviewing_task.status = TaskStatus.RUNNING
    reviewing_task.phase = TaskPhase.VALIDATION
    context.store.update_task(reviewing_task)
    context.delivery_case_service.sync_case_for_root(reviewing.task_id)

    failed = context.task_service.create_video_task(prompt="draw a pentagon")
    failed_task = context.store.get_task(failed.task_id)
    assert failed_task is not None
    failed_task.status = TaskStatus.FAILED
    failed_task.phase = TaskPhase.FAILED
    failed_task.delivery_status = "failed"
    failed_task.delivery_stop_reason = "runtime_unhealthy"
    context.store.update_task(failed_task)
    context.delivery_case_service.sync_case_for_root(failed.task_id)

    payload = get_runtime_status_tool(context, {})

    assert branching_child.task_id is not None
    assert payload["delivery_summary"]["case_status_counts"] == {
        "arbitrating": 1,
        "branching": 1,
        "completed": 1,
        "failed": 1,
        "reviewing": 1,
    }


def test_runtime_status_delivery_summary_exposes_agent_run_status_counts(tmp_path: Path) -> None:
    settings = bootstrapped_settings(
        Settings(
            data_dir=tmp_path / "data",
            database_path=tmp_path / "data" / "video_agent.db",
            artifact_root=tmp_path / "data" / "tasks",
            run_embedded_worker=False,
            multi_agent_workflow_enabled=True,
        )
    )
    context = create_app_context(settings)

    completed = context.task_service.create_video_task(prompt="draw a circle")
    completed_task = context.store.get_task(completed.task_id)
    assert completed_task is not None
    context.delivery_case_service.record_generator_run(
        task=completed_task,
        status="completed",
        summary="Generation and render completed",
        phase=TaskPhase.RENDERING.value,
    )

    running = context.task_service.create_video_task(prompt="draw a square")
    running_task = context.store.get_task(running.task_id)
    assert running_task is not None
    context.delivery_case_service.mark_generator_running(task=running_task)

    branching = context.task_service.create_video_task(prompt="draw a triangle")
    branching_task = context.store.get_task(branching.task_id)
    assert branching_task is not None
    branching_task.status = TaskStatus.COMPLETED
    branching_task.phase = TaskPhase.COMPLETED
    branching_task.delivery_status = "delivered"
    branching_task.completion_mode = "primary"
    branching_task.resolved_task_id = branching_task.task_id
    context.store.update_task(branching_task)
    context.delivery_case_service.record_generator_run(
        task=branching_task,
        status="completed",
        summary="Generation and render completed",
        phase=TaskPhase.RENDERING.value,
    )
    context.task_service.create_challenger_task(branching.task_id, feedback="try alt")

    failed = context.task_service.create_video_task(prompt="draw a pentagon")
    failed_task = context.store.get_task(failed.task_id)
    assert failed_task is not None
    context.delivery_case_service.record_generator_run(
        task=failed_task,
        status="failed",
        summary="Generation failed",
        phase=TaskPhase.RENDERING.value,
        stop_reason="render_failed",
    )

    payload = get_runtime_status_tool(context, {})

    assert payload["delivery_summary"]["agent_run_status_counts"] == {
        "completed": 2,
        "failed": 1,
        "queued": 1,
        "running": 1,
    }


def test_runtime_status_delivery_summary_exposes_agent_run_role_status_counts(tmp_path: Path) -> None:
    settings = bootstrapped_settings(
        Settings(
            data_dir=tmp_path / "data",
            database_path=tmp_path / "data" / "video_agent.db",
            artifact_root=tmp_path / "data" / "tasks",
            run_embedded_worker=False,
            multi_agent_workflow_enabled=True,
        )
    )
    context = create_app_context(settings)

    completed = context.task_service.create_video_task(prompt="draw a circle")
    completed_task = context.store.get_task(completed.task_id)
    assert completed_task is not None
    context.delivery_case_service.mark_planner_running(task=completed_task)
    context.delivery_case_service.record_planner_run(
        task=completed_task,
        scene_spec_path=context.artifact_store.write_scene_spec(completed.task_id, {"scene": "spec"}),
        scene_plan_path=context.artifact_store.write_scene_plan(completed.task_id, {"scene": "plan"}),
    )
    context.delivery_case_service.record_generator_run(
        task=completed_task,
        status="completed",
        summary="Generation and render completed",
        phase=TaskPhase.RENDERING.value,
    )
    context.delivery_case_service.mark_reviewer_running(task=completed_task)
    context.delivery_case_service.record_reviewer_run(
        task=completed_task,
        report=ValidationReport(passed=True, summary="ok", issues=[]),
        summary="Validation and quality review completed",
        quality_gate_status="accepted",
    )

    failed = context.task_service.create_video_task(prompt="draw a square")
    failed_task = context.store.get_task(failed.task_id)
    assert failed_task is not None
    context.delivery_case_service.record_generator_run(
        task=failed_task,
        status="failed",
        summary="Generation failed",
        phase=TaskPhase.RENDERING.value,
        stop_reason="render_failed",
    )

    repairing = context.task_service.create_video_task(prompt="draw a triangle")
    repairing_task = context.store.get_task(repairing.task_id)
    assert repairing_task is not None
    context.delivery_case_service.mark_repairer_running(task=repairing_task)

    payload = get_runtime_status_tool(context, {})

    assert payload["delivery_summary"]["agent_run_role_status_counts"] == {
        "generator": {
            "completed": 1,
            "failed": 1,
            "queued": 1,
        },
        "planner": {
            "completed": 1,
        },
        "repairer": {
            "running": 1,
        },
        "reviewer": {
            "completed": 1,
        },
    }


def test_runtime_status_delivery_summary_exposes_agent_run_stop_reason_counts(tmp_path: Path) -> None:
    settings = bootstrapped_settings(
        Settings(
            data_dir=tmp_path / "data",
            database_path=tmp_path / "data" / "video_agent.db",
            artifact_root=tmp_path / "data" / "tasks",
            run_embedded_worker=False,
            multi_agent_workflow_enabled=True,
        )
    )
    context = create_app_context(settings)

    render_failed = context.task_service.create_video_task(prompt="draw a square")
    render_failed_task = context.store.get_task(render_failed.task_id)
    assert render_failed_task is not None
    context.delivery_case_service.record_generator_run(
        task=render_failed_task,
        status="failed",
        summary="Generation failed",
        phase=TaskPhase.RENDERING.value,
        stop_reason="render_failed",
    )

    provider_timeout = context.task_service.create_video_task(prompt="draw a triangle")
    provider_timeout_task = context.store.get_task(provider_timeout.task_id)
    assert provider_timeout_task is not None
    context.delivery_case_service.record_generator_run(
        task=provider_timeout_task,
        status="failed",
        summary="Generation failed",
        phase=TaskPhase.GENERATING_CODE.value,
        stop_reason="provider_timeout",
    )

    repeated_render_failed = context.task_service.create_video_task(prompt="draw a pentagon")
    repeated_render_failed_task = context.store.get_task(repeated_render_failed.task_id)
    assert repeated_render_failed_task is not None
    context.delivery_case_service.record_generator_run(
        task=repeated_render_failed_task,
        status="failed",
        summary="Generation failed",
        phase=TaskPhase.RENDERING.value,
        stop_reason="render_failed",
    )

    payload = get_runtime_status_tool(context, {})

    assert payload["delivery_summary"]["agent_run_stop_reason_counts"] == {
        "provider_timeout": 1,
        "render_failed": 2,
    }


def test_runtime_status_reports_blocked_autonomy_guard_when_branch_rejection_rate_regresses(tmp_path: Path) -> None:
    settings = bootstrapped_settings(
        Settings(
            data_dir=tmp_path / "data",
            database_path=tmp_path / "data" / "video_agent.db",
            artifact_root=tmp_path / "data" / "tasks",
            eval_root=tmp_path / "data" / "evals",
            capability_rollout_profile="autonomy-guarded",
            multi_agent_workflow_guarded_max_branch_rejection_rate=0.25,
            run_embedded_worker=False,
        )
    )
    context = create_app_context(settings)
    canary_target = context.settings.eval_root / "delivery-canary" / "latest.json"
    canary_target.parent.mkdir(parents=True, exist_ok=True)
    canary_target.write_text('{"task_id":"canary","delivered":true}')

    root = context.task_service.create_video_task(prompt="draw a circle")
    root_task = context.store.get_task(root.task_id)
    assert root_task is not None
    root_task.status = TaskStatus.COMPLETED
    root_task.phase = TaskPhase.COMPLETED
    root_task.delivery_status = "delivered"
    root_task.completion_mode = "primary"
    root_task.resolved_task_id = root_task.task_id
    context.store.update_task(root_task)
    challenger = context.task_service.create_challenger_task(root.task_id, feedback="push quality")
    challenger_task = context.store.get_task(challenger.task_id)
    assert challenger_task is not None
    challenger_task.status = TaskStatus.COMPLETED
    challenger_task.phase = TaskPhase.COMPLETED
    challenger_task.delivery_status = "delivered"
    challenger_task.quality_gate_status = "accepted"
    challenger_task.completion_mode = "repaired"
    context.store.update_task(challenger_task)
    context.delivery_case_service.record_auto_arbitration_evaluated(
        task=challenger_task,
        arbitration_summary={
            "recommended_task_id": root.task_id,
            "recommended_action": "keep_incumbent",
            "selected_task_id": root.task_id,
            "candidate_count": 2,
            "reason": "incumbent_has_best_accepted_score",
        },
        promoted=False,
    )

    payload = get_runtime_status_tool(context, {})

    assert payload["autonomy_guard"]["enabled"] is True
    assert payload["autonomy_guard"]["allowed"] is False
    assert payload["autonomy_guard"]["reasons"] == ["branch_rejection_rate_above_threshold"]
