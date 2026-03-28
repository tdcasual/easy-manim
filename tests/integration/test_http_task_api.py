from collections.abc import Callable
from pathlib import Path
import sys
import types

from fastapi.testclient import TestClient

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.domain.enums import TaskPhase, TaskStatus
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


def test_task_create_list_get_result_roundtrip(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    login_token = _login(client, "agent-a-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "做一个蓝色圆形开场动画，画面干净简洁"},
        headers={"Authorization": f"Bearer {login_token}"},
    )
    assert created.status_code == 200
    created_payload = created.json()
    task_id = created_payload["task_id"]
    assert created_payload["display_title"] == "蓝色圆形开场动画"
    assert created_payload["title_source"] == "prompt"

    listed = client.get("/api/tasks", headers={"Authorization": f"Bearer {login_token}"})
    assert listed.status_code == 200
    listed_items = listed.json()["items"]
    assert any(item["task_id"] == task_id for item in listed_items)
    assert listed_items[0]["display_title"] == "蓝色圆形开场动画"
    assert listed_items[0]["title_source"] == "prompt"

    snapshot = client.get(f"/api/tasks/{task_id}", headers={"Authorization": f"Bearer {login_token}"})
    assert snapshot.status_code == 200
    snapshot_payload = snapshot.json()
    assert snapshot_payload["task_id"] == task_id
    assert snapshot_payload["agent_id"] == "agent-a"
    assert snapshot_payload["display_title"] == "蓝色圆形开场动画"
    assert snapshot_payload["title_source"] == "prompt"

    result = client.get(f"/api/tasks/{task_id}/result", headers={"Authorization": f"Bearer {login_token}"})
    assert result.status_code == 200
    assert result.json()["task_id"] == task_id
    assert result.json()["ready"] is False


def test_task_revise_retry_cancel_endpoints_are_agent_scoped(tmp_path: Path) -> None:
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
    task_id = created.json()["task_id"]

    forbidden_revise = client.post(
        f"/api/tasks/{task_id}/revise",
        json={"feedback": "make it blue"},
        headers={"Authorization": f"Bearer {login_token_b}"},
    )
    assert forbidden_revise.status_code == 403
    assert forbidden_revise.json()["detail"] == "agent_access_denied"

    revised = client.post(
        f"/api/tasks/{task_id}/revise",
        json={"feedback": "make it blue"},
        headers={"Authorization": f"Bearer {login_token_a}"},
    )
    assert revised.status_code == 200
    revised_snapshot = client.get(
        f"/api/tasks/{revised.json()['task_id']}",
        headers={"Authorization": f"Bearer {login_token_a}"},
    )
    assert revised_snapshot.status_code == 200
    assert revised_snapshot.json()["parent_task_id"] == task_id

    context = client.app.state.app_context
    stored = context.store.get_task(task_id)
    assert stored is not None
    stored.status = TaskStatus.FAILED
    stored.phase = TaskPhase.FAILED
    context.store.update_task(stored)

    forbidden_retry = client.post(
        f"/api/tasks/{task_id}/retry",
        headers={"Authorization": f"Bearer {login_token_b}"},
    )
    assert forbidden_retry.status_code == 403
    assert forbidden_retry.json()["detail"] == "agent_access_denied"

    retried = client.post(
        f"/api/tasks/{task_id}/retry",
        headers={"Authorization": f"Bearer {login_token_a}"},
    )
    assert retried.status_code == 200

    forbidden_cancel = client.post(
        f"/api/tasks/{task_id}/cancel",
        headers={"Authorization": f"Bearer {login_token_b}"},
    )
    assert forbidden_cancel.status_code == 403
    assert forbidden_cancel.json()["detail"] == "agent_access_denied"

    cancelled = client.post(
        f"/api/tasks/{task_id}/cancel",
        headers={"Authorization": f"Bearer {login_token_a}"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["task_id"] == task_id
    assert cancelled.json()["status"] == "cancelled"


def test_new_review_endpoints_do_not_change_existing_task_roundtrip(tmp_path: Path) -> None:
    settings = _build_http_task_settings(tmp_path)
    settings.multi_agent_workflow_enabled = True
    client = TestClient(_create_http_api(settings))
    _seed_agent(client, "agent-a", "agent-a-secret")
    login_token = _login(client, "agent-a-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "做一个蓝色圆形开场动画，画面干净简洁"},
        headers={"Authorization": f"Bearer {login_token}"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]

    listed = client.get("/api/tasks", headers={"Authorization": f"Bearer {login_token}"})
    assert listed.status_code == 200
    assert any(item["task_id"] == task_id for item in listed.json()["items"])

    snapshot = client.get(f"/api/tasks/{task_id}", headers={"Authorization": f"Bearer {login_token}"})
    assert snapshot.status_code == 200
    assert snapshot.json()["task_id"] == task_id

    result = client.get(f"/api/tasks/{task_id}/result", headers={"Authorization": f"Bearer {login_token}"})
    assert result.status_code == 200
    assert result.json()["task_id"] == task_id
    assert result.json()["ready"] is False
