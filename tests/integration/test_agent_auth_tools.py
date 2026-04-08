from pathlib import Path

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.server.app import create_app_context
from video_agent.server.mcp_tools import authenticate_agent_tool, create_video_task_tool, get_video_task_tool, revise_video_task_tool
from video_agent.server.session_auth import SessionAuthRegistry
from tests.support import bootstrapped_settings


def _build_agent_auth_settings(tmp_path: Path) -> Settings:
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


def _seed_agent_profile_and_token(
    store,
    *,
    secret: str = "agent-a-secret",
    scopes_json: dict | None = None,
    policy_json: dict | None = None,
) -> None:
    store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A",
            profile_json={"style_hints": {"tone": "patient", "pace": "steady"}},
            policy_json=policy_json or {},
        )
    )
    store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token(secret),
            agent_id="agent-a",
            scopes_json=scopes_json or {},
            override_json={"style_hints": {"tone": "teaching"}},
        )
    )


def _delete_runtime_definition(store, agent_id: str) -> None:
    with store._connect() as connection:
        connection.execute(
            "DELETE FROM agent_runtime_definitions WHERE agent_id = ?",
            (agent_id,),
        )


def test_authenticate_agent_returns_profile_summary(tmp_path: Path) -> None:
    app = create_app_context(_build_agent_auth_settings(tmp_path))
    _seed_agent_profile_and_token(app.store)

    payload = authenticate_agent_tool(app, {"agent_token": "agent-a-secret"})
    principal = app.agent_identity_service.authenticate("agent-a-secret")
    stored_runtime_definition = app.store.get_agent_runtime_definition("agent-a")

    assert payload["agent_id"] == "agent-a"
    assert payload["authenticated"] is True
    assert principal.runtime_definition.agent_id == "agent-a"
    assert principal.runtime_definition.definition_source in {"explicit", "materialized"}
    assert stored_runtime_definition is not None
    assert stored_runtime_definition.definition_source in {"explicit", "materialized"}


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
    snapshot = get_video_task_tool(app, {"task_id": payload["task_id"]}, agent_principal=principal)

    assert task is not None
    assert task.agent_id == "agent-a"
    assert task.style_hints["tone"] == "teaching"
    assert snapshot["agent_id"] == "agent-a"


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
    assert task.profile_version == 1
    assert task.effective_policy_flags == {}


def test_create_video_task_rejects_scope_limited_token(tmp_path: Path) -> None:
    app = create_app_context(_build_agent_auth_settings(tmp_path))
    _seed_agent_profile_and_token(app.store, secret="agent-a-read-secret", scopes_json={"allow": ["task:read"]})
    principal = app.agent_identity_service.authenticate("agent-a-read-secret")

    payload = create_video_task_tool(
        app,
        {"prompt": "draw a circle"},
        agent_principal=principal,
    )

    assert payload["error"]["code"] == "agent_scope_denied"


def test_revise_video_task_respects_profile_policy_denials(tmp_path: Path) -> None:
    app = create_app_context(_build_agent_auth_settings(tmp_path))
    _seed_agent_profile_and_token(app.store, policy_json={"deny_actions": ["task:mutate"]})
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

    assert revised["error"]["code"] == "agent_scope_denied"


def test_create_video_task_persists_profile_version_and_resolved_defaults(tmp_path: Path) -> None:
    app = create_app_context(_build_agent_auth_settings(tmp_path))
    _seed_agent_profile_and_token(app.store)
    principal = app.agent_identity_service.authenticate("agent-a-secret")

    payload = create_video_task_tool(app, {"prompt": "draw a circle"}, agent_principal=principal)
    task = app.store.get_task(payload["task_id"])

    assert task is not None
    assert task.profile_version == 1
    assert task.effective_request_profile
    assert task.effective_request_profile["output_profile"]["quality_preset"] == app.settings.default_quality_preset


def test_restarted_app_uses_existing_persisted_runtime_definition(tmp_path: Path) -> None:
    app = create_app_context(_build_agent_auth_settings(tmp_path))
    _seed_agent_profile_and_token(app.store)

    restarted = create_app_context(_build_agent_auth_settings(tmp_path))
    runtime_definition = restarted.store.get_agent_runtime_definition("agent-a")

    assert runtime_definition is not None
    assert runtime_definition.agent_id == "agent-a"
    assert runtime_definition.definition_source == "materialized"


def test_authenticate_agent_rejects_missing_runtime_definition_after_restart(tmp_path: Path) -> None:
    settings = _build_agent_auth_settings(tmp_path)
    app = create_app_context(settings)
    _seed_agent_profile_and_token(app.store)
    _delete_runtime_definition(app.store, "agent-a")

    restarted = create_app_context(settings)

    try:
        authenticate_agent_tool(restarted, {"agent_token": "agent-a-secret"})
    except ValueError as exc:
        assert str(exc) == "agent runtime definition not found"
    else:
        raise AssertionError("Expected authenticate_agent_tool to reject missing runtime definition")
