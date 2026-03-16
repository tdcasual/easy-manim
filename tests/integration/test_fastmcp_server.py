import asyncio
import json
from pathlib import Path

import video_agent.server.fastmcp_server as fastmcp_server_module
from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.server.app import create_app_context
from video_agent.server.fastmcp_server import create_mcp_server



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

    return Settings(
        data_dir=data_dir,
        database_path=data_dir / "video_agent.db",
        artifact_root=data_dir / "tasks",
        manim_command=str(fake_manim),
        ffmpeg_command=str(fake_ffmpeg),
        ffprobe_command=str(fake_ffprobe),
    )


def _seed_agent(settings: Settings) -> None:
    app = create_app_context(settings)
    app.store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A",
            profile_json={"style_hints": {"tone": "teaching"}},
        )
    )
    app.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token("agent-a-secret"),
            agent_id="agent-a",
        )
    )



def test_fastmcp_server_registers_expected_tools(tmp_path: Path) -> None:
    async def run() -> None:
        mcp = create_mcp_server(_build_fake_pipeline_settings(tmp_path))
        tool_names = {tool.name for tool in await mcp.list_tools()}
        assert {
            "authenticate_agent",
            "create_video_task",
            "get_video_task",
            "revise_video_task",
            "get_video_result",
            "cancel_video_task",
        } <= tool_names

    asyncio.run(run())


def test_fastmcp_registers_session_memory_tools(tmp_path: Path) -> None:
    async def run() -> None:
        mcp = create_mcp_server(_build_fake_pipeline_settings(tmp_path))
        tool_names = {tool.name for tool in await mcp.list_tools()}
        assert {
            "get_session_memory",
            "summarize_session_memory",
            "clear_session_memory",
        } <= tool_names

    asyncio.run(run())



def test_fastmcp_tool_and_resource_roundtrip(tmp_path: Path) -> None:
    async def run() -> None:
        mcp = create_mcp_server(_build_fake_pipeline_settings(tmp_path))
        _, created = await mcp.call_tool("create_video_task", {"prompt": "draw a circle"})
        assert created["task_id"]

        _, task = await mcp.call_tool("get_video_task", {"task_id": created["task_id"]})
        assert task["task_id"] == created["task_id"]

        resource = list(await mcp.read_resource(f"video-task://{created['task_id']}/task.json"))
        assert resource
        assert created["task_id"] in resource[0].content

    asyncio.run(run())



def test_fastmcp_server_can_skip_background_worker(tmp_path: Path, monkeypatch) -> None:
    called = False

    async def fake_run_background_worker(context, stop_event):
        nonlocal called
        called = True
        while not stop_event.is_set():
            await asyncio.sleep(0)

    async def run() -> None:
        monkeypatch.setattr(fastmcp_server_module, "_run_background_worker", fake_run_background_worker)
        settings = _build_fake_pipeline_settings(tmp_path)
        settings.run_embedded_worker = False
        mcp = create_mcp_server(settings)

        async with mcp._mcp_server.lifespan(mcp._mcp_server):
            await asyncio.sleep(0)

        assert called is False

    asyncio.run(run())


def test_fastmcp_authenticate_agent_enables_followup_task_creation(tmp_path: Path) -> None:
    async def run() -> None:
        settings = _build_fake_pipeline_settings(tmp_path)
        settings.auth_mode = "required"
        settings.run_embedded_worker = False
        _seed_agent(settings)
        mcp = create_mcp_server(settings)

        _, auth_payload = await mcp.call_tool("authenticate_agent", {"agent_token": "agent-a-secret"})
        assert auth_payload["authenticated"] is True
        assert auth_payload["agent_id"] == "agent-a"

        _, created = await mcp.call_tool("create_video_task", {"prompt": "draw a circle"})
        assert created["task_id"]
        assert created["status"] == "queued"

    asyncio.run(run())


def test_same_agent_sessions_do_not_share_memory(tmp_path: Path) -> None:
    async def run() -> None:
        settings = _build_fake_pipeline_settings(tmp_path)
        settings.auth_mode = "required"
        settings.run_embedded_worker = False
        _seed_agent(settings)

        mcp_a = create_mcp_server(settings)
        mcp_b = create_mcp_server(settings)

        await mcp_a.call_tool("authenticate_agent", {"agent_token": "agent-a-secret"})
        await mcp_b.call_tool("authenticate_agent", {"agent_token": "agent-a-secret"})
        await mcp_a.call_tool("create_video_task", {"prompt": "draw a circle"})

        _, memory_a = await mcp_a.call_tool("get_session_memory", {})
        _, memory_b = await mcp_b.call_tool("get_session_memory", {})

        assert memory_a["entry_count"] == 1
        assert memory_b["entry_count"] == 0

    asyncio.run(run())
