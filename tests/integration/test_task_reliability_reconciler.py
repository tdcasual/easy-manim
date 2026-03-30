import json
from pathlib import Path

from video_agent.config import Settings
from video_agent.domain.delivery_case_models import AgentRun
from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.domain.quality_models import QualityScorecard
from video_agent.server.app import create_app_context
from tests.support import bootstrapped_settings


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _build_failed_pipeline_settings(tmp_path: Path, **overrides) -> Settings:
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

    values = {
        "data_dir": data_dir,
        "database_path": data_dir / "video_agent.db",
        "artifact_root": data_dir / "tasks",
        "manim_command": str(fake_manim),
        "ffmpeg_command": "definitely-missing-ffmpeg-binary",
        "ffprobe_command": str(fake_ffprobe),
        "run_embedded_worker": False,
        "auto_repair_enabled": False,
        "delivery_guarantee_enabled": True,
    }
    values.update(overrides)
    return bootstrapped_settings(Settings(**values))


def _build_success_pipeline_settings(tmp_path: Path, **overrides) -> Settings:
    data_dir = tmp_path / "data"

    fake_manim = tmp_path / "fake_manim.sh"
    _write_executable(
        fake_manim,
        "#!/bin/sh\n"
        "if [ \"$1\" != \"-ql\" ]; then exit 11; fi\n"
        "if [ \"$4\" != \"--media_dir\" ]; then exit 12; fi\n"
        "if [ \"$6\" != \"-o\" ]; then exit 13; fi\n"
        "script_name=$(basename \"$2\" .py)\n"
        "mkdir -p \"$5/videos/$script_name/480p15\"\n"
        "printf 'normal-video' > \"$5/videos/$script_name/480p15/$7\"\n",
    )

    fake_ffprobe = tmp_path / "fake_ffprobe_ok.sh"
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

    values = {
        "data_dir": data_dir,
        "database_path": data_dir / "video_agent.db",
        "artifact_root": data_dir / "tasks",
        "manim_command": str(fake_manim),
        "ffmpeg_command": str(fake_ffmpeg),
        "ffprobe_command": str(fake_ffprobe),
        "run_embedded_worker": False,
        "delivery_guarantee_enabled": False,
    }
    values.update(overrides)
    return bootstrapped_settings(Settings(**values))


def test_startup_reconciler_delivers_pending_failed_root_after_restart(tmp_path: Path) -> None:
    settings = _build_failed_pipeline_settings(tmp_path)
    app = create_app_context(settings)
    created = app.task_service.create_video_task(prompt="draw a circle")
    task = app.store.get_task(created.task_id)
    assert task is not None
    task.status = TaskStatus.FAILED
    task.phase = TaskPhase.FAILED
    task.delivery_status = "pending"
    app.store.update_task(task)
    app.artifact_store.write_task_snapshot(task)

    restarted = create_app_context(settings)
    snapshot = restarted.task_service.get_video_task(created.task_id).model_dump(mode="json")
    result = restarted.task_service.get_video_result(created.task_id).model_dump(mode="json")

    assert snapshot["delivery_status"] == "delivered"
    assert snapshot["completion_mode"] == "emergency_fallback"
    assert result["ready"] is True
    assert result["delivery_status"] == "delivered"
    assert result["completion_mode"] == "emergency_fallback"


def test_startup_reconciler_syncs_root_to_existing_delivered_descendant(tmp_path: Path) -> None:
    settings = _build_failed_pipeline_settings(tmp_path)
    app = create_app_context(settings)
    created = app.task_service.create_video_task(prompt="draw a circle")
    root = app.store.get_task(created.task_id)
    assert root is not None
    root.status = TaskStatus.FAILED
    root.phase = TaskPhase.FAILED
    root.delivery_status = "pending"
    app.store.update_task(root)
    app.artifact_store.write_task_snapshot(root)

    child_created = app.task_service.create_degraded_delivery_task(
        created.task_id,
        feedback="Guaranteed delivery degraded fallback.",
        generation_mode="guided_generate",
    )
    child = app.store.get_task(child_created.task_id)
    assert child is not None
    child_video_path = app.artifact_store.final_video_path(child.task_id)
    child_video_path.write_bytes(b"delivered-child-video")
    child.best_result_artifact_id = app.store.register_artifact(child.task_id, "final_video", child_video_path)
    child.status = TaskStatus.COMPLETED
    child.phase = TaskPhase.COMPLETED
    child.delivery_status = "delivered"
    child.completion_mode = "degraded"
    child.delivery_tier = "guided_generate"
    app.store.update_task(child)
    app.artifact_store.write_task_snapshot(child)

    restarted = create_app_context(settings)
    root_snapshot = restarted.task_service.get_video_task(created.task_id).model_dump(mode="json")
    result = restarted.task_service.get_video_result(created.task_id).model_dump(mode="json")

    assert root_snapshot["delivery_status"] == "delivered"
    assert root_snapshot["resolved_task_id"] == child.task_id
    assert root_snapshot["completion_mode"] == "degraded"
    assert result["ready"] is True
    assert result["resolved_task_id"] == child.task_id


