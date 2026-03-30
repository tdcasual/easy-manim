import json
from pathlib import Path

from video_agent.adapters.rendering.emergency_video_writer import EmergencyVideoWriter
import video_agent.server.app as app_module
from video_agent.application.delivery_guarantee_service import DeliveryGuaranteeService
from video_agent.config import Settings
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
        "delivery_guarantee_enabled": True,
    }
    values.update(overrides)
    return bootstrapped_settings(Settings(**values))


def _build_degraded_success_settings(tmp_path: Path, **overrides) -> Settings:
    data_dir = tmp_path / "data"

    fake_manim = tmp_path / "fake_manim_degraded_success.sh"
    _write_executable(
        fake_manim,
        "#!/bin/sh\n"
        "script_path=\"$2\"\n"
        "script_name=$(basename \"$script_path\" .py)\n"
        "mkdir -p \"$5/videos/$script_name/480p15\"\n"
        "if grep -q \"GUARANTEED_DELIVERY_DEGRADED\" \"$script_path\"; then\n"
        "  printf 'degraded-video' > \"$5/videos/$script_name/480p15/$7\"\n"
        "  exit 0\n"
        "fi\n"
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
        "delivery_guarantee_enabled": True,
    }
    values.update(overrides)
    return bootstrapped_settings(Settings(**values))


class _DegradedSuccessLLMClient:
    def generate_script(self, prompt_text: str) -> str:
        marker = ""
        if "Guaranteed delivery degraded fallback" in prompt_text:
            marker = "\n# GUARANTEED_DELIVERY_DEGRADED\n"
        return (
            "from manim import Scene\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        pass\n"
            f"{marker}"
        )


