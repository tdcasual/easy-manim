from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.application.errors import AdmissionControlError
from video_agent.application.persistent_memory_service import PersistentMemoryError
from video_agent.domain.review_workflow_models import ReviewDecision
from video_agent.server.app import AppContext



def authenticate_agent_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    session_key: str | None = None,
) -> dict[str, Any]:
    principal = context.agent_identity_service.authenticate(payload["agent_token"])
    if session_key is not None:
        context.session_auth.authenticate(session_key, principal)
        context.session_memory_registry.ensure_session(session_key, agent_id=principal.agent_id)
    return {
        "authenticated": True,
        "agent_id": principal.agent_id,
        "name": principal.profile.name,
        "profile": principal.profile.profile_json,
    }


def _error_payload(code: str, message: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": message}}


def _normalize_review_decision_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    collaboration = normalized.get("collaboration")
    if collaboration is not None and not isinstance(collaboration, dict):
        normalized["collaboration"] = None
    return normalized


def _permission_error_code(exc: PermissionError) -> str:
    code = str(exc)
    if code in {"agent_not_authenticated", "agent_access_denied", "agent_scope_denied"}:
        return code
    return "agent_access_denied"


def _require_agent_principal(
    context: AppContext,
    agent_principal: AgentPrincipal | None,
) -> AgentPrincipal | None:
    if context.settings.auth_mode != "required":
        return agent_principal
    if agent_principal is None:
        raise PermissionError("agent_not_authenticated")
    return agent_principal


def _resolve_memory_agent_id(
    context: AppContext,
    agent_principal: AgentPrincipal | None,
) -> str:
    principal = _require_agent_principal(context, agent_principal)
    if principal is None:
        return context.settings.anonymous_agent_id
    return principal.agent_id


def _authorize_agent_action(
    context: AppContext,
    agent_principal: AgentPrincipal | None,
    action: str,
) -> AgentPrincipal | None:
    principal = _require_agent_principal(context, agent_principal)
    if principal is not None:
        context.agent_identity_service.require_action(principal, action)
    return principal


def create_video_task_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        result = context.task_service.create_video_task(
            prompt=payload["prompt"],
            idempotency_key=payload.get("idempotency_key"),
            output_profile=payload.get("output_profile"),
            style_hints=payload.get("style_hints"),
            validation_profile=payload.get("validation_profile"),
            strategy_prompt_cluster=payload.get("strategy_prompt_cluster"),
            feedback=payload.get("feedback"),
            session_id=payload.get("session_id"),
            memory_ids=payload.get("memory_ids"),
            agent_principal=agent_principal,
        )
    except AdmissionControlError as exc:
        return _error_payload(exc.code, str(exc))
    except PersistentMemoryError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return result.model_dump(mode="json")


def get_video_task_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:read")
        if principal is None:
            result = context.task_service.get_video_task(payload["task_id"])
        else:
            result = context.task_service.get_video_task_for_agent(payload["task_id"], principal.agent_id)
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return result.model_dump(mode="json")


def get_failure_contract_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:read")
        failure_contract = (
            context.task_service.get_failure_contract(payload["task_id"])
            if principal is None
            else context.task_service.get_failure_contract_for_agent(payload["task_id"], principal.agent_id)
        )
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return {"task_id": payload["task_id"], "failure_contract": failure_contract}


def get_scene_spec_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:read")
        scene_spec = (
            context.task_service.get_scene_spec(payload["task_id"])
            if principal is None
            else context.task_service.get_scene_spec_for_agent(payload["task_id"], principal.agent_id)
        )
    except KeyError:
        return _error_payload("task_not_found", "task_not_found")
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    if scene_spec is None:
        return _error_payload("scene_spec_not_found", "scene_spec_not_found")
    return {"task_id": payload["task_id"], "scene_spec": scene_spec}


def get_recovery_plan_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:read")
        recovery_plan = (
            context.task_service.get_recovery_plan(payload["task_id"])
            if principal is None
            else context.task_service.get_recovery_plan_for_agent(payload["task_id"], principal.agent_id)
        )
    except KeyError:
        return _error_payload("task_not_found", "task_not_found")
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    if recovery_plan is None:
        return _error_payload("recovery_plan_not_found", "recovery_plan_not_found")
    return {"task_id": payload["task_id"], "recovery_plan": recovery_plan}


def get_quality_score_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:read")
        quality_score = (
            context.task_service.get_quality_score(payload["task_id"])
            if principal is None
            else context.task_service.get_quality_score_for_agent(payload["task_id"], principal.agent_id)
        )
    except KeyError:
        return _error_payload("task_not_found", "task_not_found")
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    if quality_score is None:
        return _error_payload("quality_score_not_found", "quality_score_not_found")
    return {"task_id": payload["task_id"], "quality_score": quality_score}


def list_video_tasks_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:read")
        items = (
            context.task_service.list_video_tasks(
                limit=payload.get("limit", 50),
                status=payload.get("status"),
            )
            if principal is None
            else context.task_service.list_video_tasks_for_agent(
                principal.agent_id,
                limit=payload.get("limit", 50),
                status=payload.get("status"),
            )
        )
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return {"items": items, "next_cursor": None}


def get_task_events_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:read")
        items = (
            context.task_service.get_task_events(
                payload["task_id"],
                limit=payload.get("limit", 200),
            )
            if principal is None
            else context.task_service.get_task_events_for_agent(
                payload["task_id"],
                principal.agent_id,
                limit=payload.get("limit", 200),
            )
        )
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return {"items": items, "next_cursor": None}



def get_metrics_snapshot_tool(context: AppContext, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "counters": dict(context.metrics.counters),
        "timings": {name: list(values) for name, values in context.metrics.timings.items()},
    }



def get_runtime_status_tool(context: AppContext, payload: dict[str, Any]) -> dict[str, Any]:
    return context.runtime_service.inspect().model_dump(mode="json")



def retry_video_task_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        result = context.task_service.retry_video_task(
            payload["task_id"],
            session_id=payload.get("session_id"),
            agent_principal=agent_principal,
        )
    except AdmissionControlError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return result.model_dump(mode="json")


def revise_video_task_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        result = context.task_service.revise_video_task(
            base_task_id=payload["base_task_id"],
            feedback=payload["feedback"],
            preserve_working_parts=payload.get("preserve_working_parts", True),
            session_id=payload.get("session_id"),
            memory_ids=payload.get("memory_ids"),
            agent_principal=agent_principal,
        )
    except AdmissionControlError as exc:
        return _error_payload(exc.code, str(exc))
    except PersistentMemoryError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return result.model_dump(mode="json")


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
            agent_principal=principal,
        )
    except ValidationError as exc:
        return _error_payload("invalid_review_decision", str(exc))
    except AdmissionControlError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return result.model_dump(mode="json")


