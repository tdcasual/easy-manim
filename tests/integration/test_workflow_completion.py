import json
import sqlite3
from pathlib import Path

from video_agent.adapters.llm.client import StubLLMClient
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.config import Settings
from video_agent.safety.runtime_policy import RuntimePolicy
from video_agent.server.app import create_app_context
from tests.support import bootstrapped_settings



def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)



def _build_fake_pipeline_settings(tmp_path: Path, **overrides) -> Settings:
    data_dir = tmp_path / "data"

    fake_manim = tmp_path / "fake_manim.sh"
    _write_executable(
        fake_manim,
        "#!/bin/sh\n"
        "if [ \"$1\" != \"-ql\" ]; then exit 11; fi\n"
        "if [ \"$4\" != \"--media_dir\" ]; then exit 12; fi\n"
        "if [ \"$6\" != \"-o\" ]; then exit 13; fi\n"
        "printf '%s' \"$TEXMFCNF\" > \"$5/env-captured.txt\"\n"
        "script_name=$(basename \"$2\" .py)\n"
        "mkdir -p \"$5/videos/$script_name/480p15\"\n"
        "printf 'normal-video' > \"$5/videos/$script_name/480p15/$7\"\n"
        "printf 'render ok\\n'\n",
    )

    fake_ffprobe = tmp_path / "fake_ffprobe.sh"
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

    fake_ffmpeg = tmp_path / "fake_ffmpeg.sh"
    _write_executable(
        fake_ffmpeg,
        "#!/bin/sh\n"
        "if [ \"$1\" != \"-y\" ]; then exit 20; fi\n"
        "if [ \"$2\" != \"-i\" ]; then exit 21; fi\n"
        "if [ \"$4\" != \"-vf\" ]; then exit 22; fi\n"
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
        "delivery_guarantee_enabled": False,
    }
    values.update(overrides)
    return bootstrapped_settings(Settings(**values))



def _load_event_payloads(database_path: Path, task_id: str, event_type: str) -> list[dict[str, object]]:
    connection = sqlite3.connect(database_path)
    try:
        rows = connection.execute(
            "SELECT payload_json FROM task_events WHERE task_id = ? AND event_type = ? ORDER BY id ASC",
            (task_id, event_type),
        ).fetchall()
    finally:
        connection.close()
    return [json.loads(row[0]) for row in rows]


def _write_delivery_canary_result(app_context, *, delivered: bool) -> None:
    target = app_context.settings.eval_root / "delivery-canary" / "latest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"task_id": "canary-task", "delivered": delivered}))


class CapturingLLMClient:
    def __init__(self) -> None:
        self.last_prompt: str | None = None

    def generate_script(self, prompt_text: str) -> str:
        self.last_prompt = prompt_text
        return (
            "from manim import Scene\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        pass\n"
        )


def _seed_agent_memory(
    app_context,
    *,
    memory_id: str,
    agent_id: str,
    summary_text: str,
    status: str = "active",
) -> None:
    app_context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id=memory_id,
            agent_id=agent_id,
            source_session_id=f"session-{agent_id}",
            status=status,
            summary_text=summary_text,
            summary_digest=f"digest-{memory_id}",
        )
    )



def test_task_becomes_completed_only_after_validation_passes(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="complete")

    processed = app_context.worker.run_once()
    snapshot = app_context.task_service.get_video_task(created.task_id)

    assert processed == 1
    assert snapshot.status == "completed"
    assert snapshot.latest_validation_summary["passed"] is True
    assert snapshot.repair_state["attempted"] is False
    assert snapshot.repair_state["child_count"] == 0
    assert snapshot.repair_state["last_issue_code"] is None
    assert snapshot.repair_state["stop_reason"] is None


