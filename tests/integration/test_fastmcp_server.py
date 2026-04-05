import asyncio
import inspect
import json
from pathlib import Path
import re
import sys
import types
from collections.abc import Callable

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
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
        def __init__(self, client_id: str | None = None) -> None:
            self.client_id = client_id
            self.session = object()

    class _ToolInfo:  # pragma: no cover - test import shim
        def __init__(self, name: str) -> None:
            self.name = name

    class _ResourceContent:  # pragma: no cover - test import shim
        def __init__(self, content: str | bytes) -> None:
            self.content = content

    def _compile_resource_pattern(template: str) -> re.Pattern[str]:
        parts: list[str] = []
        cursor = 0
        for match in re.finditer(r"{([^}]+)}", template):
            parts.append(re.escape(template[cursor : match.start()]))
            parts.append(f"(?P<{match.group(1)}>[^/]+)")
            cursor = match.end()
        parts.append(re.escape(template[cursor:]))
        return re.compile(f"^{''.join(parts)}$")

    class _FastMCP:  # pragma: no cover - test import shim
        def __init__(self, **kwargs) -> None:
            self._tools: dict[str, Callable[..., dict[str, object]]] = {}
            self._resources: list[tuple[re.Pattern[str], Callable[..., str | bytes]]] = []
            self._ctx = _Context(client_id=f"shim:{id(self)}")
            self._mcp_server = types.SimpleNamespace(
                lifespan=kwargs.get("lifespan"),
            )

        def tool(self, name: str):
            def decorator(fn):
                self._tools[name] = fn
                return fn

            return decorator

        def resource(self, template: str, mime_type: str | None = None):
            _ = mime_type

            def decorator(fn):
                self._resources.append((_compile_resource_pattern(template), fn))
                return fn

            return decorator

        async def list_tools(self):
            return [_ToolInfo(name) for name in self._tools]

        async def call_tool(self, name: str, payload: dict[str, object]):
            fn = self._tools[name]
            kwargs = dict(payload)
            if "ctx" in inspect.signature(fn).parameters and "ctx" not in kwargs:
                kwargs["ctx"] = self._ctx
            return None, fn(**kwargs)

        async def read_resource(self, uri: str):
            for pattern, fn in self._resources:
                match = pattern.match(uri)
                if match is None:
                    continue
                kwargs = dict(match.groupdict())
                if "ctx" in inspect.signature(fn).parameters and "ctx" not in kwargs:
                    kwargs["ctx"] = self._ctx
                return [_ResourceContent(fn(**kwargs))]
            raise KeyError(f"Unknown resource URI: {uri}")

    mcp_fastmcp_module.Context = _Context
    mcp_fastmcp_module.FastMCP = _FastMCP
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


def _load_fastmcp_server():
    def _load():
        import video_agent.server.fastmcp_server as fastmcp_server_module

        return fastmcp_server_module, fastmcp_server_module.create_mcp_server

    return _with_temporary_mcp_shim(_load)


def _load_fastmcp_registration_modules():
    def _load():
        from mcp.server.fastmcp import FastMCP
        from video_agent.server.fastmcp_server_memory_registration import register_memory_tools
        from video_agent.server.fastmcp_server_resource_registration import register_resources
        from video_agent.server.fastmcp_server_task_registration import register_task_tools
        from video_agent.server.fastmcp_server_thread_registration import register_thread_tools

        return (
            FastMCP,
            register_memory_tools,
            register_resources,
            register_task_tools,
            register_thread_tools,
        )

    return _with_temporary_mcp_shim(_load)


def _create_mcp_server(settings: Settings):
    _, create_mcp_server = _load_fastmcp_server()
    return create_mcp_server(settings)


def _create_app_context(settings: Settings):
    def _load():
        from video_agent.server.app import create_app_context

        return create_app_context(settings)

    return _with_temporary_mcp_shim(_load)


def _session_key_for_ctx(ctx) -> str:
    return f"session:{getattr(ctx, 'client_id', 'unknown')}"


def _current_principal(app_context, ctx):
    if ctx is None:
        return None
    return app_context.session_auth.get(_session_key_for_ctx(ctx))