def test_startup_reconciler_recovers_delivered_branch_missing_final_video_artifact(tmp_path: Path) -> None:
    settings = _build_failed_pipeline_settings(tmp_path)
    app = create_app_context(settings)
    created = app.task_service.create_video_task(prompt="draw a circle")
    root = app.store.get_task(created.task_id)
    assert root is not None
    root.status = TaskStatus.FAILED
    root.phase = TaskPhase.FAILED
    root.delivery_status = "pending"
    app.store.update_task(root)
    app.artifact_store.write_task_snapshot(root)

    child_created = app.task_service.create_degraded_delivery_task(
        created.task_id,
        feedback="Guaranteed delivery degraded fallback.",
        generation_mode="guided_generate",
    )
    child = app.store.get_task(child_created.task_id)
    assert child is not None
    child.status = TaskStatus.COMPLETED
    child.phase = TaskPhase.COMPLETED
    child.delivery_status = "delivered"
    child.resolved_task_id = child.task_id
    child.completion_mode = "degraded"
    child.delivery_tier = "guided_generate"
    app.store.update_task(child)
    app.artifact_store.write_task_snapshot(child)
    app.delivery_case_service.sync_case_for_root(created.task_id)

    restarted = create_app_context(settings)
    root_snapshot = restarted.task_service.get_video_task(created.task_id).model_dump(mode="json")
    result = restarted.task_service.get_video_result(created.task_id).model_dump(mode="json")
    recovered_child = restarted.store.get_task(child.task_id)
    events = restarted.store.list_events(created.task_id)

    assert root_snapshot["delivery_status"] == "delivered"
    assert root_snapshot["resolved_task_id"] == child.task_id
    assert root_snapshot["completion_mode"] == "degraded"
    assert result["ready"] is True
    assert result["resolved_task_id"] == child.task_id
    assert result["video_resource"] == f"video-task://{child.task_id}/artifacts/final_video.mp4"
    assert recovered_child is not None
    assert recovered_child.best_result_artifact_id is not None
    assert restarted.artifact_store.final_video_path(child.task_id).exists()
    assert any(
        event["event_type"] == "task_reliability_reconciled"
        and event["payload"].get("action") == "delivery_completed"
        and event["payload"].get("completion_mode") == "degraded"
        for event in events
    )


def test_startup_reconciler_recovers_missing_final_video_after_case_sync(tmp_path: Path) -> None:
    settings = _build_failed_pipeline_settings(tmp_path)
    app = create_app_context(settings)
    created = app.task_service.create_video_task(prompt="draw a circle")
    root = app.store.get_task(created.task_id)
    assert root is not None
    root.status = TaskStatus.FAILED
    root.phase = TaskPhase.FAILED
    root.delivery_status = "pending"
    app.store.update_task(root)
    app.artifact_store.write_task_snapshot(root)

    child_created = app.task_service.create_degraded_delivery_task(
        created.task_id,
        feedback="Guaranteed delivery degraded fallback.",
        generation_mode="guided_generate",
    )
    child = app.store.get_task(child_created.task_id)
    assert child is not None
    child.status = TaskStatus.COMPLETED
    child.phase = TaskPhase.COMPLETED
    child.delivery_status = "delivered"
    child.resolved_task_id = child.task_id
    child.completion_mode = "degraded"
    child.delivery_tier = "guided_generate"
    app.store.update_task(child)
    app.artifact_store.write_task_snapshot(child)

    root.status = TaskStatus.COMPLETED
    root.phase = TaskPhase.COMPLETED
    root.delivery_status = "delivered"
    root.resolved_task_id = child.task_id
    root.completion_mode = "degraded"
    root.delivery_tier = "guided_generate"
    app.store.update_task(root)
    app.artifact_store.write_task_snapshot(root)

    case, _ = app.delivery_case_service.ensure_case_for_task(root)
    case.status = "queued"
    case.active_task_id = root.task_id
    case.selected_task_id = None
    case.delivery_status = "pending"
    app.store.upsert_delivery_case(case)

    restarted = create_app_context(settings)
    result = restarted.task_service.get_video_result(created.task_id).model_dump(mode="json")
    events = restarted.store.list_events(created.task_id)

    assert result["ready"] is True
    assert result["resolved_task_id"] == child.task_id
    assert result["video_resource"] == f"video-task://{child.task_id}/artifacts/final_video.mp4"
    assert restarted.artifact_store.final_video_path(child.task_id).exists()
    assert any(
        event["event_type"] == "task_reliability_reconciled"
        and event["payload"].get("action") == "missing_final_video_artifact_detected"
        and event["payload"].get("affected_task_id") == child.task_id
        for event in events
    )