def cancel_video_task_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        context.task_service.cancel_video_task(payload["task_id"], agent_principal=agent_principal)
    except AdmissionControlError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return {"task_id": payload["task_id"], "status": "cancelled"}


def accept_best_version_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        snapshot = context.task_service.accept_best_version(
            payload["task_id"],
            agent_principal=agent_principal,
        )
    except AdmissionControlError as exc:
        return _error_payload(exc.code, str(exc))
    except KeyError:
        return _error_payload("task_not_found", "task_not_found")
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    except ValueError as exc:
        return _error_payload("invalid_task_state", str(exc))
    return {
        "task_id": snapshot.task_id,
        "accepted_as_best": snapshot.accepted_as_best,
        "accepted_version_rank": snapshot.accepted_version_rank,
    }


def get_video_result_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:read")
        result = (
            context.task_service.get_video_result(payload["task_id"])
            if principal is None
            else context.task_service.get_video_result_for_agent(payload["task_id"], principal.agent_id)
        )
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return result.model_dump(mode="json")


def get_session_memory_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    resolved_session_id = _resolve_session_id(payload, session_id)
    if resolved_session_id is None:
        return _error_payload("session_id_required", "session_id is required")
    try:
        _authorize_agent_action(context, agent_principal, "memory:read")
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))

    snapshot = context.session_memory_service.get_session_memory(resolved_session_id)
    return {
        "session_id": snapshot.session_id,
        "agent_id": snapshot.agent_id,
        "entries": [entry.model_dump(mode="json") for entry in snapshot.entries],
        "entry_count": snapshot.entry_count,
    }


