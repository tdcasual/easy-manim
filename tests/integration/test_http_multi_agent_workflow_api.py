from collections.abc import Callable
from pathlib import Path
import sys
import types

from fastapi.testclient import TestClient

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
