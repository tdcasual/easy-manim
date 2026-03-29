from pathlib import Path

from fastapi.testclient import TestClient

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.server.app import create_app_context
from video_agent.server.http_api import create_http_api
from video_agent.server.mcp_tools import get_runtime_status_tool
from tests.support import bootstrapped_settings


def _write_executable(path: Path) -> None:
    path.write_text("#!/bin/sh\nexit 0\n")
    path.chmod(0o755)


def test_runtime_status_tool_reports_binary_and_provider_state(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    fake_latex = tmp_path / "fake_latex.sh"
    fake_dvisvgm = tmp_path / "fake_dvisvgm.sh"
    _write_executable(fake_latex)
    _write_executable(fake_dvisvgm)
    settings = Settings(
        data_dir=data_dir,
        database_path=data_dir / "video_agent.db",
        artifact_root=data_dir / "tasks",
        manim_command="manim",
        ffmpeg_command="ffmpeg",
        ffprobe_command="ffprobe",
        latex_command=str(fake_latex),
        dvisvgm_command=str(fake_dvisvgm),
        llm_provider="stub",
        run_embedded_worker=False,
    )
    SQLiteBootstrapper(settings.database_path).bootstrap()
    context = create_app_context(settings)

    payload = get_runtime_status_tool(context, {})

    assert payload["provider"]["mode"] == "stub"
    assert payload["provider"]["api_base_present"] is False
    assert payload["storage"]["data_dir"].endswith("data")
    assert set(payload["checks"]).issuperset({"manim", "ffmpeg", "ffprobe", "latex", "dvisvgm"})
    assert payload["features"]["mathtex"]["available"] is True
    assert payload["features"]["mathtex"]["checked"] is False
    assert payload["features"]["mathtex"]["missing_checks"] == []
    assert payload["features"]["mathtex"]["smoke_error"] is None
    assert payload["worker"]["embedded"] is False
    assert payload["sandbox"]["network_disabled"] is False
    assert payload["sandbox"]["temp_root_allowed"] is True
    assert payload["sandbox"]["process_limit"] is None
    assert payload["sandbox"]["memory_limit_mb"] is None
    assert payload["release"]["version"]
    assert payload["release"]["channel"] == "beta"
    assert payload["capabilities"]["rollout_profile"] == "conservative"
    assert payload["capabilities"]["effective"] == {
        "agent_learning_auto_apply_enabled": False,
        "auto_repair_enabled": False,
        "multi_agent_workflow_enabled": False,
        "strategy_promotion_enabled": False,
    }


def test_http_runtime_status_returns_payload_when_auth_optional(tmp_path: Path) -> None:
    settings = bootstrapped_settings(
        Settings(
            data_dir=tmp_path / "data",
            database_path=tmp_path / "data" / "video_agent.db",
            artifact_root=tmp_path / "data" / "tasks",
            auth_mode="optional",
            capability_rollout_profile="supervised",
            run_embedded_worker=False,
        )
    )
    client = TestClient(create_http_api(settings))

    response = client.get("/api/runtime/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["capabilities"]["rollout_profile"] == "supervised"
    assert payload["capabilities"]["effective"] == {
        "agent_learning_auto_apply_enabled": False,
        "auto_repair_enabled": True,
        "multi_agent_workflow_enabled": True,
        "strategy_promotion_enabled": False,
    }


def test_http_runtime_status_requires_auth_when_mode_required(tmp_path: Path) -> None:
    settings = bootstrapped_settings(
        Settings(
            data_dir=tmp_path / "data",
            database_path=tmp_path / "data" / "video_agent.db",
            artifact_root=tmp_path / "data" / "tasks",
            auth_mode="required",
            run_embedded_worker=False,
        )
    )
    client = TestClient(create_http_api(settings))

    response = client.get("/api/runtime/status")

    assert response.status_code == 401
    assert response.json()["detail"] == "missing_session_token"


def test_http_runtime_status_allows_authenticated_read_scope(tmp_path: Path) -> None:
    settings = bootstrapped_settings(
        Settings(
            data_dir=tmp_path / "data",
            database_path=tmp_path / "data" / "video_agent.db",
            artifact_root=tmp_path / "data" / "tasks",
            auth_mode="required",
            run_embedded_worker=False,
        )
    )
    client = TestClient(create_http_api(settings))
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
            scopes_json={"allow": ["task:read"]},
        )
    )

    login = client.post("/api/sessions", json={"agent_token": "agent-a-secret"})
    session_token = login.json()["session_token"]

    response = client.get("/api/runtime/status", headers={"Authorization": f"Bearer {session_token}"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["capabilities"]["rollout_profile"] == "conservative"
    assert payload["capabilities"]["effective"]["auto_repair_enabled"] is False