def test_quality_rejected_delivery_auto_queues_challenger_branch(tmp_path: Path) -> None:
    app_context = create_app_context(
        _build_fake_pipeline_settings(
            tmp_path,
            multi_agent_workflow_enabled=True,
            quality_gate_min_score=0.95,
            multi_agent_workflow_max_child_attempts=1,
        )
    )
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="auto-challenger")

    processed = app_context.worker.run_once()
    root_snapshot = app_context.task_service.get_video_task(created.task_id).model_dump(mode="json")
    lineage = app_context.store.list_lineage_tasks(created.task_id)
    case = app_context.store.get_delivery_case(created.task_id)
    runs = app_context.store.list_agent_runs(created.task_id, role="orchestrator")

    assert processed == 1
    assert root_snapshot["status"] == "completed"
    assert root_snapshot["delivery_status"] == "delivered"
    assert root_snapshot["quality_gate_status"] == "needs_revision"
    assert root_snapshot["resolved_task_id"] == created.task_id
    assert len(lineage) == 2
    assert lineage[-1].task_id != created.task_id
    assert lineage[-1].parent_task_id == created.task_id
    assert lineage[-1].status == "queued"
    assert case is not None
    assert case.status == "branching"
    assert case.selected_task_id == created.task_id
    assert case.active_task_id == lineage[-1].task_id
    assert any(
        run.decision.get("action") == "challenger_created"
        and run.decision.get("challenger_task_id") == lineage[-1].task_id
        for run in runs
    )


def test_auto_challenger_respects_role_governance_flag(tmp_path: Path) -> None:
    app_context = create_app_context(
        _build_fake_pipeline_settings(
            tmp_path,
            multi_agent_workflow_enabled=True,
            multi_agent_workflow_auto_challenger_enabled=False,
            quality_gate_min_score=0.95,
            multi_agent_workflow_max_child_attempts=1,
        )
    )
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        idempotency_key="auto-challenger-governance-off",
    )

    processed = app_context.worker.run_once()
    root_snapshot = app_context.task_service.get_video_task(created.task_id).model_dump(mode="json")
    lineage = app_context.store.list_lineage_tasks(created.task_id)
    case = app_context.store.get_delivery_case(created.task_id)
    decisions = _load_event_payloads(app_context.settings.database_path, created.task_id, "auto_challenger_decision")

    assert processed == 1
    assert root_snapshot["status"] == "completed"
    assert root_snapshot["delivery_status"] == "delivered"
    assert root_snapshot["quality_gate_status"] == "needs_revision"
    assert len(lineage) == 1
    assert case is not None
    assert case.status == "completed"
    assert case.active_task_id == created.task_id
    assert decisions[-1]["created"] is False
    assert decisions[-1]["reason"] == "auto_challenger_governance_disabled"


def test_guarded_rollout_blocks_auto_challenger_without_healthy_canary(tmp_path: Path) -> None:
    app_context = create_app_context(
        _build_fake_pipeline_settings(
            tmp_path,
            capability_rollout_profile="autonomy-guarded",
            quality_gate_min_score=0.95,
            multi_agent_workflow_max_child_attempts=1,
        )
    )
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        idempotency_key="guarded-rollout-no-canary",
    )

    app_context.worker.run_once()
    lineage = app_context.store.list_lineage_tasks(created.task_id)
    decisions = _load_event_payloads(app_context.settings.database_path, created.task_id, "auto_challenger_decision")

    assert len(lineage) == 1
    assert decisions[-1]["created"] is False
    assert decisions[-1]["reason"] == "guarded_rollout_blocked"
    assert decisions[-1]["blocked_reasons"] == ["delivery_canary_unavailable"]


