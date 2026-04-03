from pathlib import Path
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


def _create_app_context(settings: Settings):
    def _load():
        from video_agent.server.app import create_app_context

        return create_app_context(settings)

    return _with_temporary_mcp_shim(_load)


def _get_video_thread_tools():
    def _load():
        import video_agent.server.mcp_tools as mcp_tools

        return (
            getattr(mcp_tools, "create_video_thread_tool", None),
            getattr(mcp_tools, "get_video_thread_surface_tool", None),
            getattr(mcp_tools, "request_video_revision_tool", None),
            getattr(mcp_tools, "append_video_turn_tool", None),
            getattr(mcp_tools, "request_video_explanation_tool", None),
            getattr(mcp_tools, "select_video_result_tool", None),
            getattr(mcp_tools, "list_video_thread_participants_tool", None),
            getattr(mcp_tools, "upsert_video_thread_participant_tool", None),
            getattr(mcp_tools, "remove_video_thread_participant_tool", None),
        )

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


def _seed_agent_profile_and_token(app_context, *, agent_id: str, secret: str, scopes_json: dict | None = None):
    app_context.store.upsert_agent_profile(
        AgentProfile(
            agent_id=agent_id,
            name=agent_id,
        )
    )
    app_context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token(secret),
            agent_id=agent_id,
            scopes_json=scopes_json or {},
        )
    )
    return app_context.agent_identity_service.authenticate(secret)


def test_mcp_video_thread_tools_create_surface_and_revision(tmp_path: Path) -> None:
    (
        create_video_thread_tool,
        get_video_thread_surface_tool,
        request_video_revision_tool,
        append_video_turn_tool,
        request_video_explanation_tool,
        select_video_result_tool,
        list_video_thread_participants_tool,
        upsert_video_thread_participant_tool,
        remove_video_thread_participant_tool,
    ) = _get_video_thread_tools()
    assert create_video_thread_tool is not None
    assert get_video_thread_surface_tool is not None
    assert request_video_revision_tool is not None
    assert append_video_turn_tool is not None
    assert request_video_explanation_tool is not None
    assert select_video_result_tool is not None
    assert list_video_thread_participants_tool is not None
    assert upsert_video_thread_participant_tool is not None
    assert remove_video_thread_participant_tool is not None
    app_context = _create_app_context(_build_settings(tmp_path))

    created = create_video_thread_tool(
        app_context,
        {"owner_agent_id": "owner", "title": "Circle explainer", "prompt": "draw a circle"},
    )
    surface = get_video_thread_surface_tool(app_context, {"thread_id": created["thread"]["thread_id"]})
    revised = request_video_revision_tool(
        app_context,
        {
            "thread_id": created["thread"]["thread_id"],
            "iteration_id": created["iteration"]["iteration_id"],
            "summary": "Slow the opener and make the title entrance more deliberate.",
            "preserve_working_parts": True,
        },
    )

    assert surface["thread_header"]["thread_id"] == created["thread"]["thread_id"]
    assert surface["actions"]["items"][0]["action_id"] == "request_revision"
    assert surface["participants"]["items"][0]["role"] == "owner"
    assert revised["thread"]["thread_id"] == created["thread"]["thread_id"]
    assert revised["iteration"]["parent_iteration_id"] == created["iteration"]["iteration_id"]
    assert revised["created_task"]["task_id"]

    appended = append_video_turn_tool(
        app_context,
        {
            "thread_id": created["thread"]["thread_id"],
            "iteration_id": created["iteration"]["iteration_id"],
            "title": "Why this pacing?",
            "summary": "Explain the slower opener.",
        },
    )
    explained = request_video_explanation_tool(
        app_context,
        {
            "thread_id": created["thread"]["thread_id"],
            "iteration_id": created["iteration"]["iteration_id"],
            "summary": "Why did you choose this slower opening?",
        },
    )
    result = app_context.video_iteration_service.register_result(
        thread_id=created["thread"]["thread_id"],
        iteration_id=created["iteration"]["iteration_id"],
        source_task_id=created["created_task"]["task_id"],
        status="ready",
        result_summary="Initial cut with a brisk opener.",
    )
    initial_selected = select_video_result_tool(
        app_context,
        {
            "thread_id": created["thread"]["thread_id"],
            "iteration_id": created["iteration"]["iteration_id"],
            "result_id": result.result_id,
        },
    )
    assert initial_selected["thread"]["selected_result_id"] == result.result_id
    revised = request_video_revision_tool(
        app_context,
        {
            "thread_id": created["thread"]["thread_id"],
            "iteration_id": created["iteration"]["iteration_id"],
            "summary": "Slow the opener and make the title entrance more deliberate.",
            "preserve_working_parts": True,
        },
    )
    revised_result = app_context.video_iteration_service.register_result(
        thread_id=created["thread"]["thread_id"],
        iteration_id=revised["iteration"]["iteration_id"],
        source_task_id=revised["created_task"]["task_id"],
        status="ready",
        result_summary="Selected cut with a slower title entrance.",
    )
    selected = select_video_result_tool(
        app_context,
        {
            "thread_id": created["thread"]["thread_id"],
            "iteration_id": revised["iteration"]["iteration_id"],
            "result_id": revised_result.result_id,
        },
    )
    revised_result.video_resource = f"video-task://{revised['created_task']['task_id']}/artifacts/final.mp4"
    app_context.store.upsert_video_result(revised_result)

    assert appended["turn"]["turn_type"] == "owner_request"
    assert appended["turn"]["intent_type"] == "discuss"
    assert explained["agent_turn"]["turn_type"] == "agent_explanation"
    assert explained["owner_turn"]["intent_type"] == "request_explanation"
    assert explained["agent_turn"]["intent_type"] == "request_explanation"
    assert explained["agent_turn"]["reply_to_turn_id"] == explained["owner_turn"]["turn_id"]
    assert selected["thread"]["selected_result_id"] == revised_result.result_id
    refreshed_surface = get_video_thread_surface_tool(app_context, {"thread_id": created["thread"]["thread_id"]})
    assert refreshed_surface["render_contract"]["sticky_primary_action_id"] == "request_revision"
    assert refreshed_surface["current_focus"]["current_result_author_role"] == "planner"
    assert refreshed_surface["authorship"]["primary_agent_role"] == "planner"
    assert refreshed_surface["decision_notes"]["title"] == "Decision Notes"
    assert refreshed_surface["decision_notes"]["items"][0]["note_kind"] == "selection_rationale"
    assert refreshed_surface["artifact_lineage"]["title"] == "Artifact Lineage"
    assert [item["from_result_id"] for item in refreshed_surface["artifact_lineage"]["items"]] == [
        None,
        result.result_id,
    ]
    assert [item["to_result_id"] for item in refreshed_surface["artifact_lineage"]["items"]] == [
        result.result_id,
        revised_result.result_id,
    ]
    assert refreshed_surface["artifact_lineage"]["items"][1]["status"] == "selected"
    assert refreshed_surface["rationale_snapshots"]["title"] == "Rationale Snapshots"
    assert [item["snapshot_kind"] for item in refreshed_surface["rationale_snapshots"]["items"]] == [
        "agent_explanation",
        "owner_goal",
        "selection_rationale",
    ]
    assert refreshed_surface["production_journal"]["title"] == "Production Journal"
    assert refreshed_surface["production_journal"]["entries"][-1]["entry_kind"] == "result"
    assert any(
        group["status"] == "answered" and group["prompt_intent_type"] == "request_explanation"
        for group in refreshed_surface["discussion_groups"]["groups"]
    )
    assert refreshed_surface["history"]["cards"][0]["intent_type"] == "request_explanation"

    listed = list_video_thread_participants_tool(
        app_context,
        {"thread_id": created["thread"]["thread_id"]},
    )
    assert listed["items"][0]["role"] == "owner"

    upserted = upsert_video_thread_participant_tool(
        app_context,
        {
            "thread_id": created["thread"]["thread_id"],
            "participant_id": "reviewer-1",
            "participant_type": "agent",
            "agent_id": "reviewer-1",
            "role": "reviewer",
            "display_name": "Reviewer",
            "capabilities": ["review_bundle:read"],
        },
    )
    assert upserted["participant"]["participant_id"] == "reviewer-1"

    removed = remove_video_thread_participant_tool(
        app_context,
        {
            "thread_id": created["thread"]["thread_id"],
            "participant_id": "reviewer-1",
        },
    )
    assert removed["removed"] is True


