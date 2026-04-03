import asyncio
import json
import inspect
import re
import sys
import types
from pathlib import Path
from collections.abc import Callable

from video_agent.config import Settings
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

    class _Context:
        def __init__(self, client_id: str | None = None) -> None:
            self.client_id = client_id
            self.session = object()

    class _ToolInfo:
        def __init__(self, name: str) -> None:
            self.name = name

    class _ResourceContent:
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

    class _FastMCP:
        def __init__(self, **kwargs) -> None:
            self._tools: dict[str, Callable[..., dict[str, object]]] = {}
            self._resources: list[tuple[re.Pattern[str], Callable[..., str | bytes]]] = []
            self._ctx = _Context(client_id=f"shim:{id(self)}")
            self._mcp_server = types.SimpleNamespace(lifespan=kwargs.get("lifespan"))

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
            raise KeyError(uri)

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


def _create_mcp_server(settings: Settings):
    def _load():
        from video_agent.server.fastmcp_server import create_mcp_server

        return create_mcp_server(settings)

    return _with_temporary_mcp_shim(_load)


def _build_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            run_embedded_worker=False,
        )
    )


def test_fastmcp_video_thread_resources_expose_surface_and_timeline(tmp_path: Path) -> None:
    async def run() -> None:
        mcp = _create_mcp_server(_build_settings(tmp_path))
        _, created = await mcp.call_tool(
            "create_video_thread",
            {"owner_agent_id": "owner", "title": "Circle explainer", "prompt": "draw a circle"},
        )
        thread_id = created["thread"]["thread_id"]
        iteration_id = created["iteration"]["iteration_id"]
        await mcp.call_tool(
            "upsert_video_thread_participant",
            {
                "thread_id": thread_id,
                "participant_id": "planner-1",
                "participant_type": "agent",
                "agent_id": "planner-1",
                "role": "planner",
                "display_name": "Planner",
            },
        )

        _, appended = await mcp.call_tool(
            "append_video_turn",
            {
                "thread_id": thread_id,
                "iteration_id": iteration_id,
                "title": "Why this pacing?",
                "summary": "Explain the slower opener.",
                "addressed_participant_id": "planner-1",
                "reply_to_turn_id": "turn-root",
                "related_result_id": "result-0",
            },
        )
        _, explained = await mcp.call_tool(
            "request_video_explanation",
            {
                "thread_id": thread_id,
                "iteration_id": iteration_id,
                "summary": "Why did you choose this slower opening?",
            },
        )

        surface_resource = list(await mcp.read_resource(f"video-thread://{thread_id}/surface.json"))
        timeline_resource = list(await mcp.read_resource(f"video-thread://{thread_id}/timeline.json"))
        iteration_resource = list(
            await mcp.read_resource(f"video-thread://{thread_id}/iterations/{iteration_id}.json")
        )
        surface = json.loads(surface_resource[0].content)
        timeline = json.loads(timeline_resource[0].content)
        iteration = json.loads(iteration_resource[0].content)

        assert surface["thread_header"]["thread_id"] == thread_id
        assert surface["latest_explanation"]["summary"]
        assert surface["authorship"]["primary_agent_role"] == "planner"
        assert surface["decision_notes"]["title"] == "Decision Notes"
        assert surface["decision_notes"]["items"][0]["note_kind"] == "selection_rationale"
        assert surface["artifact_lineage"]["title"] == "Artifact Lineage"
        assert surface["artifact_lineage"]["items"] == []
        assert surface["rationale_snapshots"]["title"] == "Rationale Snapshots"
        assert len(surface["rationale_snapshots"]["items"]) == 1
        assert surface["rationale_snapshots"]["items"][0]["snapshot_kind"] == "agent_explanation"
        assert surface["composer"]["target"]["iteration_id"] == iteration_id
        assert surface["composer"]["target"]["addressed_participant_id"] == "planner-1"
        assert surface["composer"]["target"]["addressed_agent_id"] == "planner-1"
        assert surface["composer"]["target"]["addressed_display_name"] == "Planner"
        assert surface["composer"]["target"]["agent_role"] == "planner"
        assert surface["discussion_runtime"]["title"] == "Discussion Runtime"
        assert surface["discussion_runtime"]["active_iteration_id"] == iteration_id
        assert surface["discussion_runtime"]["active_discussion_group_id"] == (
            surface["discussion_groups"]["groups"][0]["group_id"]
        )
        assert surface["discussion_runtime"]["continuity_scope"] == "iteration"
        assert surface["discussion_runtime"]["reply_policy"] == "continue_thread"
        assert surface["discussion_runtime"]["default_intent_type"] == "discuss"
        assert surface["discussion_runtime"]["default_reply_to_turn_id"] == (
            surface["discussion_groups"]["groups"][0]["prompt_turn_id"]
        )
        assert surface["discussion_runtime"]["default_related_result_id"] is None
        assert surface["discussion_runtime"]["addressed_participant_id"] == "planner-1"
        assert surface["discussion_runtime"]["addressed_agent_id"] == "planner-1"
        assert surface["discussion_runtime"]["addressed_display_name"] == "Planner"
        assert surface["discussion_runtime"]["suggested_follow_up_modes"] == [
            "ask_why",
            "request_change",
            "preserve_direction",
            "branch_revision",
        ]
        assert surface["iteration_detail"]["selected_iteration_id"] == iteration_id
        assert surface["iteration_detail"]["resource_uri"] == (
            f"video-thread://{thread_id}/iterations/{iteration_id}.json"
        )
        assert surface["production_journal"]["title"] == "Production Journal"
        assert surface["production_journal"]["entries"][0]["entry_kind"] == "iteration"
        assert surface["discussion_groups"]["groups"][0]["status"] == "answered"
        assert [item["card_type"] for item in surface["history"]["cards"]] == [
            "agent_explanation",
            "owner_request",
        ]
        assert surface["history"]["cards"][0]["intent_type"] == "request_explanation"
        assert surface["history"]["cards"][0]["reply_to_turn_id"] == explained["owner_turn"]["turn_id"]
        assert surface["render_contract"]["default_focus_panel"] == "latest_explanation"
        assert surface["render_contract"]["sticky_primary_action_emphasis"] == "normal"
        assert any(
            item["panel_id"] == "history" and item["default_open"]
            for item in surface["render_contract"]["panel_presentations"]
        )
        assert timeline["thread_id"] == thread_id
        assert "conversation" in timeline
        assert "process" in timeline
        assert appended["turn"]["turn_type"] == "owner_request"
        assert appended["turn"]["addressed_participant_id"] == "planner-1"
        assert appended["turn"]["addressed_agent_id"] == "planner-1"
        assert appended["turn"]["reply_to_turn_id"] == "turn-root"
        assert appended["turn"]["related_result_id"] == "result-0"
        assert explained["agent_turn"]["turn_type"] == "agent_explanation"
        assert iteration["iteration_id"] == iteration_id
        assert iteration["summary"]
        assert iteration["composer_target"]["iteration_id"] == iteration_id
        assert iteration["composer_target"]["addressed_participant_id"] == "planner-1"
        assert iteration["composer_target"]["addressed_agent_id"] == "planner-1"
        assert iteration["composer_target"]["addressed_display_name"] == "Planner"
        assert iteration["composer_target"]["agent_role"] == "planner"
        assert iteration["execution_summary"]["title"] == "Execution Summary"
        assert iteration["execution_summary"]["summary"] == (
            "Planner has not started a tracked task yet, but the iteration is anchored to this agent."
        )
        assert iteration["execution_summary"]["task_id"] is None
        assert iteration["execution_summary"]["run_id"] is None
        assert iteration["execution_summary"]["status"] == "pending"
        assert iteration["execution_summary"]["phase"] is None
        assert iteration["execution_summary"]["agent_id"] == "planner-1"
        assert iteration["execution_summary"]["agent_display_name"] == "Planner"
        assert iteration["execution_summary"]["agent_role"] == "planner"
        assert iteration["execution_summary"]["result_id"] is None
        assert iteration["execution_summary"]["discussion_group_id"] == (
            f"group-{explained['owner_turn']['turn_id']}"
        )
        assert iteration["execution_summary"]["reply_to_turn_id"] == explained["owner_turn"]["turn_id"]
        assert iteration["execution_summary"]["latest_owner_turn_id"] == explained["owner_turn"]["turn_id"]
        assert iteration["execution_summary"]["latest_agent_turn_id"] == explained["agent_turn"]["turn_id"]
        assert iteration["execution_summary"]["is_active"] is False
        assert any(item["intent_type"] == "discuss" for item in iteration["turns"])
        assert any(
            item["reply_to_turn_id"] == explained["owner_turn"]["turn_id"]
            for item in iteration["turns"]
        )
        assert iteration["runs"] == []
        assert iteration["results"] == []

    asyncio.run(run())