def _current_session_id(app_context, ctx):
    if ctx is None:
        return None
    principal = _current_principal(app_context, ctx)
    handle = app_context.session_memory_registry.ensure_session(
        _session_key_for_ctx(ctx),
        agent_id=None if principal is None else principal.agent_id,
    )
    return handle.session_id



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
        )
    )


def _seed_agent(settings: Settings) -> None:
    app = _create_app_context(settings)
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
        mcp = _create_mcp_server(_build_fake_pipeline_settings(tmp_path))
        tool_names = {tool.name for tool in await mcp.list_tools()}
        assert {
            "authenticate_agent",
            "create_video_task",
            "get_video_task",
            "get_review_bundle",
            "apply_review_decision",
            "revise_video_task",
            "get_video_result",
            "cancel_video_task",
        } <= tool_names

    asyncio.run(run())


def test_fastmcp_registers_session_memory_tools(tmp_path: Path) -> None:
    async def run() -> None:
        mcp = _create_mcp_server(_build_fake_pipeline_settings(tmp_path))
        tool_names = {tool.name for tool in await mcp.list_tools()}
        assert {
            "get_session_memory",
            "summarize_session_memory",
            "clear_session_memory",
        } <= tool_names

    asyncio.run(run())


def test_fastmcp_registers_persistent_memory_tools(tmp_path: Path) -> None:
    async def run() -> None:
        mcp = _create_mcp_server(_build_fake_pipeline_settings(tmp_path))
        tool_names = {tool.name for tool in await mcp.list_tools()}
        assert {
            "promote_session_memory",
            "list_agent_memories",
            "get_agent_memory",
            "disable_agent_memory",
            "query_agent_memories",
        } <= tool_names

    asyncio.run(run())


def test_fastmcp_registration_modules_register_expected_tool_names(tmp_path: Path) -> None:
    async def run() -> None:
        FastMCP, register_memory_tools, _, register_task_tools, register_thread_tools = (
            _load_fastmcp_registration_modules()
        )
        settings = _build_fake_pipeline_settings(tmp_path)
        app_context = _create_app_context(settings)
        mcp = FastMCP(name="registration-test")

        register_memory_tools(
            mcp=mcp,
            context=app_context,
            current_principal=lambda ctx: _current_principal(app_context, ctx),
            current_session_id=lambda ctx: _current_session_id(app_context, ctx),
            session_key_for_ctx=_session_key_for_ctx,
        )
        register_task_tools(
            mcp=mcp,
            context=app_context,
            current_principal=lambda ctx: _current_principal(app_context, ctx),
            current_session_id=lambda ctx: _current_session_id(app_context, ctx),
        )
        register_thread_tools(
            mcp=mcp,
            context=app_context,
            current_principal=lambda ctx: _current_principal(app_context, ctx),
            current_session_id=lambda ctx: _current_session_id(app_context, ctx),
        )

        tool_names = {tool.name for tool in await mcp.list_tools()}
        assert {
            "authenticate_agent",
            "create_video_task",
            "get_video_task",
            "append_video_turn",
            "get_session_memory",
            "query_agent_memories",
        } <= tool_names

    asyncio.run(run())


def test_fastmcp_resource_registration_module_preserves_resource_templates(tmp_path: Path) -> None:
    async def run() -> None:
        FastMCP, _, register_resources, _, _ = _load_fastmcp_registration_modules()
        settings = _build_fake_pipeline_settings(tmp_path)
        app_context = _create_app_context(settings)
        mcp = FastMCP(name="resource-registration-test")

        register_resources(
            mcp=mcp,
            context=app_context,
            current_principal=lambda ctx: _current_principal(app_context, ctx),
        )

        created = app_context.task_service.create_video_task(prompt="draw a circle", session_id="session-1")
        thread = app_context.video_thread_service.create_thread(
            owner_agent_id="local-anonymous",
            title="Draw a circle",
            prompt="draw a circle",
            session_id="session-1",
        )

        task_resource = list(await mcp.read_resource(f"video-task://{created.task_id}/task.json"))
        thread_resource = list(await mcp.read_resource(f"video-thread://{thread.thread.thread_id}/surface.json"))

        assert created.task_id in task_resource[0].content
        assert thread.thread.thread_id in thread_resource[0].content

    asyncio.run(run())


