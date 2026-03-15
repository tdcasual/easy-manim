from pathlib import Path

import pytest

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.server.app import create_app_context
from video_agent.server.mcp_resources import read_resource_for_agent
from video_agent.server.mcp_tools import create_video_task_tool


def _build_agent_auth_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return Settings(
        data_dir=data_dir,
        database_path=data_dir / "video_agent.db",
        artifact_root=data_dir / "tasks",
        run_embedded_worker=False,
        auth_mode="required",
    )


def _seed_agent(app, agent_id: str, secret: str) -> None:
    app.store.upsert_agent_profile(AgentProfile(agent_id=agent_id, name=agent_id))
    app.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token(secret),
            agent_id=agent_id,
        )
    )


def _create_task_for_agent(app, secret: str, prompt: str = "draw a circle") -> str:
    principal = app.agent_identity_service.authenticate(secret)
    payload = create_video_task_tool(app, {"prompt": prompt}, agent_principal=principal)
    return payload["task_id"]


def _create_task_with_script_artifact_for_agent(app, secret: str) -> str:
    task_id = _create_task_for_agent(app, secret)
    app.artifact_store.write_script(task_id, "print('agent owned script')\n")
    return task_id


def test_agent_cannot_read_another_agents_task_snapshot(tmp_path: Path) -> None:
    app = create_app_context(_build_agent_auth_settings(tmp_path))
    _seed_agent(app, "agent-a", "agent-a-secret")
    _seed_agent(app, "agent-b", "agent-b-secret")
    task_id = _create_task_for_agent(app, "agent-a-secret")

    with pytest.raises(PermissionError):
        app.task_service.get_video_task_for_agent(task_id, agent_id="agent-b")


def test_agent_cannot_read_another_agents_resource(tmp_path: Path) -> None:
    app = create_app_context(_build_agent_auth_settings(tmp_path))
    _seed_agent(app, "agent-a", "agent-a-secret")
    _seed_agent(app, "agent-b", "agent-b-secret")
    task_id = _create_task_with_script_artifact_for_agent(app, "agent-a-secret")

    with pytest.raises(PermissionError):
        read_resource_for_agent(app, f"video-task://{task_id}/artifacts/current_script.py", agent_id="agent-b")
