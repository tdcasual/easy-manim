from collections.abc import Callable
from pathlib import Path
import sys
import types

from fastapi.testclient import TestClient

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


def _create_http_api(settings: Settings):
    def _load():
        from video_agent.server.http_api import create_http_api

        return create_http_api(settings)

    return _with_temporary_mcp_shim(_load)


def _build_http_task_settings(tmp_path: Path) -> Settings:
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


def _seed_agent(client: TestClient, agent_id: str, secret: str) -> None:
    context = client.app.state.app_context
    context.store.upsert_agent_profile(
        AgentProfile(
            agent_id=agent_id,
            name=agent_id,
            profile_json={"style_hints": {"tone": f"{agent_id}-tone"}},
        )
    )
    context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token(secret),
            agent_id=agent_id,
        )
    )


def _login(client: TestClient, secret: str) -> str:
    response = client.post("/api/sessions", json={"agent_token": secret})
    assert response.status_code == 200
    return response.json()["session_token"]


def _seed_workflow_participant(
    client: TestClient,
    *,
    root_task_id: str,
    agent_id: str,
    role: str = "reviewer",
    capabilities: list[str] | None = None,
) -> None:
    client.app.state.app_context.store.upsert_workflow_participant(
        WorkflowParticipant(
            root_task_id=root_task_id,
            agent_id=agent_id,
            role=role,
            capabilities=capabilities or ["review_bundle:read", "review_decision:write"],
        )
    )


def _seed_memory(
    client: TestClient,
    *,
    memory_id: str,
    agent_id: str,
    summary_text: str,
) -> None:
    client.app.state.app_context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id=memory_id,
            agent_id=agent_id,
            source_session_id=f"session-{agent_id}",
            summary_text=summary_text,
            summary_digest=f"digest-{memory_id}",
        )
    )


