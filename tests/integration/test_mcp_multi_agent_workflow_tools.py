from pathlib import Path
import sys
import types
from collections.abc import Callable

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.domain.review_workflow_models import WorkflowParticipant
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
            revise_video_task_tool,
        )

        return (
            apply_review_decision_tool,
            create_video_task_tool,
            get_review_bundle_tool,
            revise_video_task_tool,
        )

    return _with_temporary_mcp_shim(_load)


def _get_workflow_participant_tools():
    def _load():
        import video_agent.server.mcp_tools as mcp_tools

        return (
            getattr(mcp_tools, "list_workflow_participants_tool", None),
            getattr(mcp_tools, "upsert_workflow_participant_tool", None),
            getattr(mcp_tools, "remove_workflow_participant_tool", None),
        )

    return _with_temporary_mcp_shim(_load)


def _get_workflow_memory_tools():
    def _load():
        import video_agent.server.mcp_tools as mcp_tools

        return (
            getattr(mcp_tools, "list_workflow_memory_recommendations_tool", None),
            getattr(mcp_tools, "pin_workflow_memory_tool", None),
            getattr(mcp_tools, "unpin_workflow_memory_tool", None),
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


def _seed_agent_profile_and_token(
    app_context,
    *,
    agent_id: str = "agent-a",
    secret: str,
    scopes_json: dict | None = None,
):
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


def _seed_workflow_participant(
    app_context,
    *,
    root_task_id: str,
    agent_id: str,
    role: str = "reviewer",
    capabilities: list[str] | None = None,
) -> None:
    app_context.store.upsert_workflow_participant(
        WorkflowParticipant(
            root_task_id=root_task_id,
            agent_id=agent_id,
            role=role,
            capabilities=capabilities or ["review_bundle:read", "review_decision:write"],
        )
    )


def _seed_memory(
    app_context,
    *,
    memory_id: str,
    agent_id: str,
    summary_text: str,
) -> None:
    app_context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id=memory_id,
            agent_id=agent_id,
            source_session_id=f"session-{agent_id}",
            summary_text=summary_text,
            summary_digest=f"digest-{memory_id}",
        )
    )


def test_apply_review_decision_tool_creates_revision_for_revise_decision(tmp_path: Path) -> None:
    apply_review_decision_tool, create_video_task_tool, get_review_bundle_tool, _ = _get_mcp_tools()
    app_context = _create_app_context(_build_settings(tmp_path))
    created = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle", "session_id": "session-1"},
    )
    bundle = get_review_bundle_tool(app_context, {"task_id": created["task_id"]})
    assert bundle["collaboration"]["planner_recommendation"]["role"] == "planner"
    assert bundle["collaboration"]["reviewer_decision"]["role"] == "reviewer"
    assert bundle["collaboration"]["repairer_execution_hint"]["role"] == "repairer"
    assert bundle["branch_scoreboard"][0]["task_id"] == created["task_id"]
    assert bundle["arbitration_summary"]["recommended_task_id"] == created["task_id"]
    assert bundle["arbitration_summary"]["recommended_action"] == "wait_for_completion"

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
    assert payload["reason"] == "revision_created"
    assert payload["refresh_scope"] == "navigate"
    assert payload["refresh_task_id"] == payload["created_task_id"]

    revised = app_context.store.get_task(payload["created_task_id"])
    assert revised is not None
    assert revised.parent_task_id == created["task_id"]


def test_apply_review_decision_tool_accept_returns_task_and_panel_refresh_scope(tmp_path: Path) -> None:
    apply_review_decision_tool, create_video_task_tool, _, _ = _get_mcp_tools()
    app_context = _create_app_context(_build_settings(tmp_path))
    created = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle", "session_id": "session-1"},
    )
    task = app_context.store.get_task(created["task_id"])
    assert task is not None
    task.status = TaskStatus.COMPLETED
    task.phase = TaskPhase.COMPLETED
    task.delivery_status = "delivered"
    task.resolved_task_id = task.task_id
    app_context.store.update_task(task)

    payload = apply_review_decision_tool(
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

    assert payload["action"] == "accept"
    assert payload["created_task_id"] is None
    assert payload["reason"] == "winner_selected"
    assert payload["refresh_scope"] == "task_and_panel"
    assert payload["refresh_task_id"] == created["task_id"]


def test_apply_review_decision_tool_accepts_collaboration_only_repair_hint(tmp_path: Path) -> None:
    apply_review_decision_tool, create_video_task_tool, _, _ = _get_mcp_tools()
    app_context = _create_app_context(_build_settings(tmp_path))
    created = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle", "session_id": "session-1"},
    )

    payload = apply_review_decision_tool(
        app_context,
        {
            "task_id": created["task_id"],
            "review_decision": {
                "decision": "revise",
                "summary": "Needs one more pass",
                "collaboration": {
                    "planner_recommendation": {
                        "role": "planner",
                        "summary": "choose targeted repair",
                    },
                    "reviewer_decision": {
                        "role": "reviewer",
                        "decision": "revise",
                        "summary": "revise with minimal patch",
                    },
                    "repairer_execution_hint": {
                        "role": "repairer",
                        "execution_hint": "Make the circle blue",
                    },
                },
            },
            "session_id": "session-1",
        },
    )

    assert payload["action"] == "revise"
    assert payload["created_task_id"]
    assert payload["reason"] == "revision_created"