def test_fastmcp_registration_modules_preserve_auth_and_session_context(tmp_path: Path) -> None:
    async def run() -> None:
        FastMCP, register_memory_tools, _, register_task_tools, _ = _load_fastmcp_registration_modules()
        settings = _build_fake_pipeline_settings(tmp_path)
        settings.auth_mode = "required"
        settings.run_embedded_worker = False
        _seed_agent(settings)
        app_context = _create_app_context(settings)
        mcp = FastMCP(name="auth-session-test")

        register_memory_tools(
            mcp=mcp,
            context=app_context,
            current_principal=lambda ctx: _current_principal(app_context, ctx),
            current_session_id=lambda ctx: _current_session_id(app_context, ctx),
            session_key_for_ctx=_session_key_for_ctx,
        )
        register_task_tools(
            mcp=mcp,
            context=app_context,
            current_principal=lambda ctx: _current_principal(app_context, ctx),
            current_session_id=lambda ctx: _current_session_id(app_context, ctx),
        )

        _, auth_payload = await mcp.call_tool("authenticate_agent", {"agent_token": "agent-a-secret"})
        _, created = await mcp.call_tool("create_video_task", {"prompt": "draw a circle"})
        _, session_memory = await mcp.call_tool("get_session_memory", {})

        task = app_context.store.get_task(created["task_id"])

        assert auth_payload["authenticated"] is True
        assert task is not None
        assert task.agent_id == "agent-a"
        assert task.session_id
        assert session_memory["entry_count"] == 1

    asyncio.run(run())



def test_fastmcp_tool_and_resource_roundtrip(tmp_path: Path) -> None:
    async def run() -> None:
        mcp = _create_mcp_server(_build_fake_pipeline_settings(tmp_path))
        _, created = await mcp.call_tool("create_video_task", {"prompt": "draw a circle"})
        assert created["task_id"]

        _, task = await mcp.call_tool("get_video_task", {"task_id": created["task_id"]})
        assert task["task_id"] == created["task_id"]

        resource = list(await mcp.read_resource(f"video-task://{created['task_id']}/task.json"))
        assert resource
        assert created["task_id"] in resource[0].content

    asyncio.run(run())


def test_fastmcp_no_longer_exposes_legacy_video_discussion_thread_resource(tmp_path: Path) -> None:
    async def run() -> None:
        settings = _build_fake_pipeline_settings(tmp_path)
        app = _create_app_context(settings)
        created = app.task_service.create_video_task(prompt="draw a circle", session_id="session-1")
        mcp = _create_mcp_server(settings)
        try:
            await mcp.read_resource(f"video-discussion://{created.task_id}/thread.json")
        except (KeyError, ValueError) as exc:
            assert "video-discussion://" in str(exc)
        else:  # pragma: no cover - regression guard
            raise AssertionError("legacy video-discussion resource should not be registered")

    asyncio.run(run())


def test_fastmcp_server_can_skip_background_worker(tmp_path: Path, monkeypatch) -> None:
    called = False

    async def fake_run_background_worker(context, stop_event):
        nonlocal called
        called = True
        while not stop_event.is_set():
            await asyncio.sleep(0)

    async def run() -> None:
        fastmcp_server_module, _ = _load_fastmcp_server()
        monkeypatch.setattr(fastmcp_server_module, "_run_background_worker", fake_run_background_worker)
        settings = _build_fake_pipeline_settings(tmp_path)
        settings.run_embedded_worker = False
        mcp = _create_mcp_server(settings)

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
        mcp = _create_mcp_server(settings)

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

        mcp_a = _create_mcp_server(settings)
        mcp_b = _create_mcp_server(settings)

        await mcp_a.call_tool("authenticate_agent", {"agent_token": "agent-a-secret"})
        await mcp_b.call_tool("authenticate_agent", {"agent_token": "agent-a-secret"})
        await mcp_a.call_tool("create_video_task", {"prompt": "draw a circle"})

        _, memory_a = await mcp_a.call_tool("get_session_memory", {})
        _, memory_b = await mcp_b.call_tool("get_session_memory", {})

        assert memory_a["entry_count"] == 1
        assert memory_b["entry_count"] == 0

    asyncio.run(run())