def test_get_video_result_is_not_ready_without_final_video_artifact(tmp_path: Path) -> None:
    settings = _build_success_pipeline_settings(tmp_path)
    app = create_app_context(settings)
    created = app.task_service.create_video_task(prompt="draw a circle")
    root = app.store.get_task(created.task_id)
    assert root is not None
    root.status = TaskStatus.COMPLETED
    root.phase = TaskPhase.COMPLETED
    root.delivery_status = "delivered"
    root.resolved_task_id = root.task_id
    root.completion_mode = "primary"
    app.store.update_task(root)
    app.artifact_store.write_task_snapshot(root)

    result = app.task_service.get_video_result(created.task_id).model_dump(mode="json")

    assert result["ready"] is False
    assert result["video_resource"] is None
    assert result["delivery_status"] == "delivered"
    assert result["resolved_task_id"] == root.task_id


def test_startup_reconciler_promotes_completed_accepted_challenger_after_restart(tmp_path: Path) -> None:
    settings = _build_success_pipeline_settings(
        tmp_path,
        multi_agent_workflow_enabled=True,
        quality_gate_min_score=0.95,
        multi_agent_workflow_max_child_attempts=1,
    )
    app = create_app_context(settings)
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()
    lineage = app.store.list_lineage_tasks(created.task_id)
    challenger = lineage[-1]
    assert challenger.task_id != created.task_id

    challenger_video_path = app.artifact_store.final_video_path(challenger.task_id)
    challenger_video_path.write_bytes(b"accepted-challenger-video")
    challenger.best_result_artifact_id = app.store.register_artifact(
        challenger.task_id,
        "final_video",
        challenger_video_path,
    )
    challenger.status = TaskStatus.COMPLETED
    challenger.phase = TaskPhase.COMPLETED
    challenger.branch_kind = "challenger"
    challenger.delivery_status = "delivered"
    challenger.quality_gate_status = "accepted"
    challenger.resolved_task_id = challenger.task_id
    challenger.completion_mode = "repaired"
    challenger.delivery_tier = "guided_generate"
    app.store.update_task(challenger)
    app.artifact_store.write_task_snapshot(challenger)
    app.store.upsert_task_quality_score(
        challenger.task_id,
        QualityScorecard(
            task_id=challenger.task_id,
            total_score=0.96,
            accepted=True,
            decision="accept",
            summary="accepted challenger",
        ),
    )
    app.delivery_case_service.sync_case_for_root(created.task_id)

    restarted = create_app_context(settings)
    snapshot = restarted.task_service.get_video_task(created.task_id).model_dump(mode="json")
    result = restarted.task_service.get_video_result(created.task_id).model_dump(mode="json")
    case = restarted.store.get_delivery_case(created.task_id)
    events = restarted.store.list_events(created.task_id)

    assert snapshot["resolved_task_id"] == challenger.task_id
    assert snapshot["delivery_status"] == "delivered"
    assert result["resolved_task_id"] == challenger.task_id
    assert result["video_resource"] == f"video-task://{challenger.task_id}/artifacts/final_video.mp4"
    assert case is not None
    assert case.selected_task_id == challenger.task_id
    assert any(
        event["event_type"] == "task_reliability_reconciled"
        and event["payload"].get("action") == "auto_arbitration_promoted"
        and event["payload"].get("resolved_task_id") == challenger.task_id
        for event in events
    )