def test_apply_review_decision_tool_can_pin_workflow_memory_for_owner(tmp_path: Path) -> None:
    apply_review_decision_tool, create_video_task_tool, _, _ = _get_mcp_tools()
    app_context = _create_app_context(_build_required_auth_settings(tmp_path))
    owner = _seed_agent_profile_and_token(app_context, agent_id="agent-a", secret="agent-a-secret")
    _seed_memory(
        app_context,
        memory_id="mem-a",
        agent_id="agent-a",
        summary_text="Prefer high-contrast diagrams with concise labels.",
    )
    created = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle", "session_id": "session-1"},
        agent_principal=owner,
    )

    payload = apply_review_decision_tool(
        app_context,
        {
            "task_id": created["task_id"],
            "review_decision": {
                "decision": "revise",
                "summary": "Needs one more pass",
                "feedback": "Make the circle blue",
            },
            "pin_workflow_memory_ids": ["mem-a"],
            "session_id": "session-1",
        },
        agent_principal=owner,
    )

    assert payload["action"] == "revise"
    assert payload["workflow_memory_state"]["pinned_memory_ids"] == ["mem-a"]
    revised = app_context.store.get_task(payload["created_task_id"])
    root_task = app_context.store.get_task(created["task_id"])
    assert revised is not None
    assert revised.selected_memory_ids == ["mem-a"]
    assert root_task is not None
    assert root_task.selected_memory_ids == ["mem-a"]


def test_apply_review_decision_tool_denies_collaborator_workflow_memory_mutation(tmp_path: Path) -> None:
    apply_review_decision_tool, create_video_task_tool, _, _ = _get_mcp_tools()
    app_context = _create_app_context(_build_required_auth_settings(tmp_path))
    owner = _seed_agent_profile_and_token(app_context, agent_id="agent-a", secret="agent-a-secret")
    reviewer = _seed_agent_profile_and_token(
        app_context,
        agent_id="agent-b",
        secret="agent-b-secret",
        scopes_json={"allow": ["task:read"]},
    )
    _seed_memory(
        app_context,
        memory_id="mem-a",
        agent_id="agent-a",
        summary_text="Prefer high-contrast diagrams with concise labels.",
    )
    created = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle", "session_id": "session-1"},
        agent_principal=owner,
    )
    _seed_workflow_participant(
        app_context,
        root_task_id=created["task_id"],
        agent_id="agent-b",
    )

    payload = apply_review_decision_tool(
        app_context,
        {
            "task_id": created["task_id"],
            "review_decision": {
                "decision": "revise",
                "summary": "Needs one more pass",
                "feedback": "Make the circle blue",
            },
            "pin_workflow_memory_ids": ["mem-a"],
            "session_id": "session-1",
        },
        agent_principal=reviewer,
    )

    assert payload["error"]["code"] == "agent_access_denied"


def test_review_workflow_mutations_remain_orchestrator_owned(tmp_path: Path) -> None:
    apply_review_decision_tool, create_video_task_tool, _, _ = _get_mcp_tools()
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
    apply_review_decision_tool, create_video_task_tool, get_review_bundle_tool, _ = _get_mcp_tools()
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
    apply_review_decision_tool, create_video_task_tool, get_review_bundle_tool, _ = _get_mcp_tools()
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


