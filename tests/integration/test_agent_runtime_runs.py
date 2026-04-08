from pathlib import Path

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.server.app import create_app_context
from video_agent.server.mcp_tools import authenticate_agent_tool, create_video_task_tool
from tests.support import bootstrapped_settings


def _build_settings(tmp_path: Path) -> Settings:
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


def _seed_agent(app_context) -> None:
    app_context.store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A",
            profile_json={"style_hints": {"tone": "teaching"}},
        )
    )
    app_context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token("agent-a-secret"),
            agent_id="agent-a",
        )
    )


def test_authentication_records_runtime_run(tmp_path: Path) -> None:
    app = create_app_context(_build_settings(tmp_path))
    _seed_agent(app)

    payload = authenticate_agent_tool(
        app,
        {"agent_token": "agent-a-secret"},
        session_key="mcp-client-a",
    )
    runs = app.store.list_agent_runtime_runs(agent_id="agent-a")

    assert payload["authenticated"] is True
    assert len(runs) == 1
    assert runs[0].trigger_kind == "authenticate"
    assert runs[0].source_kind == "mcp_transport"


def test_create_task_records_runtime_run_for_authenticated_session(tmp_path: Path) -> None:
    app = create_app_context(_build_settings(tmp_path))
    _seed_agent(app)
    principal = app.agent_identity_service.authenticate("agent-a-secret")

    payload = create_video_task_tool(
        app,
        {
            "prompt": "draw a circle",
            "session_id": "gw-sess-123",
            "source_kind": "http_control",
        },
        agent_principal=principal,
    )
    runs = app.store.list_agent_runtime_runs(session_id="gw-sess-123")

    assert "task_id" in payload
    assert len(runs) == 1
    assert runs[0].trigger_kind == "create_video_task"
    assert runs[0].task_id == payload["task_id"]