def test_startup_reconciler_resolves_arbitrating_case_with_accepted_challenger(tmp_path: Path) -> None:
    settings = _build_success_pipeline_settings(
        tmp_path,
        multi_agent_workflow_enabled=True,
        quality_gate_min_score=0.95,
        multi_agent_workflow_max_child_attempts=1,
    )
    app = create_app_context(settings)
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()
    lineage = app.store.list_lineage_tasks(created.task_id)
    challenger = lineage[-1]
    assert challenger.task_id != created.task_id

    challenger_video_path = app.artifact_store.final_video_path(challenger.task_id)
    challenger_video_path.write_bytes(b"accepted-challenger-video")
    challenger.best_result_artifact_id = app.store.register_artifact(
        challenger.task_id,
        "final_video",
        challenger_video_path,
    )
    challenger.status = TaskStatus.COMPLETED
    challenger.phase = TaskPhase.COMPLETED
    challenger.branch_kind = "challenger"
    challenger.delivery_status = "delivered"
    challenger.quality_gate_status = "accepted"
    challenger.resolved_task_id = challenger.task_id
    challenger.completion_mode = "repaired"
    challenger.delivery_tier = "guided_generate"
    app.store.update_task(challenger)
    app.artifact_store.write_task_snapshot(challenger)
    app.store.upsert_task_quality_score(
        challenger.task_id,
        QualityScorecard(
            task_id=challenger.task_id,
            total_score=0.96,
            accepted=True,
            decision="accept",
            summary="accepted challenger",
        ),
    )
    case, _ = app.delivery_case_service.ensure_case_for_task(app.store.get_task(created.task_id))
    case.status = "arbitrating"
    case.active_task_id = challenger.task_id
    case.selected_task_id = created.task_id
    case.delivery_status = "delivered"
    app.store.upsert_delivery_case(case)

    restarted = create_app_context(settings)
    synced_case = restarted.store.get_delivery_case(created.task_id)
    events = restarted.store.list_events(created.task_id)

    assert synced_case is not None
    assert synced_case.status == "completed"
    assert synced_case.selected_task_id == challenger.task_id
    assert any(
        event["event_type"] == "task_reliability_reconciled"
        and event["payload"].get("action") == "case_arbitration_resumed"
        and event["payload"].get("resolved_task_id") == challenger.task_id
        for event in events
    )


def test_startup_reconciler_completes_case_after_finished_unaccepted_challenger(tmp_path: Path) -> None:
    settings = _build_success_pipeline_settings(
        tmp_path,
        multi_agent_workflow_enabled=True,
        quality_gate_min_score=0.95,
        multi_agent_workflow_max_child_attempts=1,
    )
    app = create_app_context(settings)
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()
    lineage = app.store.list_lineage_tasks(created.task_id)
    challenger = lineage[-1]
    assert challenger.task_id != created.task_id

    challenger_video_path = app.artifact_store.final_video_path(challenger.task_id)
    challenger_video_path.write_bytes(b"unfinished-accepted-challenger-video")
    challenger.best_result_artifact_id = app.store.register_artifact(
        challenger.task_id,
        "final_video",
        challenger_video_path,
    )
    challenger.status = TaskStatus.COMPLETED
    challenger.phase = TaskPhase.COMPLETED
    challenger.branch_kind = "challenger"
    challenger.delivery_status = "delivered"
    challenger.quality_gate_status = "needs_revision"
    challenger.resolved_task_id = challenger.task_id
    challenger.completion_mode = "repaired"
    challenger.delivery_tier = "guided_generate"
    app.store.update_task(challenger)
    app.artifact_store.write_task_snapshot(challenger)

    restarted = create_app_context(settings)
    snapshot = restarted.task_service.get_video_task(created.task_id).model_dump(mode="json")
    case = restarted.store.get_delivery_case(created.task_id)
    events = restarted.store.list_events(created.task_id)

    assert snapshot["resolved_task_id"] == created.task_id
    assert snapshot["delivery_status"] == "delivered"
    assert case is not None
    assert case.status == "completed"
    assert case.selected_task_id == created.task_id
    assert case.active_task_id == challenger.task_id
    assert any(
        event["event_type"] == "task_reliability_reconciled"
        and event["payload"].get("action") == "auto_arbitration_kept_incumbent"
        and event["payload"].get("recommended_action") == "wait_for_completion"
        for event in events
    )