def test_guarded_rollout_blocks_auto_challenger_when_branch_rejection_rate_regresses(tmp_path: Path) -> None:
    app_context = create_app_context(
        _build_fake_pipeline_settings(
            tmp_path,
            capability_rollout_profile="autonomy-guarded",
            quality_gate_min_score=0.95,
            multi_agent_workflow_max_child_attempts=1,
            multi_agent_workflow_guarded_max_branch_rejection_rate=0.25,
        )
    )
    _write_delivery_canary_result(app_context, delivered=True)

    historical = app_context.task_service.create_video_task(
        prompt="draw a square",
        idempotency_key="historical-branch-rejection",
    )
    historical_task = app_context.store.get_task(historical.task_id)
    assert historical_task is not None
    historical_task.status = historical_task.status.COMPLETED
    historical_task.phase = historical_task.phase.COMPLETED
    historical_task.delivery_status = "delivered"
    historical_task.completion_mode = "primary"
    historical_task.resolved_task_id = historical_task.task_id
    app_context.store.update_task(historical_task)
    historical_child = app_context.task_service.create_challenger_task(
        historical.task_id,
        feedback="raise quality",
    )
    historical_child_task = app_context.store.get_task(historical_child.task_id)
    assert historical_child_task is not None
    historical_child_task.status = historical_child_task.status.COMPLETED
    historical_child_task.phase = historical_child_task.phase.COMPLETED
    historical_child_task.delivery_status = "delivered"
    historical_child_task.quality_gate_status = "accepted"
    historical_child_task.completion_mode = "repaired"
    app_context.store.update_task(historical_child_task)
    app_context.delivery_case_service.record_auto_arbitration_evaluated(
        task=historical_child_task,
        arbitration_summary={
            "recommended_task_id": historical.task_id,
            "recommended_action": "keep_incumbent",
            "selected_task_id": historical.task_id,
            "candidate_count": 2,
            "reason": "incumbent_has_best_accepted_score",
        },
        promoted=False,
    )

    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        idempotency_key="guarded-rollout-branch-regression",
    )

    app_context.worker.run_once()
    lineage = app_context.store.list_lineage_tasks(created.task_id)
    decisions = _load_event_payloads(app_context.settings.database_path, created.task_id, "auto_challenger_decision")

    assert len(lineage) == 1
    assert decisions[-1]["created"] is False
    assert decisions[-1]["reason"] == "guarded_rollout_blocked"
    assert decisions[-1]["blocked_reasons"] == ["branch_rejection_rate_above_threshold"]


def test_completed_challenger_does_not_replace_incumbent_until_accepted(tmp_path: Path) -> None:
    app_context = create_app_context(
        _build_fake_pipeline_settings(
            tmp_path,
            multi_agent_workflow_enabled=True,
            quality_gate_min_score=0.95,
            multi_agent_workflow_max_child_attempts=1,
        )
    )
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        idempotency_key="challenger-incumbent-guard",
    )

    app_context.worker.run_once()
    app_context.worker.run_once()
    root_snapshot = app_context.task_service.get_video_task(created.task_id).model_dump(mode="json")
    result = app_context.task_service.get_video_result(created.task_id).model_dump(mode="json")
    lineage = app_context.store.list_lineage_tasks(created.task_id)
    challenger = lineage[-1]
    case = app_context.store.get_delivery_case(created.task_id)

    assert len(lineage) == 2
    assert challenger.task_id != created.task_id
    assert challenger.status.value == "completed"
    assert root_snapshot["resolved_task_id"] == created.task_id
    assert result["resolved_task_id"] == created.task_id
    assert result["video_resource"] == f"video-task://{created.task_id}/artifacts/final_video.mp4"
    assert case is not None
    assert case.status == "completed"
    assert case.selected_task_id == created.task_id


def test_guarded_rollout_allows_auto_promotion_with_healthy_canary_and_slo(tmp_path: Path) -> None:
    app_context = create_app_context(
        _build_fake_pipeline_settings(
            tmp_path,
            capability_rollout_profile="autonomy-guarded",
            quality_gate_min_score=0.95,
            multi_agent_workflow_max_child_attempts=1,
        )
    )
    _write_delivery_canary_result(app_context, delivered=True)
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        idempotency_key="guarded-rollout-green",
    )

    app_context.worker.run_once()
    lineage_after_root = app_context.store.list_lineage_tasks(created.task_id)
    challenger = lineage_after_root[-1]
    app_context.workflow_engine.quality_judge_service.min_score = 0.90

    app_context.worker.run_once()
    root_snapshot = app_context.task_service.get_video_task(created.task_id).model_dump(mode="json")
    decisions = _load_event_payloads(app_context.settings.database_path, created.task_id, "auto_arbitration_decision")

    assert challenger.task_id != created.task_id
    assert root_snapshot["resolved_task_id"] == challenger.task_id
    assert decisions[-1]["promoted"] is True


