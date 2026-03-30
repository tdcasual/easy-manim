# Roadmap requires this alignment suite under unit path even though it validates
# cross-surface behavior through public service entry points.
import json
from pathlib import Path
import sys
import types
from collections.abc import Callable

if "mcp.server.fastmcp" not in sys.modules:
    mcp_module = types.ModuleType("mcp")
    mcp_server_module = types.ModuleType("mcp.server")
    mcp_fastmcp_module = types.ModuleType("mcp.server.fastmcp")

    class _ImportContext:  # pragma: no cover - test import shim
        pass

    mcp_fastmcp_module.Context = _ImportContext
    mcp_server_module.fastmcp = mcp_fastmcp_module
    mcp_module.server = mcp_server_module
    sys.modules["mcp"] = mcp_module
    sys.modules["mcp.server"] = mcp_server_module
    sys.modules["mcp.server.fastmcp"] = mcp_fastmcp_module

from fastapi.testclient import TestClient

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.application.agent_learning_service import quality_score_from_scorecard
from video_agent.application.eval_service import EvaluationService
from video_agent.config import Settings
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.agent_models import AgentProfile, AgentToken
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


def _load_server_app_module():
    def _load():
        import video_agent.server.app as app_module

        return app_module

    return _with_temporary_mcp_shim(_load)


def _create_app_context(settings: Settings):
    app_module = _load_server_app_module()
    return app_module.create_app_context(settings)


def _create_http_api(settings: Settings):
    def _load():
        from video_agent.server.http_api import create_http_api

        return create_http_api(settings)

    return _with_temporary_mcp_shim(_load)


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _build_quality_alignment_settings(
    tmp_path: Path,
    *,
    auth_mode: str = "optional",
    auto_apply_enabled: bool = False,
    auto_apply_min_completed_tasks: int = 1,
    auto_apply_min_quality_score: float = 0.0,
) -> Settings:
    data_dir = tmp_path / "data"

    fake_manim = tmp_path / "fake_manim.sh"
    _write_executable(
        fake_manim,
        "#!/bin/sh\n"
        "script_path=''\n"
        "media_dir=''\n"
        "output_name=''\n"
        "while [ $# -gt 0 ]; do\n"
        "  case \"$1\" in\n"
        "    --media_dir)\n"
        "      shift\n"
        "      media_dir=\"$1\"\n"
        "      ;;\n"
        "    -o)\n"
        "      shift\n"
        "      output_name=\"$1\"\n"
        "      ;;\n"
        "    *.py)\n"
        "      script_path=\"$1\"\n"
        "      ;;\n"
        "  esac\n"
        "  shift\n"
        "done\n"
        "if [ -z \"$script_path\" ]; then exit 11; fi\n"
        "if [ -z \"$media_dir\" ]; then exit 12; fi\n"
        "if [ -z \"$output_name\" ]; then exit 13; fi\n"
        "script_name=$(basename \"$script_path\" .py)\n"
        "mkdir -p \"$media_dir/videos/$script_name/480p15\"\n"
        "printf 'normal-video' > \"$media_dir/videos/$script_name/480p15/$output_name\"\n",
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
        "verbosity=''\n"
        "output_format=''\n"
        "while [ $# -gt 0 ]; do\n"
        "  case \"$1\" in\n"
        "    -v)\n"
        "      shift\n"
        "      verbosity=\"$1\"\n"
        "      ;;\n"
        "    -of)\n"
        "      shift\n"
        "      output_format=\"$1\"\n"
        "      ;;\n"
        "  esac\n"
        "  shift\n"
        "done\n"
        "if [ \"$verbosity\" != 'error' ]; then exit 31; fi\n"
        "if [ \"$output_format\" != 'json' ]; then exit 32; fi\n"
        f"printf '%s' '{probe_json}'\n",
    )

    fake_ffmpeg = tmp_path / "fake_ffmpeg.sh"
    _write_executable(
        fake_ffmpeg,
        "#!/bin/sh\n"
        "input_path=''\n"
        "vf_filter=''\n"
        "output_path=''\n"
        "while [ $# -gt 0 ]; do\n"
        "  case \"$1\" in\n"
        "    -i)\n"
        "      shift\n"
        "      input_path=\"$1\"\n"
        "      ;;\n"
        "    -vf)\n"
        "      shift\n"
        "      vf_filter=\"$1\"\n"
        "      ;;\n"
        "    -*)\n"
        "      ;;\n"
        "    *)\n"
        "      output_path=\"$1\"\n"
        "      ;;\n"
        "  esac\n"
        "  shift\n"
        "done\n"
        "if [ -z \"$input_path\" ]; then exit 21; fi\n"
        "if [ -z \"$vf_filter\" ]; then exit 22; fi\n"
        "if [ -z \"$output_path\" ]; then exit 23; fi\n"
        "mkdir -p \"$(dirname \"$output_path\")\"\n"
        "printf 'frame1' > \"$(dirname \"$output_path\")/frame_001.png\"\n",
    )

    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            eval_root=data_dir / "evals",
            manim_command=str(fake_manim),
            ffmpeg_command=str(fake_ffmpeg),
            ffprobe_command=str(fake_ffprobe),
            run_embedded_worker=False,
            auth_mode=auth_mode,
            agent_learning_auto_apply_enabled=auto_apply_enabled,
            agent_learning_auto_apply_min_completed_tasks=auto_apply_min_completed_tasks,
            agent_learning_auto_apply_min_quality_score=auto_apply_min_quality_score,
            agent_learning_auto_apply_max_recent_failures=0,
        )
    )


