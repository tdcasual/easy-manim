from typing import Any

from fastapi import FastAPI, HTTPException, Request, status

from video_agent.application.agent_profile_suggestion_service import AgentProfileSuggestionService
from video_agent.application.persistent_memory_service import PersistentMemoryError
from video_agent.config import Settings
from video_agent.server.app import create_app_context
from video_agent.server.http_auth import (
    ResolvedAgentSession,
    resolve_agent_session,
)
from video_agent.server.http_api_identity_routes import register_identity_routes
from video_agent.server.http_api_profile_memory_routes import register_profile_memory_routes
from video_agent.server.http_api_task_routes import register_task_routes
from video_agent.server.http_api_video_thread_routes import register_video_thread_routes
from video_agent.server.http_api_support import RECENT_PROFILE_SUGGESTION_LIMIT


def _suggestion_payload(suggestion: Any) -> dict[str, Any]:
    return {
        "suggestion_id": suggestion.suggestion_id,
        "agent_id": suggestion.agent_id,
        "patch": suggestion.patch_json,
        "rationale": suggestion.rationale_json,
        "status": suggestion.status,
        "created_at": suggestion.created_at.isoformat(),
        "applied_at": None if suggestion.applied_at is None else suggestion.applied_at.isoformat(),
    }


def _strategy_profile_payload(profile: Any) -> dict[str, Any]:
    params = profile.params if isinstance(profile.params, dict) else {}
    metrics = profile.metrics if isinstance(profile.metrics, dict) else {}
    routing = params.get("routing") if isinstance(params.get("routing"), dict) else {}
    raw_keywords = routing.get("keywords") if isinstance(routing.get("keywords"), list) else []
    routing_keywords = [str(item) for item in raw_keywords if str(item).strip()]
    guarded_rollout = metrics.get("guarded_rollout") if isinstance(metrics.get("guarded_rollout"), dict) else {}
    last_eval_run = metrics.get("last_eval_run") if isinstance(metrics.get("last_eval_run"), dict) else {}
    return {
        "strategy_id": profile.strategy_id,
        "scope": profile.scope,
        "prompt_cluster": profile.prompt_cluster,
        "status": profile.status,
        "routing_keywords": routing_keywords,
        "params": params,
        "guarded_rollout": guarded_rollout,
        "last_eval_run": last_eval_run,
        "created_at": profile.created_at.isoformat(),
        "updated_at": profile.updated_at.isoformat(),
    }


def create_http_api(settings: Settings) -> FastAPI:
    context = create_app_context(settings)

    def _resolve_optional_agent_session(
        request: Request,
        authorization: str | None,
    ) -> ResolvedAgentSession | None:
        if authorization is None:
            if context.settings.auth_mode == "required":
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_session_token")
            return None
        return resolve_agent_session(request, authorization=authorization)

    def _list_recent_memories(agent_id: str) -> list[Any]:
        return context.store.list_agent_memories(agent_id, include_disabled=False)[-RECENT_PROFILE_SUGGESTION_LIMIT :]

    def _list_recent_session_summaries(agent_id: str) -> list[dict[str, Any]]:
        snapshots = context.session_memory_registry.list_snapshots(agent_id)
        items: list[dict[str, Any]] = []
        for snapshot in reversed(snapshots):
            summary = context.session_memory_service.summarize_session_memory(snapshot.session_id)
            if summary.summary_text:
                items.append({"session_id": summary.session_id, "summary_text": summary.summary_text})
            if len(items) >= RECENT_PROFILE_SUGGESTION_LIMIT:
                break
        items.reverse()
        return items

    def _raise_persistent_memory_http_error(exc: PersistentMemoryError) -> None:
        if exc.code == "agent_memory_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.code) from exc
        if exc.code == "agent_memory_forbidden":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.code) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.code) from exc

    def _require_accessible_session_summary(session_id: str, agent_id: str) -> Any:
        snapshot = context.session_memory_registry.find_snapshot(session_id)
        if snapshot is not None and snapshot.agent_id not in {None, agent_id}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="agent_access_denied")

        session = context.store.get_agent_session_by_id(session_id)
        if session is None and snapshot is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_memory_not_found")
        if session is not None and session.agent_id != agent_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="agent_access_denied")
        return context.session_memory_service.summarize_session_memory(session_id)

    profile_suggestion_service = AgentProfileSuggestionService(
        list_memories=_list_recent_memories,
        list_recent_session_summaries=_list_recent_session_summaries,
        build_scorecard=context.agent_learning_service.build_scorecard,
        create_suggestion=context.store.create_agent_profile_suggestion,
    )
    app = FastAPI(title="easy-manim API", version="0.1.0")
    app.state.app_context = context

    register_identity_routes(app=app, context=context)
    register_profile_memory_routes(
        app=app,
        context=context,
        profile_suggestion_service=profile_suggestion_service,
        suggestion_payload=_suggestion_payload,
        strategy_profile_payload=_strategy_profile_payload,
        require_accessible_session_summary=_require_accessible_session_summary,
        raise_persistent_memory_http_error=_raise_persistent_memory_http_error,
    )
    register_video_thread_routes(
        app=app,
        context=context,
        resolve_optional_agent_session=_resolve_optional_agent_session,
    )
    register_task_routes(app=app, context=context)

    return app
