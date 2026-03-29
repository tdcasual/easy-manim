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


def _create_app_context(settings: Settings):
    def _load():
        from video_agent.server.app import create_app_context

        return create_app_context(settings)

    return _with_temporary_mcp_shim(_load)


def _get_mcp_tools():
    def _load():
        from video_agent.server.mcp_tools import (
            apply_review_decision_tool,
            create_video_task_tool,
            get_review_bundle_tool,
        )

        return apply_review_decision_tool, create_video_task_tool, get_review_bundle_tool

    return _with_temporary_mcp_shim(_load)


def _build_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            run_embedded_worker=False,
            multi_agent_workflow_enabled=True,
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
            multi_agent_workflow_enabled=True,
        )
    )


def _seed_agent_profile_and_token(app_context, *, secret: str, scopes_json: dict | None = None):
    app_context.store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A",
        )
    )
    app_context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token(secret),
            agent_id="agent-a",
            scopes_json=scopes_json or {},
        )
    )
    return app_context.agent_identity_service.authenticate(secret)


def test_apply_review_decision_tool_creates_revision_for_revise_decision(tmp_path: Path) -> None:
    apply_review_decision_tool, create_video_task_tool, get_review_bundle_tool = _get_mcp_tools()
    app_context = _create_app_context(_build_settings(tmp_path))
    created = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle", "session_id": "session-1"},
    )
    bundle = get_review_bundle_tool(app_context, {"task_id": created["task_id"]})
    assert bundle["collaboration"]["planner_recommendation"]["role"] == "planner"
    assert bundle["collaboration"]["reviewer_decision"]["role"] == "reviewer"
    assert bundle["collaboration"]["repairer_execution_hint"]["role"] == "repairer"

    payload = apply_review_decision_tool(
        app_context,
        {
            "task_id": created["task_id"],
            "review_decision": {
                "decision": "revise",
                "summary": "Needs one more pass",
                "feedback": "Make the circle blue",
            },
            "session_id": "session-1",
        },
    )

    assert payload["action"] == "revise"
    assert payload["created_task_id"]

    revised = app_context.store.get_task(payload["created_task_id"])
    assert revised is not None
    assert revised.parent_task_id == created["task_id"]


def test_review_workflow_mutations_remain_orchestrator_owned(tmp_path: Path) -> None:
    apply_review_decision_tool, create_video_task_tool, _ = _get_mcp_tools()
    app_context = _create_app_context(_build_required_auth_settings(tmp_path))
    principal = _seed_agent_profile_and_token(
        app_context,
        secret="agent-a-read-secret",
        scopes_json={"allow": ["task:create", "task:read"]},
    )
    created = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle", "session_id": "session-1"},
        agent_principal=principal,
    )

    decision = apply_review_decision_tool(
        app_context,
        {
            "task_id": created["task_id"],
            "review_decision": {
                "decision": "revise",
                "summary": "Needs one more pass",
                "feedback": "Make the circle blue",
            },
            "session_id": "session-1",
        },
        agent_principal=principal,
    )

    assert decision["error"]["code"] == "agent_scope_denied"


def test_review_workflow_tools_require_authenticated_agent_in_required_mode(tmp_path: Path) -> None:
    apply_review_decision_tool, create_video_task_tool, get_review_bundle_tool = _get_mcp_tools()
    app_context = _create_app_context(_build_required_auth_settings(tmp_path))
    principal = _seed_agent_profile_and_token(app_context, secret="agent-a-secret")
    created = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle", "session_id": "session-1"},
        agent_principal=principal,
    )

    bundle = get_review_bundle_tool(app_context, {"task_id": created["task_id"]})
    decision = apply_review_decision_tool(
        app_context,
        {
            "task_id": created["task_id"],
            "review_decision": {
                "decision": "accept",
                "summary": "Looks good",
            },
            "session_id": "session-1",
        },
    )

    assert bundle["error"]["code"] == "agent_not_authenticated"
    assert decision["error"]["code"] == "agent_not_authenticated"


def test_review_workflow_tools_require_task_read_scope(tmp_path: Path) -> None:
    apply_review_decision_tool, create_video_task_tool, get_review_bundle_tool = _get_mcp_tools()
    app_context = _create_app_context(_build_required_auth_settings(tmp_path))
    principal = _seed_agent_profile_and_token(
        app_context,
        secret="agent-a-create-secret",
        scopes_json={"allow": ["task:create"]},
    )
    created = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle", "session_id": "session-1"},
        agent_principal=principal,
    )

    bundle = get_review_bundle_tool(
        app_context,
        {"task_id": created["task_id"]},
        agent_principal=principal,
    )
    decision = apply_review_decision_tool(
        app_context,
        {
            "task_id": created["task_id"],
            "review_decision": {
                "decision": "accept",
                "summary": "Looks good",
            },
            "session_id": "session-1",
        },
        agent_principal=principal,
    )

    assert bundle["error"]["code"] == "agent_scope_denied"
    assert decision["error"]["code"] == "agent_scope_denied"
