import importlib
import importlib.util
from types import SimpleNamespace

import pytest

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.domain.agent_models import AgentProfile, AgentToken


def _load_module(module_name: str):
    spec = importlib.util.find_spec(module_name)
    assert spec is not None
    return importlib.import_module(module_name)


class _DumpableResult:
    def __init__(self, payload):
        self._payload = payload

    def model_dump(self, *, mode: str = "python"):
        return dict(self._payload)


def _principal(agent_id: str = "agent-a") -> AgentPrincipal:
    return AgentPrincipal(
        agent_id=agent_id,
        profile=AgentProfile(agent_id=agent_id, name=agent_id),
        token=AgentToken(token_hash=f"token-{agent_id}", agent_id=agent_id),
    )


def test_permission_error_code_preserves_known_agent_codes_and_normalizes_unknown_values() -> None:
    module = _load_module("video_agent.server.mcp_tools_auth")

    assert module._permission_error_code(PermissionError("agent_not_authenticated")) == "agent_not_authenticated"
    assert module._permission_error_code(PermissionError("agent_scope_denied")) == "agent_scope_denied"
    assert module._permission_error_code(PermissionError("something_else")) == "agent_access_denied"


def test_require_agent_principal_enforces_required_authentication() -> None:
    module = _load_module("video_agent.server.mcp_tools_auth")
    required_context = SimpleNamespace(settings=SimpleNamespace(auth_mode="required"))
    optional_context = SimpleNamespace(settings=SimpleNamespace(auth_mode="none"))

    with pytest.raises(PermissionError, match="agent_not_authenticated"):
        module._require_agent_principal(required_context, None)

    assert module._require_agent_principal(optional_context, None) is None


def test_normalize_review_decision_payload_discards_non_mapping_collaboration() -> None:
    module = _load_module("video_agent.server.mcp_tools_workflow")

    normalized = module._normalize_review_decision_payload(
        {
            "decision": "accept",
            "summary": "Looks good",
            "collaboration": "ignore me",
        }
    )

    assert normalized["decision"] == "accept"
    assert normalized["summary"] == "Looks good"
    assert normalized["collaboration"] is None


def test_create_video_task_tool_maps_permission_errors_to_standard_payload() -> None:
    module = _load_module("video_agent.server.mcp_tools_task")
    context = SimpleNamespace(
        task_service=SimpleNamespace(
            create_video_task=lambda **_: (_ for _ in ()).throw(PermissionError("unexpected_denial"))
        )
    )

    payload = module.create_video_task_tool(context, {"prompt": "draw a circle"})

    assert payload == {
        "error": {
            "code": "agent_access_denied",
            "message": "unexpected_denial",
        }
    }


def test_apply_review_decision_tool_normalizes_collaboration_before_service_call() -> None:
    module = _load_module("video_agent.server.mcp_tools_workflow")
    captured: dict[str, object] = {}

    def _apply_review_decision(**kwargs):
        captured.update(kwargs)
        return _DumpableResult({"task_id": "task-1", "action": "accept"})

    context = SimpleNamespace(
        settings=SimpleNamespace(auth_mode="none"),
        agent_identity_service=SimpleNamespace(require_action=lambda principal, action: None),
        multi_agent_workflow_service=SimpleNamespace(apply_review_decision=_apply_review_decision),
    )

    payload = module.apply_review_decision_tool(
        context,
        {
            "task_id": "task-1",
            "review_decision": {
                "decision": "accept",
                "summary": "Looks good",
                "collaboration": "discard this string",
            },
        },
    )

    assert payload == {"task_id": "task-1", "action": "accept"}
    assert captured["review_decision"].collaboration is None