def test_apply_review_decision_tool_returns_acceptance_blocked_reason(tmp_path: Path) -> None:
    apply_review_decision_tool, create_video_task_tool, _, _ = _get_mcp_tools()
    app_context = _create_app_context(_build_settings(tmp_path))
    created = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle", "session_id": "session-1"},
    )

    payload = apply_review_decision_tool(
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

    assert payload["action"] == "escalate"
    assert payload["reason"] == "acceptance_blocked"


def test_review_workflow_participant_can_review_but_not_mutate_directly(tmp_path: Path) -> None:
    (
        apply_review_decision_tool,
        create_video_task_tool,
        get_review_bundle_tool,
        revise_video_task_tool,
    ) = _get_mcp_tools()
    app_context = _create_app_context(_build_required_auth_settings(tmp_path))
    owner = _seed_agent_profile_and_token(app_context, agent_id="agent-a", secret="agent-a-secret")
    reviewer = _seed_agent_profile_and_token(
        app_context,
        agent_id="agent-b",
        secret="agent-b-secret",
        scopes_json={"allow": ["task:read"]},
    )
    created = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle", "session_id": "session-1"},
        agent_principal=owner,
    )
    _seed_workflow_participant(
        app_context,
        root_task_id=created["task_id"],
        agent_id="agent-b",
    )

    bundle = get_review_bundle_tool(
        app_context,
        {"task_id": created["task_id"]},
        agent_principal=reviewer,
    )
    decision = apply_review_decision_tool(
        app_context,
        {
            "task_id": created["task_id"],
            "review_decision": {
                "decision": "revise",
                "summary": "Needs more emphasis",
                "feedback": "Make the circle blue",
            },
            "session_id": "session-1",
        },
        agent_principal=reviewer,
    )
    direct_revise = revise_video_task_tool(
        app_context,
        {
            "base_task_id": created["task_id"],
            "feedback": "Bypass workflow controls",
            "session_id": "session-1",
        },
        agent_principal=reviewer,
    )

    assert bundle["task_id"] == created["task_id"]
    assert decision["action"] == "revise"
    assert decision["created_task_id"]
    revised = app_context.store.get_task(decision["created_task_id"])
    assert revised is not None
    assert revised.agent_id == "agent-a"
    assert direct_revise["error"]["code"] == "agent_scope_denied"


def test_mcp_tools_no_longer_expose_legacy_discussion_message_tool(tmp_path: Path) -> None:
    _ = tmp_path
    import video_agent.server.mcp_tools as mcp_tools

    assert not hasattr(mcp_tools, "create_discussion_message_tool")


def test_get_review_bundle_tool_omits_legacy_video_discussion_surface(tmp_path: Path) -> None:
    _, create_video_task_tool, get_review_bundle_tool, _ = _get_mcp_tools()
    app_context = _create_app_context(_build_settings(tmp_path))
    created = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle", "session_id": "session-1"},
    )
    bundle = get_review_bundle_tool(app_context, {"task_id": created["task_id"]})

    assert bundle["task_id"] == created["task_id"]
    assert "video_discussion_surface" not in bundle


def test_owner_can_manage_workflow_participants_via_mcp_tools(tmp_path: Path) -> None:
    list_workflow_participants_tool, upsert_workflow_participant_tool, remove_workflow_participant_tool = (
        _get_workflow_participant_tools()
    )
    assert callable(list_workflow_participants_tool)
    assert callable(upsert_workflow_participant_tool)
    assert callable(remove_workflow_participant_tool)

    _, create_video_task_tool, _, _ = _get_mcp_tools()
    app_context = _create_app_context(_build_required_auth_settings(tmp_path))
    owner = _seed_agent_profile_and_token(app_context, agent_id="agent-a", secret="agent-a-secret")
    _seed_agent_profile_and_token(app_context, agent_id="agent-b", secret="agent-b-secret")
    created = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle", "session_id": "session-1"},
        agent_principal=owner,
    )

    upserted = upsert_workflow_participant_tool(
        app_context,
        {
            "task_id": created["task_id"],
            "agent_id": "agent-b",
            "role": "reviewer",
            "capabilities": ["review_bundle:read"],
        },
        agent_principal=owner,
    )
    listed = list_workflow_participants_tool(
        app_context,
        {"task_id": created["task_id"]},
        agent_principal=owner,
    )
    removed = remove_workflow_participant_tool(
        app_context,
        {"task_id": created["task_id"], "agent_id": "agent-b"},
        agent_principal=owner,
    )

    assert upserted["participant"]["agent_id"] == "agent-b"
    assert upserted["participant"]["role"] == "reviewer"
    assert upserted["participant"]["capabilities"] == ["review_bundle:read"]
    assert listed["items"][0]["agent_id"] == "agent-b"
    assert listed["items"][0]["capabilities"] == ["review_bundle:read"]
    assert removed == {
        "task_id": created["task_id"],
        "root_task_id": created["task_id"],
        "agent_id": "agent-b",
        "removed": True,
    }
    events = app_context.task_service.get_task_events(created["task_id"])
    participant_events = [event for event in events if event["event_type"].startswith("workflow_participant_")]
    assert [event["event_type"] for event in participant_events] == [
        "workflow_participant_upserted",
        "workflow_participant_removed",
    ]
    assert participant_events[0]["payload"] == {
        "root_task_id": created["task_id"],
        "agent_id": "agent-b",
        "role": "reviewer",
        "capabilities": ["review_bundle:read"],
    }
    assert participant_events[1]["payload"] == {
        "root_task_id": created["task_id"],
        "agent_id": "agent-b",
        "removed": True,
    }


