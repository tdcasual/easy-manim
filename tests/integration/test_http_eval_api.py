import json
from pathlib import Path

from fastapi.testclient import TestClient

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.domain.strategy_models import StrategyProfile
from video_agent.server.http_api import create_http_api
from tests.support import bootstrapped_settings


def _build_http_eval_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            eval_root=data_dir / "evals",
            run_embedded_worker=False,
            auth_mode="required",
        )
    )


def _seed_agent(client: TestClient) -> str:
    context = client.app.state.app_context
    context.store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A",
            profile_json={"style_hints": {"tone": "patient"}},
        )
    )
    context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token("agent-a-secret"),
            agent_id="agent-a",
            scopes_json={"allow": ["profile:read"]},
        )
    )
    return client.post("/api/sessions", json={"agent_token": "agent-a-secret"}).json()["session_token"]


def test_http_profile_evals_lists_eval_summaries(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_eval_settings(tmp_path)))
    session_token = _seed_agent(client)
    context = client.app.state.app_context
    context.artifact_store.write_eval_summary(
        "run-1",
        {
            "run_id": "run-1",
            "suite_id": "suite-a",
            "provider": "stub",
            "total_cases": 1,
            "items": [],
            "report": {"success_rate": 1.0},
        },
    )

    response = client.get("/api/profile/evals", headers={"Authorization": f"Bearer {session_token}"})

    assert response.status_code == 200
    assert response.json()["items"][0]["run_id"] == "run-1"


def test_http_profile_evals_detail_returns_run_summary(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_eval_settings(tmp_path)))
    session_token = _seed_agent(client)
    context = client.app.state.app_context
    context.artifact_store.write_eval_summary(
        "run-1",
        {
            "run_id": "run-1",
            "suite_id": "suite-a",
            "provider": "stub",
            "total_cases": 1,
            "items": [],
            "report": {"success_rate": 1.0},
        },
    )

    response = client.get("/api/profile/evals/run-1", headers={"Authorization": f"Bearer {session_token}"})

    assert response.status_code == 200
    assert response.json()["run_id"] == "run-1"
    assert response.json()["report"]["success_rate"] == 1.0


def test_http_strategy_timeline_returns_shadow_decisions(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_eval_settings(tmp_path)))
    session_token = _seed_agent(client)
    context = client.app.state.app_context
    strategy = context.store.create_strategy_profile(
        StrategyProfile(
            strategy_id="strategy-1",
            scope="global",
            prompt_cluster="beta",
            status="candidate",
            params={"style_hints": {"tone": "teaching"}},
        )
    )
    context.store.record_strategy_eval_run(
        strategy.strategy_id,
        baseline_summary={
            "run_id": "baseline-run",
            "report": {"success_rate": 0.4, "quality": {"pass_rate": 0.5}},
        },
        challenger_summary={
            "run_id": "challenger-run",
            "report": {"success_rate": 0.7, "quality": {"pass_rate": 0.8}},
        },
        promotion_recommended=True,
        promotion_decision={
            "approved": True,
            "reasons": [],
            "deltas": {"final_success_rate": 0.3},
            "mode": "shadow",
            "applied": False,
        },
    )

    response = client.get("/api/profile/strategy-decisions", headers={"Authorization": f"Bearer {session_token}"})

    assert response.status_code == 200
    assert response.json()["items"][0]["kind"] == "strategy_promotion_shadow"
    assert response.json()["items"][0]["strategy_id"] == "strategy-1"
    assert response.json()["items"][0]["promotion_decision"]["mode"] == "shadow"


def test_http_strategy_timeline_returns_applied_decisions(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_eval_settings(tmp_path)))
    session_token = _seed_agent(client)
    context = client.app.state.app_context
    strategy = context.store.create_strategy_profile(
        StrategyProfile(
            strategy_id="strategy-1",
            scope="global",
            prompt_cluster="beta",
            status="candidate",
            params={"style_hints": {"tone": "teaching"}},
        )
    )
    context.store.record_strategy_eval_run(
        strategy.strategy_id,
        baseline_summary={
            "run_id": "baseline-run",
            "report": {"success_rate": 0.4, "quality": {"pass_rate": 0.5}},
        },
        challenger_summary={
            "run_id": "challenger-run",
            "report": {"success_rate": 0.7, "quality": {"pass_rate": 0.8}},
        },
        promotion_recommended=True,
        promotion_decision={
            "approved": True,
            "reasons": [],
            "deltas": {"final_success_rate": 0.3},
            "mode": "guarded_auto_apply",
            "applied": True,
        },
    )

    response = client.get("/api/profile/strategy-decisions", headers={"Authorization": f"Bearer {session_token}"})

    assert response.status_code == 200
    assert response.json()["items"][0]["kind"] == "strategy_promotion_applied"
    assert response.json()["items"][0]["promotion_decision"]["mode"] == "guarded_auto_apply"