def test_root_snapshot_exposes_delivery_guarantee_metadata(tmp_path: Path) -> None:
    app = create_app_context(_build_failed_pipeline_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()
    root_snapshot = app.task_service.get_video_task(created.task_id).model_dump(mode="json")

    assert root_snapshot["delivery_status"] == "pending"
    assert root_snapshot["resolved_task_id"] is None
    assert root_snapshot["completion_mode"] is None
    assert root_snapshot["delivery_tier"] is None
    assert root_snapshot["delivery_stop_reason"] is None


def test_root_result_resolves_to_delivered_descendant_instead_of_failed_root(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "_build_llm_client", lambda settings: _DegradedSuccessLLMClient(), raising=False)
    app = create_app_context(_build_degraded_success_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()
    app.worker.run_once()
    app.worker.run_once()
    lineage = app.store.list_lineage_tasks(created.task_id)
    result = app.task_service.get_video_result(created.task_id).model_dump(mode="json")

    assert result["ready"] is True
    assert result["completion_mode"] == "degraded"
    assert result["delivery_status"] == "delivered"
    assert len(lineage) == 3
    assert result["resolved_task_id"] == lineage[-1].task_id
    assert result["video_resource"] is not None


def test_delivery_guarantee_queues_degraded_child_before_emergency_fallback(tmp_path: Path) -> None:
    app = create_app_context(_build_failed_pipeline_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()
    app.worker.run_once()

    lineage = app.store.list_lineage_tasks(created.task_id)
    degraded_child = lineage[-1]
    root_snapshot = app.task_service.get_video_task(created.task_id).model_dump(mode="json")
    result = app.task_service.get_video_result(created.task_id).model_dump(mode="json")

    assert len(lineage) == 3
    assert degraded_child.parent_task_id == lineage[1].task_id
    assert degraded_child.completion_mode == "degraded"
    assert degraded_child.delivery_status == "pending"
    assert degraded_child.status == "queued"
    assert root_snapshot["delivery_status"] == "pending"
    assert result["ready"] is False


def test_root_result_can_still_deliver_emergency_fallback_when_repairs_cannot_run(tmp_path: Path) -> None:
    app = create_app_context(
        _build_failed_pipeline_settings(
            tmp_path,
            auto_repair_enabled=False,
        )
    )
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()
    result = app.task_service.get_video_result(created.task_id).model_dump(mode="json")

    assert result["ready"] is True
    assert result["completion_mode"] == "emergency_fallback"
    assert result["delivery_status"] == "delivered"
    assert result["video_resource"] is not None


def test_emergency_fallback_uses_embedded_video_when_ffmpeg_is_missing(tmp_path: Path) -> None:
    app = create_app_context(
        _build_failed_pipeline_settings(
            tmp_path,
            auto_repair_enabled=False,
            ffmpeg_command="definitely-missing-ffmpeg-binary",
        )
    )
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()
    result = app.task_service.get_video_result(created.task_id).model_dump(mode="json")

    assert result["ready"] is True
    assert result["completion_mode"] == "emergency_fallback"
    assert result["delivery_status"] == "delivered"
    assert app.artifact_store.final_video_path(created.task_id).exists()


def test_leaf_attempt_marks_its_own_delivery_failed_when_guarantee_is_disabled(tmp_path: Path) -> None:
    app = create_app_context(
        _build_failed_pipeline_settings(
            tmp_path,
            auto_repair_enabled=True,
            auto_repair_max_children_per_root=1,
            delivery_guarantee_enabled=False,
        )
    )
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()
    app.worker.run_once()

    lineage = app.store.list_lineage_tasks(created.task_id)
    child = next(task for task in lineage if task.task_id != created.task_id)
    child_snapshot = app.task_service.get_video_task(child.task_id).model_dump(mode="json")
    root_snapshot = app.task_service.get_video_task(created.task_id).model_dump(mode="json")

    assert root_snapshot["delivery_status"] == "failed"
    assert root_snapshot["delivery_stop_reason"] == "disabled"
    assert child_snapshot["status"] == "failed"
    assert child_snapshot["delivery_status"] == "failed"
    assert child_snapshot["delivery_stop_reason"] == "disabled"


def test_delivery_guarantee_exceptions_do_not_crash_worker(tmp_path: Path) -> None:
    class _ExplodingWriter:
        def write(self, output_path: Path) -> Path:
            raise RuntimeError("simulated delivery failure")

    app = create_app_context(
        _build_failed_pipeline_settings(
            tmp_path,
            auto_repair_enabled=False,
            delivery_guarantee_enabled=True,
        )
    )
    app.workflow_engine.delivery_guarantee_service = DeliveryGuaranteeService(
        settings=app.settings,
        artifact_store=app.artifact_store,
        emergency_video_writer=_ExplodingWriter(),
    )
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()

    snapshot = app.task_service.get_video_task(created.task_id).model_dump(mode="json")
    result = app.task_service.get_video_result(created.task_id).model_dump(mode="json")

    assert snapshot["status"] == "failed"
    assert snapshot["delivery_status"] == "failed"
    assert snapshot["delivery_stop_reason"] == "delivery_exception"
    assert result["ready"] is False
    assert result["delivery_status"] == "failed"
    assert result["delivery_stop_reason"] == "delivery_exception"


def test_invalid_emergency_fallback_is_rejected_without_overwriting_result(tmp_path: Path) -> None:
    app = create_app_context(
        _build_failed_pipeline_settings(
            tmp_path,
            auto_repair_enabled=False,
            delivery_guarantee_enabled=True,
        )
    )
    app.workflow_engine.delivery_guarantee_service = DeliveryGuaranteeService(
        settings=app.settings,
        artifact_store=app.artifact_store,
        emergency_video_writer=EmergencyVideoWriter(
            command="definitely-missing-ffmpeg",
            validator=lambda _path: False,
        ),
    )
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()

    snapshot = app.task_service.get_video_task(created.task_id).model_dump(mode="json")
    result = app.task_service.get_video_result(created.task_id).model_dump(mode="json")

    assert snapshot["status"] == "failed"
    assert snapshot["delivery_status"] == "failed"
    assert snapshot["delivery_stop_reason"] == "invalid_emergency_video"
    assert result["ready"] is False
    assert result["delivery_status"] == "failed"
    assert result["delivery_stop_reason"] == "invalid_emergency_video"
    assert not app.artifact_store.final_video_path(created.task_id).exists()