def test_non_owner_cannot_manage_workflow_participants_via_mcp_tools(tmp_path: Path) -> None:
    list_workflow_participants_tool, upsert_workflow_participant_tool, remove_workflow_participant_tool = (
        _get_workflow_participant_tools()
    )
    assert callable(list_workflow_participants_tool)
    assert callable(upsert_workflow_participant_tool)
    assert callable(remove_workflow_participant_tool)

    _, create_video_task_tool, _, _ = _get_mcp_tools()
    app_context = _create_app_context(_build_required_auth_settings(tmp_path))
    owner = _seed_agent_profile_and_token(app_context, agent_id="agent-a", secret="agent-a-secret")
    intruder = _seed_agent_profile_and_token(
        app_context,
        agent_id="agent-b",
        secret="agent-b-secret",
        scopes_json={"allow": ["task:read", "task:mutate"]},
    )
    created = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle", "session_id": "session-1"},
        agent_principal=owner,
    )

    listed = list_workflow_participants_tool(
        app_context,
        {"task_id": created["task_id"]},
        agent_principal=intruder,
    )
    upserted = upsert_workflow_participant_tool(
        app_context,
        {
            "task_id": created["task_id"],
            "agent_id": "agent-b",
            "role": "reviewer",
        },
        agent_principal=intruder,
    )
    removed = remove_workflow_participant_tool(
        app_context,
        {"task_id": created["task_id"], "agent_id": "agent-b"},
        agent_principal=intruder,
    )

    assert listed["error"]["code"] == "agent_access_denied"
    assert upserted["error"]["code"] == "agent_access_denied"
    assert removed["error"]["code"] == "agent_access_denied"


def test_owner_can_manage_workflow_memory_via_mcp_tools(tmp_path: Path) -> None:
    list_workflow_memory_recommendations_tool, pin_workflow_memory_tool, unpin_workflow_memory_tool = (
        _get_workflow_memory_tools()
    )
    assert callable(list_workflow_memory_recommendations_tool)
    assert callable(pin_workflow_memory_tool)
    assert callable(unpin_workflow_memory_tool)

    _, create_video_task_tool, _, _ = _get_mcp_tools()
    app_context = _create_app_context(_build_required_auth_settings(tmp_path))
    owner = _seed_agent_profile_and_token(app_context, agent_id="agent-a", secret="agent-a-secret")
    _seed_memory(
        app_context,
        memory_id="mem-a",
        agent_id="agent-a",
        summary_text="Prefer high-contrast diagrams with concise labels.",
    )
    created = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle with contrast", "session_id": "session-1"},
        agent_principal=owner,
    )

    recommendations = list_workflow_memory_recommendations_tool(
        app_context,
        {"task_id": created["task_id"]},
        agent_principal=owner,
    )
    pinned = pin_workflow_memory_tool(
        app_context,
        {"task_id": created["task_id"], "memory_id": "mem-a"},
        agent_principal=owner,
    )
    unpinned = unpin_workflow_memory_tool(
        app_context,
        {"task_id": created["task_id"], "memory_id": "mem-a"},
        agent_principal=owner,
    )

    assert recommendations["root_task_id"] == created["task_id"]
    assert recommendations["items"][0]["memory_id"] == "mem-a"
    assert recommendations["items"][0]["pinned"] is False
    assert pinned["memory_id"] == "mem-a"
    assert pinned["pinned_memory_ids"] == ["mem-a"]
    assert "high-contrast diagrams" in (pinned["persistent_memory_context_summary"] or "")
    assert pinned["task_memory_context"]["persistent"]["memory_ids"] == ["mem-a"]
    assert unpinned["memory_id"] == "mem-a"
    assert unpinned["pinned_memory_ids"] == []
    assert unpinned["task_memory_context"]["persistent"]["memory_ids"] == []