def test_auto_arbitration_respects_role_governance_flag(tmp_path: Path) -> None:
    app_context = create_app_context(
        _build_fake_pipeline_settings(
            tmp_path,
            multi_agent_workflow_enabled=True,
            multi_agent_workflow_auto_arbitration_enabled=False,
            quality_gate_min_score=0.95,
            multi_agent_workflow_max_child_attempts=1,
        )
    )
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        idempotency_key="auto-arbitration-governance-off",
    )

    app_context.worker.run_once()
    lineage_after_root = app_context.store.list_lineage_tasks(created.task_id)
    challenger = lineage_after_root[-1]
    app_context.workflow_engine.quality_judge_service.min_score = 0.90

    app_context.worker.run_once()
    root_snapshot = app_context.task_service.get_video_task(created.task_id).model_dump(mode="json")
    case = app_context.store.get_delivery_case(created.task_id)
    decisions = _load_event_payloads(app_context.settings.database_path, created.task_id, "auto_arbitration_decision")

    assert challenger.task_id != created.task_id
    assert root_snapshot["resolved_task_id"] == created.task_id
    assert case is not None
    assert case.status == "arbitrating"
    assert case.selected_task_id == created.task_id
    assert decisions[-1]["promoted"] is False
    assert decisions[-1]["reason"] == "auto_arbitration_governance_disabled"
    assert decisions[-1]["selected_task_id"] is None


def test_guarded_rollout_blocks_auto_arbitration_when_delivery_rate_regresses(tmp_path: Path) -> None:
    app_context = create_app_context(
        _build_fake_pipeline_settings(
            tmp_path,
            capability_rollout_profile="autonomy-guarded",
            quality_gate_min_score=0.95,
            multi_agent_workflow_max_child_attempts=1,
            multi_agent_workflow_guarded_min_delivery_rate=0.75,
        )
    )
    _write_delivery_canary_result(app_context, delivered=True)
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        idempotency_key="guarded-rollout-slo-regression",
    )

    app_context.worker.run_once()
    degraded = app_context.task_service.create_video_task(prompt="draw a square", idempotency_key="degraded-slo-root")
    degraded_task = app_context.store.get_task(degraded.task_id)
    assert degraded_task is not None
    degraded_task.status = degraded_task.status.FAILED
    degraded_task.phase = degraded_task.phase.FAILED
    degraded_task.delivery_status = "failed"
    degraded_task.delivery_stop_reason = "runtime_unhealthy"
    app_context.store.update_task(degraded_task)
    app_context.workflow_engine.quality_judge_service.min_score = 0.90

    app_context.worker.run_once()
    root_snapshot = app_context.task_service.get_video_task(created.task_id).model_dump(mode="json")
    decisions = _load_event_payloads(app_context.settings.database_path, created.task_id, "auto_arbitration_decision")

    assert root_snapshot["resolved_task_id"] == created.task_id
    assert decisions[-1]["promoted"] is False
    assert decisions[-1]["reason"] == "guarded_rollout_blocked"
    assert decisions[-1]["blocked_reasons"] == ["delivery_rate_below_threshold"]


def test_completed_accepted_challenger_auto_promotes_to_winner(tmp_path: Path) -> None:
    app_context = create_app_context(
        _build_fake_pipeline_settings(
            tmp_path,
            multi_agent_workflow_enabled=True,
            quality_gate_min_score=0.95,
            multi_agent_workflow_max_child_attempts=1,
        )
    )
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        idempotency_key="challenger-auto-promote",
    )

    app_context.worker.run_once()
    lineage_after_root = app_context.store.list_lineage_tasks(created.task_id)
    challenger = lineage_after_root[-1]
    app_context.workflow_engine.quality_judge_service.min_score = 0.90

    app_context.worker.run_once()
    root_snapshot = app_context.task_service.get_video_task(created.task_id).model_dump(mode="json")
    result = app_context.task_service.get_video_result(created.task_id).model_dump(mode="json")
    case = app_context.store.get_delivery_case(created.task_id)
    runs = app_context.store.list_agent_runs(created.task_id, role="orchestrator")

    assert challenger.task_id != created.task_id
    assert root_snapshot["resolved_task_id"] == challenger.task_id
    assert result["resolved_task_id"] == challenger.task_id
    assert result["video_resource"] == f"video-task://{challenger.task_id}/artifacts/final_video.mp4"
    assert case is not None
    assert case.selected_task_id == challenger.task_id
    assert any(
        run.decision.get("action") == "auto_arbitration_evaluated"
        and run.decision.get("recommended_action") == "promote_challenger"
        and run.decision.get("recommended_task_id") == challenger.task_id
        for run in runs
    )
    assert any(
        run.decision.get("action") == "winner_selected"
        and run.decision.get("selected_task_id") == challenger.task_id
        for run in runs
    )


