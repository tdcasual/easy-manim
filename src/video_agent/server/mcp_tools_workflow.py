from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.application.errors import AdmissionControlError
from video_agent.application.persistent_memory_service import PersistentMemoryError
from video_agent.domain.review_workflow_models import ReviewDecision
from video_agent.server.app import AppContext
from video_agent.server.mcp_tools_auth import (
    _authorize_agent_action,
    _error_payload,
    _permission_error_code,
)


def _normalize_review_decision_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    collaboration = normalized.get("collaboration")
    if collaboration is not None and not isinstance(collaboration, dict):
        normalized["collaboration"] = None
    return normalized


def get_review_bundle_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:read")
        result = context.multi_agent_workflow_service.get_review_bundle(
            task_id=payload["task_id"],
            agent_principal=principal,
        )
    except AdmissionControlError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return result.model_dump(mode="json")


def list_workflow_participants_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:read")
        root_task_id, items = context.workflow_collaboration_service.list_workflow_participants(
            payload["task_id"],
            agent_principal=principal,
        )
    except KeyError:
        return _error_payload("task_not_found", "task_not_found")
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return {
        "task_id": payload["task_id"],
        "root_task_id": root_task_id,
        "items": [item.model_dump(mode="json") for item in items],
    }


def upsert_workflow_participant_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:mutate")
        participant = context.workflow_collaboration_service.upsert_workflow_participant(
            payload["task_id"],
            participant_agent_id=payload["agent_id"],
            role=payload["role"],
            capabilities=payload.get("capabilities"),
            agent_principal=principal,
        )
    except KeyError:
        return _error_payload("task_not_found", "task_not_found")
    except ValidationError as exc:
        return _error_payload("invalid_workflow_participant", str(exc))
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return {
        "task_id": payload["task_id"],
        "root_task_id": participant.root_task_id,
        "participant": participant.model_dump(mode="json"),
    }


def remove_workflow_participant_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:mutate")
        root_task_id, removed = context.workflow_collaboration_service.remove_workflow_participant(
            payload["task_id"],
            participant_agent_id=payload["agent_id"],
            agent_principal=principal,
        )
    except KeyError:
        return _error_payload("task_not_found", "task_not_found")
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return {
        "task_id": payload["task_id"],
        "root_task_id": root_task_id,
        "agent_id": payload["agent_id"],
        "removed": removed,
    }


def list_workflow_memory_recommendations_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:read")
        recommendations = context.workflow_collaboration_service.list_workflow_memory_recommendations(
            payload["task_id"],
            limit=payload.get("limit", 5),
            agent_principal=principal,
        )
    except KeyError:
        return _error_payload("task_not_found", "task_not_found")
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return {
        "task_id": payload["task_id"],
        **recommendations.model_dump(mode="json"),
    }


def pin_workflow_memory_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:mutate")
        state = context.workflow_collaboration_service.pin_workflow_memory(
            payload["task_id"],
            memory_id=payload["memory_id"],
            agent_principal=principal,
        )
    except KeyError:
        return _error_payload("task_not_found", "task_not_found")
    except PersistentMemoryError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return {
        "task_id": payload["task_id"],
        **state.model_dump(mode="json"),
    }


def unpin_workflow_memory_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:mutate")
        state = context.workflow_collaboration_service.unpin_workflow_memory(
            payload["task_id"],
            memory_id=payload["memory_id"],
            agent_principal=principal,
        )
    except KeyError:
        return _error_payload("task_not_found", "task_not_found")
    except PersistentMemoryError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return {
        "task_id": payload["task_id"],
        **state.model_dump(mode="json"),
    }


def apply_review_decision_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:read")
        review_decision = ReviewDecision.model_validate(
            _normalize_review_decision_payload(payload["review_decision"])
        )
        result = context.multi_agent_workflow_service.apply_review_decision(
            task_id=payload["task_id"],
            review_decision=review_decision,
            session_id=payload.get("session_id"),
            memory_ids=payload.get("memory_ids"),
            pin_workflow_memory_ids=payload.get("pin_workflow_memory_ids"),
            unpin_workflow_memory_ids=payload.get("unpin_workflow_memory_ids"),
            agent_principal=principal,
        )
    except ValidationError as exc:
        return _error_payload("invalid_review_decision", str(exc))
    except AdmissionControlError as exc:
        return _error_payload(exc.code, str(exc))
    except PersistentMemoryError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return result.model_dump(mode="json")
