import json
from collections.abc import Callable
from pathlib import Path
import sys
import types

from video_agent.application.agent_identity_service import hash_agent_token
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


def create_app_context(settings: Settings):
    def _load():
        from video_agent.server.app import create_app_context as factory

        return factory(settings)

    return _with_temporary_mcp_shim(_load)


def create_video_task_tool(app_context, payload, agent_principal=None):
    def _load():
        from video_agent.server.mcp_tools import create_video_task_tool as tool

        return tool(app_context, payload, agent_principal=agent_principal)

    return _with_temporary_mcp_shim(_load)


def get_video_task_tool(app_context, payload, agent_principal=None):
    def _load():
        from video_agent.server.mcp_tools import get_video_task_tool as tool

        return tool(app_context, payload, agent_principal=agent_principal)

    return _with_temporary_mcp_shim(_load)


def get_failure_contract_tool(app_context, payload, agent_principal=None):
    def _load():
        from video_agent.server.mcp_tools import get_failure_contract_tool as tool

        return tool(app_context, payload, agent_principal=agent_principal)

    return _with_temporary_mcp_shim(_load)


def list_video_tasks_tool(app_context, payload, agent_principal=None):
    def _load():
        from video_agent.server.mcp_tools import list_video_tasks_tool as tool

        return tool(app_context, payload, agent_principal=agent_principal)

    return _with_temporary_mcp_shim(_load)


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


def _seed_agent_memory(app_context, *, memory_id: str, agent_id: str, status: str = "active") -> None:
    app_context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id=memory_id,
            agent_id=agent_id,
            source_session_id=f"session-{agent_id}",
            status=status,
            summary_text=f"Remember {agent_id}",
            summary_digest=f"digest-{memory_id}",
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


def test_create_video_task_persists_selected_memory_ids(temp_settings) -> None:
    app_context = create_app_context(temp_settings)
    _seed_agent_memory(app_context, memory_id="mem-a", agent_id="local-anonymous")

    payload = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle", "session_id": "session-1", "memory_ids": ["mem-a"]},
    )
    task = app_context.store.get_task(payload["task_id"])

    assert task is not None
    assert task.selected_memory_ids == ["mem-a"]


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