def test_non_owner_cannot_manage_workflow_memory_via_mcp_tools(tmp_path: Path) -> None:
    list_workflow_memory_recommendations_tool, pin_workflow_memory_tool, unpin_workflow_memory_tool = (
        _get_workflow_memory_tools()
    )
    assert callable(list_workflow_memory_recommendations_tool)
    assert callable(pin_workflow_memory_tool)
    assert callable(unpin_workflow_memory_tool)

    _, create_video_task_tool, _, _ = _get_mcp_tools()
    app_context = _create_app_context(_build_required_auth_settings(tmp_path))
    owner = _seed_agent_profile_and_token(app_context, agent_id="agent-a", secret="agent-a-secret")
    intruder = _seed_agent_profile_and_token(
        app_context,
        agent_id="agent-b",
        secret="agent-b-secret",
        scopes_json={"allow": ["task:read", "task:mutate"]},
    )
    _seed_memory(
        app_context,
        memory_id="mem-a",
        agent_id="agent-a",
        summary_text="Prefer high-contrast diagrams with concise labels.",
    )
    created = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle with contrast", "session_id": "session-1"},
        agent_principal=owner,
    )

    recommendations = list_workflow_memory_recommendations_tool(
        app_context,
        {"task_id": created["task_id"]},
        agent_principal=intruder,
    )
    pinned = pin_workflow_memory_tool(
        app_context,
        {"task_id": created["task_id"], "memory_id": "mem-a"},
        agent_principal=intruder,
    )
    unpinned = unpin_workflow_memory_tool(
        app_context,
        {"task_id": created["task_id"], "memory_id": "mem-a"},
        agent_principal=intruder,
    )

    assert recommendations["error"]["code"] == "agent_access_denied"
    assert pinned["error"]["code"] == "agent_access_denied"
    assert unpinned["error"]["code"] == "agent_access_denied"


def test_get_review_bundle_tool_exposes_owner_review_panel_contract(tmp_path: Path) -> None:
    _, create_video_task_tool, get_review_bundle_tool, _ = _get_mcp_tools()
    app_context = _create_app_context(_build_required_auth_settings(tmp_path))
    owner = _seed_agent_profile_and_token(app_context, agent_id="agent-a", secret="agent-a-secret")
    _seed_memory(
        app_context,
        memory_id="mem-a",
        agent_id="agent-a",
        summary_text="Prefer high-contrast diagrams with concise labels.",
    )
    created = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle with contrast", "session_id": "session-1"},
        agent_principal=owner,
    )
    app_context.workflow_collaboration_service.pin_workflow_memory(
        created["task_id"],
        memory_id="mem-a",
        agent_principal=owner,
    )

    bundle = get_review_bundle_tool(
        app_context,
        {"task_id": created["task_id"]},
        agent_principal=owner,
    )

    controls = bundle["workflow_review_controls"]
    assert controls["panel_header"]["tone"] == controls["render_contract"]["panel_tone"]
    assert controls["render_contract"]["display_priority"] == "high"
    assert controls["render_contract"]["badge_order"] == ["recommended_action", "acceptance_blockers"]
    assert controls["render_contract"]["default_focus_section_id"] == "recommended"
    assert controls["render_contract"]["default_expanded_section_ids"] == ["recommended", "blocked"]
    assert controls["render_contract"]["section_presentations"][0] == {
        "section_id": "recommended",
        "tone": "accent",
        "collapsible": False,
    }
    assert controls["render_contract"]["sticky_primary_action_id"] == controls["status_summary"]["recommended_action_id"]
    assert controls["render_contract"]["sticky_primary_action_emphasis"] == "strong"
    assert controls["render_contract"]["applied_feedback_dismissible"] is True
    assert controls["applied_action_feedback"]["follow_up_action_id"] == controls["status_summary"]["recommended_action_id"]


def test_get_review_bundle_tool_hides_owner_review_panel_contract_from_collaborator(tmp_path: Path) -> None:
    _, create_video_task_tool, get_review_bundle_tool, _ = _get_mcp_tools()
    app_context = _create_app_context(_build_required_auth_settings(tmp_path))
    owner = _seed_agent_profile_and_token(app_context, agent_id="agent-a", secret="agent-a-secret")
    reviewer = _seed_agent_profile_and_token(
        app_context,
        agent_id="agent-b",
        secret="agent-b-secret",
        scopes_json={"allow": ["task:read"]},
    )
    created = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle", "session_id": "session-1"},
        agent_principal=owner,
    )
    _seed_workflow_participant(
        app_context,
        root_task_id=created["task_id"],
        agent_id="agent-b",
    )

    bundle = get_review_bundle_tool(
        app_context,
        {"task_id": created["task_id"]},
        agent_principal=reviewer,
    )

    assert bundle["workflow_review_controls"] is None