def summarize_session_memory_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    resolved_session_id = _resolve_session_id(payload, session_id)
    if resolved_session_id is None:
        return _error_payload("session_id_required", "session_id is required")
    try:
        _authorize_agent_action(context, agent_principal, "memory:read")
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))

    summary = context.session_memory_service.summarize_session_memory(resolved_session_id)
    return {
        "session_id": summary.session_id,
        "agent_id": summary.agent_id,
        "entries": [entry.model_dump(mode="json") for entry in summary.entries],
        "entry_count": summary.entry_count,
        "lineage_refs": summary.lineage_refs,
        "summary_text": summary.summary_text,
        "summary_digest": summary.summary_digest,
    }


def clear_session_memory_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    resolved_session_id = _resolve_session_id(payload, session_id)
    if resolved_session_id is None:
        return _error_payload("session_id_required", "session_id is required")
    try:
        _authorize_agent_action(context, agent_principal, "memory:clear")
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))

    before = context.session_memory_service.get_session_memory(resolved_session_id)
    snapshot = context.session_memory_service.clear_session_memory(resolved_session_id)
    return {
        "session_id": snapshot.session_id,
        "agent_id": snapshot.agent_id,
        "entries": [entry.model_dump(mode="json") for entry in snapshot.entries],
        "entry_count": snapshot.entry_count,
        "cleared": True,
        "cleared_entry_count": before.entry_count,
        "cleared_attempt_count": sum(len(entry.attempts) for entry in before.entries),
    }


def promote_session_memory_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    resolved_session_id = _resolve_session_id(payload, session_id)
    if resolved_session_id is None:
        return _error_payload("session_id_required", "session_id is required")

    try:
        _authorize_agent_action(context, agent_principal, "memory:promote")
        record = context.persistent_memory_service.promote_session_memory(
            resolved_session_id,
            agent_id=_resolve_memory_agent_id(context, agent_principal),
        )
    except PersistentMemoryError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))

    return record.model_dump(mode="json")


def list_agent_memories_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        _authorize_agent_action(context, agent_principal, "memory:read")
        records = context.persistent_memory_service.list_agent_memories(
            _resolve_memory_agent_id(context, agent_principal),
            include_disabled=payload.get("include_disabled", False),
        )
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))

    return {"items": [record.model_dump(mode="json") for record in records]}


def get_agent_memory_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        _authorize_agent_action(context, agent_principal, "memory:read")
        record = context.persistent_memory_service.get_agent_memory(
            payload["memory_id"],
            agent_id=_resolve_memory_agent_id(context, agent_principal),
        )
    except PersistentMemoryError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))

    return record.model_dump(mode="json")


def disable_agent_memory_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        _authorize_agent_action(context, agent_principal, "memory:write")
        record = context.persistent_memory_service.disable_agent_memory(
            payload["memory_id"],
            agent_id=_resolve_memory_agent_id(context, agent_principal),
        )
    except PersistentMemoryError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))

    return record.model_dump(mode="json")


def query_agent_memories_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        _authorize_agent_action(context, agent_principal, "memory:read")
        items = context.persistent_memory_service.query_agent_memories(
            _resolve_memory_agent_id(context, agent_principal),
            query=payload.get("query", ""),
            limit=payload.get("limit", 5),
        )
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))

    return {"items": [item.model_dump(mode="json") for item in items]}


def _resolve_session_id(payload: dict[str, Any], session_id: str | None) -> str | None:
    return session_id or payload.get("session_id")