def test_http_review_bundle_and_decision_flow(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    session_token = _login(client, "agent-a-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]

    bundle = client.get(
        f"/api/tasks/{task_id}/review-bundle",
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert bundle.status_code == 200
    assert bundle.json()["task_id"] == task_id
    assert bundle.json()["collaboration"]["planner_recommendation"]["role"] == "planner"
    assert bundle.json()["collaboration"]["reviewer_decision"]["role"] == "reviewer"
    assert bundle.json()["collaboration"]["repairer_execution_hint"]["role"] == "repairer"
    assert bundle.json()["branch_scoreboard"][0]["task_id"] == task_id
    assert bundle.json()["arbitration_summary"]["recommended_task_id"] == task_id
    assert bundle.json()["arbitration_summary"]["recommended_action"] == "wait_for_completion"

    decision = client.post(
        f"/api/tasks/{task_id}/review-decision",
        json={
            "review_decision": {
                "decision": "revise",
                "summary": "Improve emphasis",
                "feedback": "Make it blue and add a title",
            }
        },
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert decision.status_code == 200
    assert decision.json()["action"] == "revise"
    assert decision.json()["created_task_id"]
    assert decision.json()["reason"] == "revision_created"
    assert decision.json()["refresh_scope"] == "navigate"
    assert decision.json()["refresh_task_id"] == decision.json()["created_task_id"]


def test_http_review_decision_accept_returns_task_and_panel_refresh_scope(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    session_token = _login(client, "agent-a-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]
    task = client.app.state.app_context.store.get_task(task_id)
    assert task is not None
    task.status = TaskStatus.COMPLETED
    task.phase = TaskPhase.COMPLETED
    task.delivery_status = "delivered"
    task.resolved_task_id = task.task_id
    client.app.state.app_context.store.update_task(task)

    decision = client.post(
        f"/api/tasks/{task_id}/review-decision",
        json={
            "review_decision": {
                "decision": "accept",
                "summary": "Looks good",
            }
        },
        headers={"Authorization": f"Bearer {session_token}"},
    )

    assert decision.status_code == 200
    assert decision.json()["action"] == "accept"
    assert decision.json()["created_task_id"] is None
    assert decision.json()["reason"] == "winner_selected"
    assert decision.json()["refresh_scope"] == "task_and_panel"
    assert decision.json()["refresh_task_id"] == task_id


def test_http_legacy_discussion_message_endpoint_returns_gone(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    owner_token = _login(client, "agent-a-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert created.status_code == 200

    removed = client.post(
        f"/api/tasks/{created.json()['task_id']}/discussion-messages",
        json={
            "title": "Legacy message",
            "summary": "This endpoint should no longer accept owner discussion turns.",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert removed.status_code == 410
    assert removed.json()["detail"] == "legacy_discussion_transport_removed"


def test_http_legacy_discussion_thread_endpoint_returns_gone(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    session_token = _login(client, "agent-a-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert created.status_code == 200

    removed = client.get(
        f"/api/tasks/{created.json()['task_id']}/discussion-thread",
        headers={"Authorization": f"Bearer {session_token}"},
    )

    assert removed.status_code == 410
    assert removed.json()["detail"] == "legacy_discussion_transport_removed"


def test_http_review_bundle_omits_legacy_video_discussion_surface(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    session_token = _login(client, "agent-a-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert created.status_code == 200

    bundle = client.get(
        f"/api/tasks/{created.json()['task_id']}/review-bundle",
        headers={"Authorization": f"Bearer {session_token}"},
    )

    assert bundle.status_code == 200
    assert bundle.json()["task_id"] == created.json()["task_id"]
    assert "video_discussion_surface" not in bundle.json()


def test_http_review_workflow_is_agent_scoped(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    _seed_agent(client, "agent-b", "agent-b-secret")
    login_token_a = _login(client, "agent-a-secret")
    login_token_b = _login(client, "agent-b-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {login_token_a}"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]

    forbidden_bundle = client.get(
        f"/api/tasks/{task_id}/review-bundle",
        headers={"Authorization": f"Bearer {login_token_b}"},
    )
    assert forbidden_bundle.status_code == 403
    assert forbidden_bundle.json()["detail"] == "agent_access_denied"

    forbidden_decision = client.post(
        f"/api/tasks/{task_id}/review-decision",
        json={
            "review_decision": {
                "decision": "revise",
                "summary": "Improve emphasis",
                "feedback": "Make it blue and add a title",
            }
        },
        headers={"Authorization": f"Bearer {login_token_b}"},
    )
    assert forbidden_decision.status_code == 403
    assert forbidden_decision.json()["detail"] == "agent_access_denied"


def test_http_review_workflow_participant_can_review_but_not_mutate_directly(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    _seed_agent(client, "agent-b", "agent-b-secret")
    owner_token = _login(client, "agent-a-secret")
    reviewer_token = _login(client, "agent-b-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]
    _seed_workflow_participant(client, root_task_id=task_id, agent_id="agent-b")

    bundle = client.get(
        f"/api/tasks/{task_id}/review-bundle",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    decision = client.post(
        f"/api/tasks/{task_id}/review-decision",
        json={
            "review_decision": {
                "decision": "revise",
                "summary": "Improve emphasis",
                "feedback": "Make it blue and add a title",
            }
        },
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    direct_revise = client.post(
        f"/api/tasks/{task_id}/revise",
        json={"feedback": "Bypass workflow controls"},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    assert bundle.status_code == 200
    assert bundle.json()["task_id"] == task_id
    assert decision.status_code == 200
    assert decision.json()["action"] == "revise"
    assert decision.json()["created_task_id"]
    revised = client.app.state.app_context.store.get_task(decision.json()["created_task_id"])
    assert revised is not None
    assert revised.agent_id == "agent-a"
    assert direct_revise.status_code == 403
    assert direct_revise.json()["detail"] == "agent_access_denied"


def test_http_owner_can_pin_workflow_memory_via_review_decision(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    owner_token = _login(client, "agent-a-secret")
    _seed_memory(
        client,
        memory_id="mem-a",
        agent_id="agent-a",
        summary_text="Prefer high-contrast diagrams with concise labels.",
    )

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]

    decision = client.post(
        f"/api/tasks/{task_id}/review-decision",
        json={
            "review_decision": {
                "decision": "revise",
                "summary": "Improve emphasis",
                "feedback": "Make it blue and add a title",
            },
            "pin_workflow_memory_ids": ["mem-a"],
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert decision.status_code == 200
    assert decision.json()["action"] == "revise"
    assert decision.json()["workflow_memory_state"]["pinned_memory_ids"] == ["mem-a"]
    revised = client.app.state.app_context.store.get_task(decision.json()["created_task_id"])
    root_task = client.app.state.app_context.store.get_task(task_id)
    assert revised is not None
    assert revised.selected_memory_ids == ["mem-a"]
    assert root_task is not None
    assert root_task.selected_memory_ids == ["mem-a"]


def test_http_collaborator_cannot_pin_workflow_memory_via_review_decision(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    _seed_agent(client, "agent-b", "agent-b-secret")
    owner_token = _login(client, "agent-a-secret")
    reviewer_token = _login(client, "agent-b-secret")
    _seed_memory(
        client,
        memory_id="mem-a",
        agent_id="agent-a",
        summary_text="Prefer high-contrast diagrams with concise labels.",
    )

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]
    _seed_workflow_participant(client, root_task_id=task_id, agent_id="agent-b")

    decision = client.post(
        f"/api/tasks/{task_id}/review-decision",
        json={
            "review_decision": {
                "decision": "revise",
                "summary": "Improve emphasis",
                "feedback": "Make it blue and add a title",
            },
            "pin_workflow_memory_ids": ["mem-a"],
        },
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    assert decision.status_code == 403
    assert decision.json()["detail"] == "agent_access_denied"


def test_http_owner_can_manage_workflow_participants(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    _seed_agent(client, "agent-b", "agent-b-secret")
    owner_token = _login(client, "agent-a-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]

    upserted = client.post(
        f"/api/tasks/{task_id}/workflow-participants",
        json={"agent_id": "agent-b", "role": "reviewer"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    listed = client.get(
        f"/api/tasks/{task_id}/workflow-participants",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    removed = client.delete(
        f"/api/tasks/{task_id}/workflow-participants/agent-b",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert upserted.status_code == 200
    assert upserted.json()["participant"]["agent_id"] == "agent-b"
    assert upserted.json()["participant"]["role"] == "reviewer"
    assert listed.status_code == 200
    assert listed.json()["items"][0]["agent_id"] == "agent-b"
    assert listed.json()["items"][0]["capabilities"] == ["review_bundle:read", "review_decision:write"]
    assert removed.status_code == 200
    assert removed.json() == {
        "task_id": task_id,
        "root_task_id": task_id,
        "agent_id": "agent-b",
        "removed": True,
    }


def test_http_non_owner_cannot_manage_workflow_participants(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    _seed_agent(client, "agent-b", "agent-b-secret")
    owner_token = _login(client, "agent-a-secret")
    intruder_token = _login(client, "agent-b-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]

    listed = client.get(
        f"/api/tasks/{task_id}/workflow-participants",
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    upserted = client.post(
        f"/api/tasks/{task_id}/workflow-participants",
        json={"agent_id": "agent-b", "role": "reviewer"},
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    removed = client.delete(
        f"/api/tasks/{task_id}/workflow-participants/agent-b",
        headers={"Authorization": f"Bearer {intruder_token}"},
    )

    assert listed.status_code == 403
    assert listed.json()["detail"] == "agent_access_denied"
    assert upserted.status_code == 403
    assert upserted.json()["detail"] == "agent_access_denied"
    assert removed.status_code == 403
    assert removed.json()["detail"] == "agent_access_denied"


def test_http_custom_workflow_capabilities_allow_read_without_review_decision(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    _seed_agent(client, "agent-b", "agent-b-secret")
    owner_token = _login(client, "agent-a-secret")
    reviewer_token = _login(client, "agent-b-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]

    upserted = client.post(
        f"/api/tasks/{task_id}/workflow-participants",
        json={
            "agent_id": "agent-b",
            "role": "reviewer",
            "capabilities": ["review_bundle:read"],
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    bundle = client.get(
        f"/api/tasks/{task_id}/review-bundle",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    decision = client.post(
        f"/api/tasks/{task_id}/review-decision",
        json={
            "review_decision": {
                "decision": "revise",
                "summary": "Improve emphasis",
                "feedback": "Make it blue and add a title",
            }
        },
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    assert upserted.status_code == 200
    assert upserted.json()["participant"]["capabilities"] == ["review_bundle:read"]
    assert bundle.status_code == 200
    assert bundle.json()["task_id"] == task_id
    assert decision.status_code == 403
    assert decision.json()["detail"] == "agent_access_denied"


def test_http_owner_can_manage_workflow_memory(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    owner_token = _login(client, "agent-a-secret")
    _seed_memory(
        client,
        memory_id="mem-a",
        agent_id="agent-a",
        summary_text="Prefer high-contrast diagrams with concise labels.",
    )

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle with contrast"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]

    recommendations = client.get(
        f"/api/tasks/{task_id}/workflow-memory/recommendations",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    pinned = client.post(
        f"/api/tasks/{task_id}/workflow-memory/pins",
        json={"memory_id": "mem-a"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    unpinned = client.delete(
        f"/api/tasks/{task_id}/workflow-memory/pins/mem-a",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert recommendations.status_code == 200
    assert recommendations.json()["root_task_id"] == task_id
    assert recommendations.json()["items"][0]["memory_id"] == "mem-a"
    assert recommendations.json()["items"][0]["pinned"] is False
    assert pinned.status_code == 200
    assert pinned.json()["memory_id"] == "mem-a"
    assert pinned.json()["pinned_memory_ids"] == ["mem-a"]
    assert "high-contrast diagrams" in (pinned.json()["persistent_memory_context_summary"] or "")
    assert unpinned.status_code == 200
    assert unpinned.json()["memory_id"] == "mem-a"
    assert unpinned.json()["pinned_memory_ids"] == []


def test_http_review_bundle_exposes_owner_review_panel_contract(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    owner_token = _login(client, "agent-a-secret")
    _seed_memory(
        client,
        memory_id="mem-a",
        agent_id="agent-a",
        summary_text="Prefer high-contrast diagrams with concise labels.",
    )

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle with contrast"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]

    client.post(
        f"/api/tasks/{task_id}/workflow-memory/pins",
        json={"memory_id": "mem-a"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    bundle = client.get(
        f"/api/tasks/{task_id}/review-bundle",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert bundle.status_code == 200
    controls = bundle.json()["workflow_review_controls"]
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


def test_http_review_bundle_hides_owner_review_panel_contract_from_collaborator(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    _seed_agent(client, "agent-b", "agent-b-secret")
    owner_token = _login(client, "agent-a-secret")
    reviewer_token = _login(client, "agent-b-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]
    _seed_workflow_participant(client, root_task_id=task_id, agent_id="agent-b")

    bundle = client.get(
        f"/api/tasks/{task_id}/review-bundle",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    assert bundle.status_code == 200
    assert bundle.json()["workflow_review_controls"] is None


def test_http_non_owner_cannot_manage_workflow_memory(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    _seed_agent(client, "agent-b", "agent-b-secret")
    owner_token = _login(client, "agent-a-secret")
    intruder_token = _login(client, "agent-b-secret")
    _seed_memory(
        client,
        memory_id="mem-a",
        agent_id="agent-a",
        summary_text="Prefer high-contrast diagrams with concise labels.",
    )

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle with contrast"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]

    recommendations = client.get(
        f"/api/tasks/{task_id}/workflow-memory/recommendations",
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    pinned = client.post(
        f"/api/tasks/{task_id}/workflow-memory/pins",
        json={"memory_id": "mem-a"},
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    unpinned = client.delete(
        f"/api/tasks/{task_id}/workflow-memory/pins/mem-a",
        headers={"Authorization": f"Bearer {intruder_token}"},
    )

    assert recommendations.status_code == 403
    assert recommendations.json()["detail"] == "agent_access_denied"
    assert pinned.status_code == 403
    assert pinned.json()["detail"] == "agent_access_denied"
    assert unpinned.status_code == 403
    assert unpinned.json()["detail"] == "agent_access_denied"


def test_http_review_decision_rejects_invalid_payload(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    session_token = _login(client, "agent-a-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]

    decision = client.post(
        f"/api/tasks/{task_id}/review-decision",
        json={
            "review_decision": {
                "decision": "revise",
                "summary": "Improve emphasis",
            }
        },
        headers={"Authorization": f"Bearer {session_token}"},
    )

    assert decision.status_code == 400
    assert decision.json()["detail"] == "invalid_review_decision"


def test_http_review_decision_returns_acceptance_blocked_reason(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    session_token = _login(client, "agent-a-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]

    decision = client.post(
        f"/api/tasks/{task_id}/review-decision",
        json={
            "review_decision": {
                "decision": "accept",
                "summary": "Looks good",
            }
        },
        headers={"Authorization": f"Bearer {session_token}"},
    )

    assert decision.status_code == 200
    assert decision.json()["action"] == "escalate"
    assert decision.json()["reason"] == "acceptance_blocked"
