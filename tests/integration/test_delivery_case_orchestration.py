import json
from pathlib import Path

from video_agent.config import Settings
from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.domain.quality_models import QualityScorecard
from video_agent.server.app import create_app_context
from tests.support import bootstrapped_settings


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _build_fake_pipeline_settings(tmp_path: Path) -> Settings:
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
            auto_repair_enabled=True,
            delivery_guarantee_enabled=True,
        )
    )


def _build_failed_pipeline_settings(tmp_path: Path) -> Settings:
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

    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            manim_command=str(fake_manim),
            ffmpeg_command=str(fake_ffmpeg),
            ffprobe_command=str(fake_ffprobe),
            run_embedded_worker=False,
            auto_repair_enabled=True,
            auto_repair_max_children_per_root=1,
            auto_repair_retryable_issue_codes=["render_failed"],
            delivery_guarantee_enabled=True,
        )
    )


def test_root_task_creation_creates_delivery_case_and_orchestrator_run(tmp_path: Path) -> None:
    app = create_app_context(_build_fake_pipeline_settings(tmp_path))

    created = app.task_service.create_video_task(prompt="draw a circle")

    case = app.store.get_delivery_case(created.task_id)
    runs = app.store.list_agent_runs(created.task_id)
    generator_runs = [run for run in runs if run.role == "generator" and run.task_id == created.task_id]

    assert case is not None
    assert case.case_id == created.task_id
    assert case.root_task_id == created.task_id
    assert case.delivery_status == "pending"
    assert case.selected_task_id is None
    assert len(generator_runs) == 1
    assert generator_runs[0].status == "queued"
    assert generator_runs[0].summary == "Generator queued"
    assert any(
        run.role == "orchestrator"
        and run.status == "completed"
        and run.decision.get("action") == "case_created"
        for run in runs
    )


def test_successful_workflow_syncs_case_and_role_runs(tmp_path: Path) -> None:
    app = create_app_context(_build_fake_pipeline_settings(tmp_path))

    created = app.task_service.create_video_task(prompt="draw a circle")
    queued_generator_runs = app.store.list_agent_runs(created.task_id, role="generator", task_id=created.task_id)
    assert len(queued_generator_runs) == 1
    queued_generator_run = queued_generator_runs[0]
    assert queued_generator_run.status == "queued"
    app.worker.run_once()

    case = app.store.get_delivery_case(created.task_id)
    runs = app.store.list_agent_runs(created.task_id)
    completed_roles = {run.role for run in runs if run.status == "completed"}
    generator_runs = app.store.list_agent_runs(created.task_id, role="generator", task_id=created.task_id)

    assert case is not None
    assert case.status == "completed"
    assert case.delivery_status == "delivered"
    assert case.selected_task_id == created.task_id
    assert {"planner", "generator", "reviewer"}.issubset(completed_roles)
    assert len(generator_runs) == 1
    assert generator_runs[0].run_id == queued_generator_run.run_id
    assert generator_runs[0].status == "completed"
    assert generator_runs[0].summary == "Generation and render completed"


def test_failed_workflow_marks_existing_generator_run_failed(tmp_path: Path) -> None:
    app = create_app_context(_build_failed_pipeline_settings(tmp_path))

    created = app.task_service.create_video_task(prompt="draw a circle")
    queued_generator_runs = app.store.list_agent_runs(created.task_id, role="generator", task_id=created.task_id)
    assert len(queued_generator_runs) == 1
    queued_generator_run = queued_generator_runs[0]
    assert queued_generator_run.status == "queued"

    app.worker.run_once()

    generator_runs = app.store.list_agent_runs(created.task_id, role="generator", task_id=created.task_id)

    assert len(generator_runs) == 1
    assert generator_runs[0].run_id == queued_generator_run.run_id
    assert generator_runs[0].status == "failed"
    assert generator_runs[0].summary == "Generation failed"
    assert generator_runs[0].stop_reason == "render_failed"


def test_sync_case_marks_delivered_accepted_challenger_as_arbitrating(tmp_path: Path) -> None:
    app = create_app_context(_build_fake_pipeline_settings(tmp_path))

    created = app.task_service.create_video_task(prompt="draw a circle")
    root = app.store.get_task(created.task_id)
    assert root is not None
    root.status = TaskStatus.COMPLETED
    root.phase = TaskPhase.COMPLETED
    root.quality_gate_status = "accepted"
    root.delivery_status = "delivered"
    root.resolved_task_id = root.task_id
    root.completion_mode = "primary"
    app.store.update_task(root)
    app.artifact_store.write_task_snapshot(root)
    app.store.upsert_task_quality_score(
        root.task_id,
        QualityScorecard(
            task_id=root.task_id,
            total_score=0.91,
            accepted=True,
            decision="accept",
            summary="incumbent accepted",
        ),
    )

    challenger_created = app.task_service.revise_video_task(
        created.task_id,
        feedback="Create a stronger challenger",
        preserve_working_parts=True,
    )
    challenger = app.store.get_task(challenger_created.task_id)
    assert challenger is not None
    challenger.status = TaskStatus.COMPLETED
    challenger.phase = TaskPhase.COMPLETED
    challenger.branch_kind = "challenger"
    challenger.quality_gate_status = "accepted"
    challenger.delivery_status = "delivered"
    challenger.resolved_task_id = challenger.task_id
    challenger.completion_mode = "repaired"
    app.store.update_task(challenger)
    app.artifact_store.write_task_snapshot(challenger)
    app.store.upsert_task_quality_score(
        challenger.task_id,
        QualityScorecard(
            task_id=challenger.task_id,
            total_score=0.97,
            accepted=True,
            decision="accept",
            summary="challenger accepted",
        ),
    )

    case = app.delivery_case_service.sync_case_for_root(created.task_id)

    assert case is not None
    assert case.status == "arbitrating"
    assert case.selected_task_id == created.task_id
    assert case.active_task_id == challenger.task_id


def test_sync_case_marks_validation_phase_task_as_reviewing(tmp_path: Path) -> None:
    app = create_app_context(_build_fake_pipeline_settings(tmp_path))

    created = app.task_service.create_video_task(prompt="draw a circle")
    task = app.store.get_task(created.task_id)
    assert task is not None
    task.status = TaskStatus.RUNNING
    task.phase = TaskPhase.VALIDATION
    app.store.update_task(task)
    app.artifact_store.write_task_snapshot(task)

    case = app.delivery_case_service.sync_case_for_root(created.task_id)

    assert case is not None
    assert case.status == "reviewing"
    assert case.active_task_id == created.task_id


def test_failed_root_with_auto_repair_records_repairer_run(tmp_path: Path) -> None:
    app = create_app_context(_build_failed_pipeline_settings(tmp_path))

    created = app.task_service.create_video_task(prompt="draw a circle")
    app.worker.run_once()

    case = app.store.get_delivery_case(created.task_id)
    runs = app.store.list_agent_runs(created.task_id, role="repairer")

    assert case is not None
    assert case.status == "repairing"
    assert case.delivery_status == "pending"
    assert case.selected_task_id is None
    assert case.active_task_id is not None
    assert case.active_task_id != created.task_id
    assert len(runs) >= 1
    assert runs[-1].status == "completed"
    assert runs[-1].decision["created"] is True
    assert runs[-1].decision["child_task_id"]