def test_auto_challenger_feedback_inherits_shared_case_memory_constraints(tmp_path: Path) -> None:
    app_context = create_app_context(
        _build_fake_pipeline_settings(
            tmp_path,
            multi_agent_workflow_enabled=True,
            quality_gate_min_score=0.95,
            multi_agent_workflow_max_child_attempts=1,
        )
    )
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        idempotency_key="challenger-feedback-shared-memory",
    )

    app_context.worker.run_once()
    lineage = app_context.store.list_lineage_tasks(created.task_id)
    challenger = lineage[-1]

    assert challenger.task_id != created.task_id
    assert challenger.feedback is not None
    assert "Shared case constraints" in challenger.feedback
    assert "Preserve core prompt intent" in challenger.feedback


def test_completed_task_updates_session_memory_outcome(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        idempotency_key="complete-session-memory",
        session_id="session-1",
    )

    app_context.worker.run_once()
    summary = app_context.session_memory_service.get_session_memory("session-1")

    entry = summary.entries[0]
    assert entry.latest_status == "completed"
    assert entry.latest_result_summary == "Validation passed"
    assert f"video-task://{created.task_id}/artifacts/final_video.mp4" in entry.artifact_refs


def test_create_task_uses_selected_persistent_memory_context(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    app_context.workflow_engine.llm_client = CapturingLLMClient()
    _seed_agent_memory(
        app_context,
        memory_id="mem-a",
        agent_id="local-anonymous",
        summary_text="Always prefer a warm light background and explicit labels.",
    )

    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        session_id="session-1",
        memory_ids=["mem-a"],
    )
    task = app_context.store.get_task(created.task_id)
    app_context.worker.run_once()

    assert task is not None
    assert task.persistent_memory_context_summary is not None
    assert "Persistent memory context:" in app_context.workflow_engine.llm_client.last_prompt
    assert "warm light background" in app_context.workflow_engine.llm_client.last_prompt