def test_non_owner_cannot_manage_thread_participants_via_mcp_tools(tmp_path: Path) -> None:
    (
        create_video_thread_tool,
        _get_video_thread_surface_tool,
        _request_video_revision_tool,
        _append_video_turn_tool,
        _request_video_explanation_tool,
        _select_video_result_tool,
        list_video_thread_participants_tool,
        upsert_video_thread_participant_tool,
        remove_video_thread_participant_tool,
    ) = _get_video_thread_tools()
    assert callable(create_video_thread_tool)
    assert callable(list_video_thread_participants_tool)
    assert callable(upsert_video_thread_participant_tool)
    assert callable(remove_video_thread_participant_tool)

    app_context = _create_app_context(_build_required_auth_settings(tmp_path))
    owner = _seed_agent_profile_and_token(app_context, agent_id="agent-a", secret="agent-a-secret")
    intruder = _seed_agent_profile_and_token(
        app_context,
        agent_id="agent-b",
        secret="agent-b-secret",
        scopes_json={"allow": ["task:read", "task:mutate"]},
    )

    created = create_video_thread_tool(
        app_context,
        {"owner_agent_id": "agent-a", "title": "Circle explainer", "prompt": "draw a circle"},
        agent_principal=owner,
    )

    listed = list_video_thread_participants_tool(
        app_context,
        {"thread_id": created["thread"]["thread_id"]},
        agent_principal=intruder,
    )
    upserted = upsert_video_thread_participant_tool(
        app_context,
        {
            "thread_id": created["thread"]["thread_id"],
            "participant_id": "reviewer-1",
            "participant_type": "agent",
            "agent_id": "agent-b",
            "role": "reviewer",
            "display_name": "Reviewer",
            "capabilities": ["review_bundle:read"],
        },
        agent_principal=intruder,
    )
    removed = remove_video_thread_participant_tool(
        app_context,
        {
            "thread_id": created["thread"]["thread_id"],
            "participant_id": "owner",
        },
        agent_principal=intruder,
    )

    assert listed["items"][0]["role"] == "owner"
    assert upserted["error"]["code"] == "agent_access_denied"
    assert removed["error"]["code"] == "agent_access_denied"