def test_startup_reconciler_syncs_stale_case_state_for_completed_root(tmp_path: Path) -> None:
    settings = _build_success_pipeline_settings(tmp_path)
    app = create_app_context(settings)
    created = app.task_service.create_video_task(prompt="draw a circle")
    root = app.store.get_task(created.task_id)
    assert root is not None
    root.status = TaskStatus.COMPLETED
    root.phase = TaskPhase.COMPLETED
    root.delivery_status = "delivered"
    root.completion_mode = "primary"
    root.resolved_task_id = root.task_id
    app.store.update_task(root)
    app.artifact_store.write_task_snapshot(root)

    case, _ = app.delivery_case_service.ensure_case_for_task(root)
    case.status = "branching"
    case.active_task_id = "missing-branch"
    case.selected_task_id = root.task_id
    app.store.upsert_delivery_case(case)

    restarted = create_app_context(settings)
    synced_case = restarted.store.get_delivery_case(created.task_id)
    events = restarted.store.list_events(created.task_id)

    assert synced_case is not None
    assert synced_case.status == "completed"
    assert synced_case.active_task_id == created.task_id
    assert synced_case.selected_task_id == created.task_id
    assert any(
        event["event_type"] == "task_reliability_reconciled"
        and event["payload"].get("action") == "sync_case_state"
        and event["payload"].get("case_status") == "completed"
        for event in events
    )


def test_worker_watchdog_fails_queued_root_when_runtime_is_hard_unhealthy(tmp_path: Path) -> None:
    settings = bootstrapped_settings(
        Settings(
            data_dir=tmp_path / "data",
            database_path=tmp_path / "data" / "video_agent.db",
            artifact_root=tmp_path / "data" / "tasks",
            manim_command="definitely-missing-manim-binary",
            ffprobe_command="definitely-missing-ffprobe-binary",
            run_embedded_worker=False,
            delivery_guarantee_enabled=True,
        )
    )
    app = create_app_context(settings)
    created = app.task_service.create_video_task(prompt="draw a circle")

    processed = app.worker.run_once()
    snapshot = app.task_service.get_video_task(created.task_id).model_dump(mode="json")

    assert processed == 0
    assert snapshot["status"] == "failed"
    assert snapshot["delivery_status"] == "failed"
    assert snapshot["delivery_stop_reason"] == "runtime_unhealthy"


def test_worker_watchdog_syncs_orphaned_pending_case_back_to_root(tmp_path: Path) -> None:
    settings = _build_success_pipeline_settings(tmp_path)
    app = create_app_context(settings)
    created = app.task_service.create_video_task(prompt="draw a circle")
    root = app.store.get_task(created.task_id)
    assert root is not None

    case, _ = app.delivery_case_service.ensure_case_for_task(root)
    case.status = "branching"
    case.active_task_id = "missing-branch"
    case.selected_task_id = root.task_id
    app.store.upsert_delivery_case(case)

    result = app.task_reliability_service.sweep_watchdog()
    synced_case = app.store.get_delivery_case(created.task_id)
    events = app.store.list_events(created.task_id)

    assert result["reconciled"] == 1
    assert synced_case is not None
    assert synced_case.status == "queued"
    assert synced_case.active_task_id == created.task_id
    assert synced_case.selected_task_id is None
    assert any(
        event["event_type"] == "task_reliability_reconciled"
        and event["payload"].get("action") == "sync_case_state"
        and event["payload"].get("case_status") == "queued"
        for event in events
    )


def test_app_context_exposes_case_reliability_service_and_task_wrapper(tmp_path: Path) -> None:
    settings = _build_success_pipeline_settings(tmp_path)
    app = create_app_context(settings)

    assert app.case_reliability_service is not None
    assert app.task_reliability_service.case_reliability_service is app.case_reliability_service


def test_task_reliability_wrapper_delegates_to_case_reliability_service(tmp_path: Path) -> None:
    settings = _build_success_pipeline_settings(tmp_path)
    app = create_app_context(settings)
    created = app.task_service.create_video_task(prompt="draw a circle")
    root = app.store.get_task(created.task_id)
    assert root is not None

    case, _ = app.delivery_case_service.ensure_case_for_task(root)
    case.status = "branching"
    case.active_task_id = "missing-branch"
    case.selected_task_id = root.task_id
    app.store.upsert_delivery_case(case)

    via_wrapper = app.task_reliability_service.sweep_watchdog()
    synced_case = app.store.get_delivery_case(created.task_id)

    assert via_wrapper["reconciled"] == 1
    assert synced_case is not None
    assert synced_case.status == "queued"
    assert synced_case.active_task_id == created.task_id


def test_worker_watchdog_uses_case_reliability_service_directly(tmp_path: Path) -> None:
    settings = _build_success_pipeline_settings(tmp_path)
    app = create_app_context(settings)

    assert app.worker.task_reliability_service is app.case_reliability_service


