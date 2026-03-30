from collections.abc import Callable
from pathlib import Path
import sys
import types

from fastapi.testclient import TestClient

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.domain.quality_models import QualityScorecard
from video_agent.domain.strategy_models import StrategyProfile
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
    assert snapshot_payload["risk_level"] is None
    assert snapshot_payload["generation_mode"] is None
    assert snapshot_payload["quality_gate_status"] is None
    assert snapshot_payload["accepted_as_best"] is False
    assert snapshot_payload["accepted_version_rank"] is None
    assert snapshot_payload["delivery_status"] == "pending"
    assert snapshot_payload["resolved_task_id"] is None
    assert snapshot_payload["completion_mode"] is None
    assert snapshot_payload["delivery_tier"] is None
    assert snapshot_payload["delivery_stop_reason"] is None

    result = client.get(f"/api/tasks/{task_id}/result", headers={"Authorization": f"Bearer {login_token}"})
    assert result.status_code == 200
    result_payload = result.json()
    assert result_payload["task_id"] == task_id
    assert result_payload["ready"] is False
    assert result_payload["delivery_status"] == "pending"
    assert result_payload["completion_mode"] is None
    assert result_payload["delivery_tier"] is None
    assert result_payload["resolved_task_id"] is None
    assert result_payload["delivery_stop_reason"] is None


def test_task_create_applies_cluster_strategy_when_requested(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    login_token = _login(client, "agent-a-secret")
    context = client.app.state.app_context
    strategy = context.store.create_strategy_profile(
        StrategyProfile(
            strategy_id="strategy-beta",
            scope="global",
            prompt_cluster="beta",
            status="active",
            params={"style_hints": {"tone": "teaching", "pace": "steady"}},
        )
    )

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle", "strategy_prompt_cluster": "beta"},
        headers={"Authorization": f"Bearer {login_token}"},
    )

    assert created.status_code == 200
    task_id = created.json()["task_id"]
    stored = context.store.get_task(task_id)
    assert stored is not None
    assert stored.strategy_profile_id == strategy.strategy_id
    assert stored.style_hints["tone"] == "teaching"
    assert stored.style_hints["pace"] == "steady"

    snapshot = client.get(f"/api/tasks/{task_id}", headers={"Authorization": f"Bearer {login_token}"})
    assert snapshot.status_code == 200
    assert snapshot.json()["strategy_profile_id"] == strategy.strategy_id


def test_task_create_does_not_apply_cluster_strategy_without_cluster_hint(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    login_token = _login(client, "agent-a-secret")
    context = client.app.state.app_context
    context.store.create_strategy_profile(
        StrategyProfile(
            strategy_id="strategy-beta",
            scope="global",
            prompt_cluster="beta",
            status="active",
            params={"style_hints": {"tone": "teaching"}},
        )
    )

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {login_token}"},
    )

    assert created.status_code == 200
    stored = context.store.get_task(created.json()["task_id"])
    assert stored is not None
    assert stored.strategy_profile_id is None
    assert stored.style_hints["tone"] == "agent-a-tone"


def test_task_create_auto_routes_cluster_strategy_from_prompt_keywords(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    login_token = _login(client, "agent-a-secret")
    context = client.app.state.app_context
    strategy = context.store.create_strategy_profile(
        StrategyProfile(
            strategy_id="strategy-geometry",
            scope="global",
            prompt_cluster="geometry",
            status="active",
            params={
                "routing": {"keywords": ["triangle", "geometry"]},
                "style_hints": {"tone": "teaching"},
            },
        )
    )

    created = client.post(
        "/api/tasks",
        json={"prompt": "Explain triangle area proof"},
        headers={"Authorization": f"Bearer {login_token}"},
    )

    assert created.status_code == 200
    stored = context.store.get_task(created.json()["task_id"])
    assert stored is not None
    assert stored.strategy_profile_id == strategy.strategy_id
    assert stored.style_hints["tone"] == "teaching"


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


def test_reliability_endpoints_are_agent_scoped(tmp_path: Path) -> None:
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

    context = client.app.state.app_context
    context.artifact_store.write_scene_spec(
        task_id,
        {"task_id": task_id, "summary": "draw a circle", "scene_count": 1, "scenes": []},
    )
    context.store.upsert_task_quality_score(
        task_id,
        QualityScorecard(task_id=task_id, total_score=0.9, accepted=True),
    )

    forbidden_scene_spec = client.get(
        f"/api/tasks/{task_id}/scene-spec",
        headers={"Authorization": f"Bearer {login_token_b}"},
    )
    forbidden_quality = client.get(
        f"/api/tasks/{task_id}/quality-score",
        headers={"Authorization": f"Bearer {login_token_b}"},
    )
    forbidden_accept = client.post(
        f"/api/tasks/{task_id}/accept-best",
        headers={"Authorization": f"Bearer {login_token_b}"},
    )

    assert forbidden_scene_spec.status_code == 403
    assert forbidden_scene_spec.json()["detail"] == "agent_access_denied"
    assert forbidden_quality.status_code == 403
    assert forbidden_quality.json()["detail"] == "agent_access_denied"
    assert forbidden_accept.status_code == 403
    assert forbidden_accept.json()["detail"] == "agent_access_denied"


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