def _build_degraded_quality_alignment_settings(tmp_path: Path) -> Settings:
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

    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            eval_root=data_dir / "evals",
            manim_command=str(fake_manim),
            ffmpeg_command=str(fake_ffmpeg),
            ffprobe_command=str(fake_ffprobe),
            run_embedded_worker=False,
            auth_mode="optional",
            auto_repair_enabled=True,
            auto_repair_max_children_per_root=1,
            auto_repair_retryable_issue_codes=["render_failed"],
            delivery_guarantee_enabled=True,
        )
    )


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


def test_completed_eval_task_quality_score_aligns_runtime_learning_profile_and_eval(tmp_path: Path) -> None:
    app_context = _create_app_context(_build_quality_alignment_settings(tmp_path))
    suite_path = tmp_path / "quality_suite.json"
    suite_path.write_text(
        json.dumps(
            {
                "suite_id": "quality-alignment",
                "cases": [{"case_id": "case-1", "prompt": "draw a circle", "tags": ["quality"]}],
            }
        )
    )

    summary = EvaluationService(app_context).run_suite(suite_path=str(suite_path))
    assert summary.total_cases == 1
    assert len(summary.items) == 1

    result = summary.items[0]
    persisted_scorecard = app_context.store.get_task_quality_score(result.task_id)
    assert persisted_scorecard is not None
    expected_score = quality_score_from_scorecard(persisted_scorecard)

    persisted_artifact = app_context.artifact_store.read_quality_score(result.task_id)
    assert persisted_artifact is not None
    assert persisted_artifact["total_score"] == expected_score

    events = app_context.store.list_agent_learning_events("local-anonymous")
    assert len(events) == 1
    assert events[0].task_id == result.task_id
    assert events[0].quality_score == expected_score

    profile_scorecard = app_context.agent_learning_service.build_scorecard("local-anonymous")
    assert profile_scorecard["completed_count"] == 1
    assert profile_scorecard["median_quality_score"] == expected_score

    assert result.quality_score == expected_score
    assert summary.report["quality"]["median_quality_score"] == expected_score


def test_degraded_delivery_counts_as_delivery_but_not_quality_success(tmp_path: Path, monkeypatch) -> None:
    app_module = _load_server_app_module()
    monkeypatch.setattr(app_module, "_build_llm_client", lambda settings: _DegradedSuccessLLMClient(), raising=False)
    app_context = _create_app_context(_build_degraded_quality_alignment_settings(tmp_path))
    suite_path = tmp_path / "quality_suite.json"
    suite_path.write_text(
        json.dumps(
            {
                "suite_id": "quality-alignment",
                "cases": [{"case_id": "case-1", "prompt": "draw a circle", "tags": ["quality"]}],
            }
        )
    )

    summary = EvaluationService(app_context).run_suite(suite_path=str(suite_path))

    result = summary.items[0]
    events = app_context.store.list_agent_learning_events("local-anonymous")
    profile_scorecard = app_context.agent_learning_service.build_scorecard("local-anonymous")

    assert result.status == "completed"
    assert result.delivery_passed is True
    assert result.quality_passed is False
    assert result.quality_score == 0.6
    assert summary.report["success_rate"] == 0.0
    assert summary.report["delivery_rate"] == 1.0
    assert summary.report["quality"]["pass_rate"] == 0.0
    assert app_context.metrics.counters.get("tasks_completed", 0) == 0
    assert app_context.metrics.counters.get("deliveries_completed", 0) == 1
    assert len(events) == 1
    assert events[0].quality_passed is False
    assert profile_scorecard["completed_count"] == 0


def test_profile_auto_apply_threshold_uses_scorecard_derived_median(tmp_path: Path) -> None:
    app = _create_http_api(
        _build_quality_alignment_settings(
            tmp_path,
            auth_mode="required",
            auto_apply_enabled=True,
            auto_apply_min_completed_tasks=1,
            auto_apply_min_quality_score=1.0,
        )
    )
    client = TestClient(app)
    context = app.state.app_context

    context.store.upsert_agent_profile(AgentProfile(agent_id="agent-a", name="Agent A"))
    context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token("agent-a-secret"),
            agent_id="agent-a",
        )
    )
    context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-1",
            agent_id="agent-a",
            source_session_id="sess-1",
            summary_text="Use a steady teaching tone and 1280x720 output.",
            summary_digest="digest-1",
        )
    )
    context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-2",
            agent_id="agent-a",
            source_session_id="sess-2",
            summary_text="Use a steady teaching tone and 1280x720 output.",
            summary_digest="digest-1",
        )
    )

    login = client.post("/api/sessions", json={"agent_token": "agent-a-secret"})
    assert login.status_code == 200
    session_token = login.json()["session_token"]
    headers = {"Authorization": f"Bearer {session_token}"}

    created = client.post("/api/tasks", json={"prompt": "draw a circle"}, headers=headers)
    assert created.status_code == 200
    task_id = created.json()["task_id"]

    processed = context.worker.run_once()
    assert processed == 1

    persisted_scorecard = context.store.get_task_quality_score(task_id)
    assert persisted_scorecard is not None
    expected_score = quality_score_from_scorecard(persisted_scorecard)
    context.settings.agent_learning_auto_apply_min_quality_score = round(expected_score + 0.01, 4)

    first_generate = client.post("/api/profile/suggestions/generate", headers=headers)
    assert first_generate.status_code == 200
    assert first_generate.json()["items"]
    assert all(item["status"] == "pending" for item in first_generate.json()["items"])

    context.settings.agent_learning_auto_apply_min_quality_score = expected_score
    second_generate = client.post("/api/profile/suggestions/generate", headers=headers)
    assert second_generate.status_code == 200
    assert any(item["status"] == "applied" for item in second_generate.json()["items"])

    profile_scorecard = client.get("/api/profile/scorecard", headers=headers)
    assert profile_scorecard.status_code == 200
    assert profile_scorecard.json()["median_quality_score"] == expected_score