def test_startup_reconciler_cancels_stalled_agent_run_after_case_completion(tmp_path: Path) -> None:
    settings = _build_success_pipeline_settings(tmp_path)
    app = create_app_context(settings)
    created = app.task_service.create_video_task(prompt="draw a circle")
    root = app.store.get_task(created.task_id)
    assert root is not None

    final_video_path = app.artifact_store.final_video_path(created.task_id)
    final_video_path.write_bytes(b"completed-root-video")
    root.best_result_artifact_id = app.store.register_artifact(created.task_id, "final_video", final_video_path)
    root.status = TaskStatus.COMPLETED
    root.phase = TaskPhase.COMPLETED
    root.delivery_status = "delivered"
    root.resolved_task_id = created.task_id
    root.completion_mode = "primary"
    app.store.update_task(root)
    app.artifact_store.write_task_snapshot(root)
    app.delivery_case_service.sync_case_for_root(created.task_id)

    stale_run = app.store.create_agent_run(
        AgentRun(
            case_id=created.task_id,
            root_task_id=created.task_id,
            task_id=created.task_id,
            role="reviewer",
            status="running",
            phase=TaskPhase.COMPLETED.value,
            summary="Stale review still marked running",
        )
    )

    restarted = create_app_context(settings)
    runs = restarted.store.list_agent_runs(created.task_id, task_id=created.task_id)
    events = restarted.store.list_events(created.task_id)
    updated_run = next(run for run in runs if run.run_id == stale_run.run_id)

    assert updated_run.status == "cancelled"
    assert updated_run.metadata["reliability_stop_reason"] == "case_terminal"
    assert any(
        event["event_type"] == "task_reliability_reconciled"
        and event["payload"].get("action") == "stalled_agent_run_cancelled"
        and event["payload"].get("run_id") == stale_run.run_id
        and event["payload"].get("reason") == "case_terminal"
        for event in events
    )


def test_startup_reconciler_fails_orphaned_branch_and_preserves_incumbent_delivery(tmp_path: Path) -> None:
    settings = _build_success_pipeline_settings(tmp_path, multi_agent_workflow_enabled=True)
    app = create_app_context(settings)
    created = app.task_service.create_video_task(prompt="draw a circle")
    root = app.store.get_task(created.task_id)
    assert root is not None

    final_video_path = app.artifact_store.final_video_path(created.task_id)
    final_video_path.write_bytes(b"completed-root-video")
    root.best_result_artifact_id = app.store.register_artifact(created.task_id, "final_video", final_video_path)
    root.status = TaskStatus.COMPLETED
    root.phase = TaskPhase.COMPLETED
    root.quality_gate_status = "accepted"
    root.delivery_status = "delivered"
    root.resolved_task_id = created.task_id
    root.completion_mode = "primary"
    app.store.update_task(root)
    app.artifact_store.write_task_snapshot(root)

    challenger_created = app.task_service.revise_video_task(
        created.task_id,
        feedback="Create a challenger that later becomes orphaned",
        preserve_working_parts=True,
    )
    orphan = app.store.get_task(challenger_created.task_id)
    assert orphan is not None
    orphan.parent_task_id = "missing-parent"
    orphan.status = TaskStatus.QUEUED
    orphan.phase = TaskPhase.QUEUED
    orphan.delivery_status = "pending"
    app.store.update_task(orphan)
    app.artifact_store.write_task_snapshot(orphan)
    app.delivery_case_service.sync_case_for_root(created.task_id)

    restarted = create_app_context(settings)
    root_snapshot = restarted.task_service.get_video_task(created.task_id).model_dump(mode="json")
    orphan_snapshot = restarted.task_service.get_video_task(orphan.task_id).model_dump(mode="json")
    case = restarted.store.get_delivery_case(created.task_id)
    events = restarted.store.list_events(created.task_id)

    assert root_snapshot["resolved_task_id"] == created.task_id
    assert root_snapshot["delivery_status"] == "delivered"
    assert orphan_snapshot["status"] == "failed"
    assert orphan_snapshot["delivery_status"] == "failed"
    assert orphan_snapshot["delivery_stop_reason"] == "orphaned_branch"
    assert case is not None
    assert case.status == "completed"
    assert case.active_task_id == created.task_id
    assert case.selected_task_id == created.task_id
    assert any(
        event["event_type"] == "task_reliability_reconciled"
        and event["payload"].get("action") == "orphaned_branch_failed"
        and event["payload"].get("affected_task_id") == orphan.task_id
        for event in events
    )