def test_create_without_memory_ids_has_no_persistent_memory_context(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    app_context.workflow_engine.llm_client = CapturingLLMClient()

    created = app_context.task_service.create_video_task(prompt="draw a circle", session_id="session-1")
    task = app_context.store.get_task(created.task_id)
    app_context.worker.run_once()

    assert task is not None
    assert task.persistent_memory_context_summary is None
    assert "Persistent memory context:" not in app_context.workflow_engine.llm_client.last_prompt



def test_get_video_result_returns_artifacts_for_completed_task(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="result")

    app_context.worker.run_once()
    result = app_context.task_service.get_video_result(created.task_id)

    assert result.video_resource == f"video-task://{created.task_id}/artifacts/final_video.mp4"
    assert app_context.artifact_store.final_video_path(created.task_id).exists()
    assert len(result.preview_frame_resources) >= 1



def test_successful_task_records_structured_logs_and_metrics(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="observability")

    app_context.worker.run_once()
    log_events = _load_event_payloads(app_context.settings.database_path, created.task_id, "task_log")

    assert any(event["phase"] == "rendering" and event["attempt_count"] == 1 for event in log_events)
    assert all(event["task_id"] == created.task_id for event in log_events)
    assert app_context.metrics.counters["generation_runs"] == 1
    assert app_context.metrics.counters["render_runs"] == 1
    assert app_context.metrics.counters["validation_runs"] == 1
    assert len(app_context.metrics.timings["generation_seconds"]) == 1
    assert len(app_context.metrics.timings["render_seconds"]) == 1
    assert len(app_context.metrics.timings["validation_seconds"]) == 1



def test_runtime_policy_blocks_artifacts_outside_allowed_root(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    app_context.workflow_engine.runtime_policy = RuntimePolicy(work_root=tmp_path / "sandbox")
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="policy")

    app_context.worker.run_once()
    snapshot = app_context.task_service.get_video_task(created.task_id)

    assert snapshot.status == "failed"
    assert snapshot.latest_validation_summary["issues"][0]["code"] == "runtime_policy_violation"


def test_task_succeeds_when_provider_returns_markdown_fenced_code(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    app_context.workflow_engine.llm_client = StubLLMClient(
        script=(
            "```python\n"
            "from manim import Scene\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        pass\n"
            "```\n"
        )
    )
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="fenced")

    app_context.worker.run_once()
    snapshot = app_context.task_service.get_video_task(created.task_id)

    assert snapshot.status == "completed"


def test_task_fails_before_render_when_mathtex_dependencies_are_missing(tmp_path: Path) -> None:
    settings = _build_fake_pipeline_settings(tmp_path)
    settings.latex_command = "missing-latex"
    settings.dvisvgm_command = "missing-dvisvgm"
    app_context = create_app_context(settings)
    app_context.workflow_engine.llm_client = StubLLMClient(
        script=(
            "from manim import MathTex, Scene\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        self.add(MathTex(r'x^2 + y^2 = z^2'))\n"
        )
    )
    created = app_context.task_service.create_video_task(prompt="show a formula", idempotency_key="mathtex-missing")

    app_context.worker.run_once()
    snapshot = app_context.task_service.get_video_task(created.task_id)

    assert snapshot.status == "failed"
    assert snapshot.latest_validation_summary["issues"][0]["code"] == "latex_dependency_missing"
    assert snapshot.latest_validation_summary["details"]["missing_checks"] == ["latex", "dvisvgm"]
    assert app_context.metrics.counters.get("render_runs", 0) == 0


def test_workflow_forwards_configured_render_environment(tmp_path: Path) -> None:
    settings = _build_fake_pipeline_settings(tmp_path)
    settings.render_environment = {"TEXMFCNF": "/configured/path"}
    app_context = create_app_context(settings)
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="render-env")

    app_context.worker.run_once()

    captured = app_context.artifact_store.task_dir(created.task_id) / "artifacts" / "env-captured.txt"
    assert captured.read_text() == "/configured/path"


def test_workflow_persists_scene_plan_artifact(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(
        prompt="show an axis animation and highlight the midpoint",
        idempotency_key="scene-plan",
        output_profile={"quality_preset": "production"},
        style_hints={"tone": "clean", "pace": "steady"},
    )

    app_context.worker.run_once()

    scene_plan_path = app_context.artifact_store.task_dir(created.task_id) / "artifacts" / "scene_plan.json"
    scene_spec_path = app_context.artifact_store.task_dir(created.task_id) / "artifacts" / "scene_spec.json"
    assert scene_plan_path.exists()
    assert scene_spec_path.exists()
    payload = json.loads(scene_plan_path.read_text())
    scene_spec = json.loads(scene_spec_path.read_text())
    assert payload["scene_class"] == "MovingCameraScene"
    assert payload["camera_strategy"] == "auto_zoom"
    assert payload["pacing_strategy"] == "measured"
    assert scene_spec["camera_strategy"] == "auto_zoom"
    assert "avoid_blank_opening_frame" in payload["quality_directives"]


def test_scene_plan_uses_resolved_default_quality_profile(tmp_path: Path) -> None:
    settings = _build_fake_pipeline_settings(tmp_path)
    settings.default_quality_preset = "production"
    app_context = create_app_context(settings)
    created = app_context.task_service.create_video_task(
        prompt="show the quadratic formula and briefly highlight the discriminant",
        idempotency_key="scene-plan-default-quality",
    )

    app_context.worker.run_once()

    scene_plan_path = app_context.artifact_store.task_dir(created.task_id) / "artifacts" / "scene_plan.json"
    payload = json.loads(scene_plan_path.read_text())

    assert "avoid_blank_opening_frame" in payload["quality_directives"]
    assert "favor_readable_spacing" in payload["quality_directives"]
