import json
from pathlib import Path

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.server.app import create_app_context
from video_agent.server.mcp_tools import (
    create_video_task_tool,
    get_failure_contract_tool,
    get_video_task_tool,
    list_video_tasks_tool,
)


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _build_auto_repair_settings(tmp_path: Path) -> Settings:
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

    return Settings(
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
    )


def _build_required_auth_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return Settings(
        data_dir=data_dir,
        database_path=data_dir / "video_agent.db",
        artifact_root=data_dir / "tasks",
        run_embedded_worker=False,
        auth_mode="required",
    )


def _seed_required_agent(app_context, agent_id: str, secret: str) -> None:
    app_context.store.upsert_agent_profile(AgentProfile(agent_id=agent_id, name=agent_id))
    app_context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token(secret),
            agent_id=agent_id,
        )
    )


def test_create_video_task_tool_returns_task_id(temp_settings) -> None:
    app_context = create_app_context(temp_settings)
    payload = create_video_task_tool(app_context, {"prompt": "draw a circle"})
    assert payload["task_id"]
    assert payload["status"] == "queued"


def test_create_video_task_tool_persists_session_id(temp_settings) -> None:
    app_context = create_app_context(temp_settings)

    payload = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle", "session_id": "session-1"},
    )
    task = app_context.store.get_task(payload["task_id"])

    assert task is not None
    assert task.session_id == "session-1"


def test_get_video_task_tool_returns_snapshot(temp_settings) -> None:
    app_context = create_app_context(temp_settings)
    created = create_video_task_tool(app_context, {"prompt": "draw a circle"})
    snapshot = get_video_task_tool(app_context, {"task_id": created["task_id"]})
    assert snapshot["task_id"] == created["task_id"]


def test_create_video_task_tool_accepts_style_hints(temp_settings) -> None:
    app_context = create_app_context(temp_settings)
    created = create_video_task_tool(
        app_context,
        {
            "prompt": "draw a circle",
            "style_hints": {"tone": "clean", "pace": "steady"},
        },
    )

    task = app_context.store.get_task(created["task_id"])

    assert task is not None
    assert task.style_hints == {"tone": "clean", "pace": "steady"}


def test_get_video_task_tool_returns_auto_repair_summary(tmp_path: Path) -> None:
    app_context = create_app_context(_build_auto_repair_settings(tmp_path))
    created = create_video_task_tool(app_context, {"prompt": "draw a circle"})

    app_context.worker.run_once()
    app_context.worker.run_once()

    snapshot = get_video_task_tool(app_context, {"task_id": created["task_id"]})

    assert snapshot["artifact_summary"]["repair_children"] == 1
    assert snapshot["auto_repair_summary"]["stopped_reason"] == "budget_exhausted"


def test_get_video_task_tool_exposes_failure_contract(tmp_path: Path) -> None:
    app_context = create_app_context(_build_auto_repair_settings(tmp_path))
    created = create_video_task_tool(app_context, {"prompt": "draw a circle"})

    app_context.worker.run_once()

    snapshot = get_video_task_tool(app_context, {"task_id": created["task_id"]})

    assert snapshot["failure_contract"]["retryable"] is True
    assert snapshot["failure_contract"]["recommended_action"] == "auto_repair"


def test_get_failure_contract_tool_returns_failure_contract(tmp_path: Path) -> None:
    app_context = create_app_context(_build_auto_repair_settings(tmp_path))
    created = create_video_task_tool(app_context, {"prompt": "draw a circle"})

    app_context.worker.run_once()

    payload = get_failure_contract_tool(app_context, {"task_id": created["task_id"]})

    assert payload["task_id"] == created["task_id"]
    assert payload["failure_contract"]["retryable"] is True
    assert payload["failure_contract"]["blocking_layer"] == "render"


def test_create_video_task_requires_authenticated_agent_in_required_mode(tmp_path: Path) -> None:
    app_context = create_app_context(_build_required_auth_settings(tmp_path))

    payload = create_video_task_tool(app_context, {"prompt": "draw a circle"})

    assert payload["error"]["code"] == "agent_not_authenticated"


def test_list_video_tasks_only_returns_authenticated_agents_tasks(tmp_path: Path) -> None:
    app_context = create_app_context(_build_required_auth_settings(tmp_path))
    _seed_required_agent(app_context, "agent-a", "agent-a-secret")
    _seed_required_agent(app_context, "agent-b", "agent-b-secret")
    agent_a = app_context.agent_identity_service.authenticate("agent-a-secret")
    agent_b = app_context.agent_identity_service.authenticate("agent-b-secret")

    agent_a_task = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle"},
        agent_principal=agent_a,
    )
    create_video_task_tool(
        app_context,
        {"prompt": "draw a square"},
        agent_principal=agent_b,
    )

    payload = list_video_tasks_tool(app_context, {"limit": 10}, agent_principal=agent_a)

    assert [item["task_id"] for item in payload["items"]] == [agent_a_task["task_id"]]
