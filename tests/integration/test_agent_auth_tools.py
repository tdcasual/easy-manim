from pathlib import Path

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.server.app import create_app_context
from video_agent.server.mcp_tools import authenticate_agent_tool, create_video_task_tool, revise_video_task_tool
from video_agent.server.session_auth import SessionAuthRegistry


def _build_agent_auth_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return Settings(
        data_dir=data_dir,
        database_path=data_dir / "video_agent.db",
        artifact_root=data_dir / "tasks",
        run_embedded_worker=False,
        auth_mode="required",
    )


def _seed_agent_profile_and_token(store) -> None:
    store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A",
            profile_json={"style_hints": {"tone": "patient", "pace": "steady"}},
        )
    )
    store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token("agent-a-secret"),
            agent_id="agent-a",
            override_json={"style_hints": {"tone": "teaching"}},
        )
    )


def test_authenticate_agent_returns_profile_summary(tmp_path: Path) -> None:
    app = create_app_context(_build_agent_auth_settings(tmp_path))
    _seed_agent_profile_and_token(app.store)

    payload = authenticate_agent_tool(app, {"agent_token": "agent-a-secret"})

    assert payload["agent_id"] == "agent-a"
    assert payload["authenticated"] is True


def test_create_video_task_uses_authenticated_agent_defaults(tmp_path: Path) -> None:
    app = create_app_context(_build_agent_auth_settings(tmp_path))
    _seed_agent_profile_and_token(app.store)
    session_auth = SessionAuthRegistry()
    principal = app.agent_identity_service.authenticate("agent-a-secret")
    session_auth.authenticate("session-a", principal)

    payload = create_video_task_tool(
        app,
        {"prompt": "draw a circle"},
        agent_principal=session_auth.require("session-a"),
    )

    task = app.store.get_task(payload["task_id"])

    assert task is not None
    assert task.agent_id == "agent-a"
    assert task.style_hints["tone"] == "teaching"


def test_revise_video_task_preserves_authenticated_agent_profile(tmp_path: Path) -> None:
    app = create_app_context(_build_agent_auth_settings(tmp_path))
    _seed_agent_profile_and_token(app.store)
    principal = app.agent_identity_service.authenticate("agent-a-secret")
    created = create_video_task_tool(
        app,
        {"prompt": "draw a circle"},
        agent_principal=principal,
    )

    revised = revise_video_task_tool(
        app,
        {"base_task_id": created["task_id"], "feedback": "make it blue"},
        agent_principal=principal,
    )

    task = app.store.get_task(revised["task_id"])

    assert task is not None
    assert task.agent_id == "agent-a"
    assert task.style_hints["tone"] == "teaching"
    assert task.effective_request_profile["style_hints"]["tone"] == "teaching"
