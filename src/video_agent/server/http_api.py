from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.application.agent_profile_suggestion_service import AgentProfileSuggestionService
from video_agent.application.errors import AdmissionControlError
from video_agent.application.persistent_memory_service import PersistentMemoryError
from video_agent.config import Settings
from video_agent.server.app import create_app_context
from video_agent.server.http_auth import (
    ResolvedAgentSession,
    current_internal_session_id,
    resolve_agent_session,
)
from video_agent.server.mcp_resources import guess_mime_type, resolve_resource_path
from video_agent.server.mcp_tools import (
    accept_best_version_tool,
    apply_review_decision_tool,
    append_video_turn_tool,
    cancel_video_task_tool,
    clear_session_memory_tool,
    create_video_thread_tool,
    create_video_task_tool,
    disable_agent_memory_tool,
    get_agent_memory_tool,
    get_quality_score_tool,
    get_recovery_plan_tool,
    get_review_bundle_tool,
    get_scene_spec_tool,
    get_session_memory_tool,
    get_video_result_tool,
    get_video_thread_surface_tool,
    get_video_task_tool,
    list_agent_memories_tool,
    list_video_thread_participants_tool,
    list_video_tasks_tool,
    list_workflow_memory_recommendations_tool,
    list_workflow_participants_tool,
    pin_workflow_memory_tool,
    promote_session_memory_tool,
    query_agent_memories_tool,
    remove_video_thread_participant_tool,
    remove_workflow_participant_tool,
    request_video_explanation_tool,
    request_video_revision_tool,
    retry_video_task_tool,
    revise_video_task_tool,
    select_video_result_tool,
    summarize_session_memory_tool,
    unpin_workflow_memory_tool,
    upsert_video_thread_participant_tool,
    upsert_workflow_participant_tool,
)


class SessionLoginRequest(BaseModel):
    agent_token: str


class CreateTaskRequest(BaseModel):
    prompt: str
    idempotency_key: str | None = None
    output_profile: dict[str, Any] | None = None
    style_hints: dict[str, Any] | None = None
    validation_profile: dict[str, Any] | None = None
    strategy_prompt_cluster: str | None = None
    memory_ids: list[str] | None = None


class ReviseTaskRequest(BaseModel):
    feedback: str
    preserve_working_parts: bool = True
    memory_ids: list[str] | None = None


class CreateVideoThreadRequest(BaseModel):
    title: str
    prompt: str
    owner_agent_id: str | None = None
    memory_ids: list[str] | None = None


class RequestVideoThreadRevisionRequest(BaseModel):
    summary: str
    preserve_working_parts: bool = True
    memory_ids: list[str] | None = None


class AppendVideoTurnRequest(BaseModel):
    iteration_id: str
    title: str
    summary: str = ""
    addressed_participant_id: str | None = None
    reply_to_turn_id: str | None = None
    related_result_id: str | None = None


class RequestVideoExplanationRequest(BaseModel):
    summary: str


class SelectVideoResultRequest(BaseModel):
    result_id: str


class VideoThreadParticipantUpsertRequest(BaseModel):
    participant_id: str
    participant_type: str
    agent_id: str | None = None
    role: str
    display_name: str
    capabilities: list[str] | None = None


class ProfileApplyRequest(BaseModel):
    patch: dict[str, Any]


class ReviewDecisionRequest(BaseModel):
    decision: str
    summary: str
    decision_role: str | None = None
    preserve_working_parts: bool = True
    confidence: float = 0.0
    issues: list[dict[str, Any]] = Field(default_factory=list)
    feedback: str | None = None
    stop_reason: str | None = None
    collaboration: dict[str, Any] | None = None


class ApplyReviewDecisionRequest(BaseModel):
    review_decision: ReviewDecisionRequest
    memory_ids: list[str] | None = None
    pin_workflow_memory_ids: list[str] | None = None
    unpin_workflow_memory_ids: list[str] | None = None


class WorkflowParticipantUpsertRequest(BaseModel):
    agent_id: str
    role: str
    capabilities: list[str] | None = None


class WorkflowMemoryPinRequest(BaseModel):
    memory_id: str


class PreferenceProposalRequest(BaseModel):
    summary_text: str
    session_id: str | None = None


class PreferencePromotionRequest(BaseModel):
    session_id: str | None = None
    memory_id: str | None = None


class MemoryRetrievalRequest(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=20)


_PROFILE_PATCH_ALLOWLIST = frozenset({"style_hints", "output_profile", "validation_profile"})
_RECENT_PROFILE_SUGGESTION_LIMIT = 5
_AUTO_APPLY_MIN_SUGGESTION_CONFIDENCE = 0.8
_LEGACY_DISCUSSION_TRANSPORT_REMOVED = "legacy_discussion_transport_removed"


def _validate_profile_patch_shape(patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if key in _PROFILE_PATCH_ALLOWLIST and not isinstance(value, dict):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="invalid_profile_patch_shape")


def _tool_payload_or_http_error(payload: dict[str, Any]) -> dict[str, Any]:
    error = payload.get("error")
    if error is None:
        return payload

    code = error.get("code", "bad_request")
    if code == "agent_not_authenticated":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=code)
    if code in {"agent_access_denied", "agent_memory_forbidden", "agent_scope_denied"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=code)
    if code in {
        "agent_memory_not_found",
        "task_not_found",
        "scene_spec_not_found",
        "recovery_plan_not_found",
        "quality_score_not_found",
    }:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=code)
    if code == "invalid_task_state":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=code)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code)


def _permission_error_code(exc: PermissionError) -> str:
    code = str(exc)
    if code in {"agent_not_authenticated", "agent_access_denied", "agent_scope_denied"}:
        return code
    return "agent_access_denied"


def _permission_http_error(exc: PermissionError) -> HTTPException:
    code = _permission_error_code(exc)
    if code == "agent_not_authenticated":
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=code)
    if code in {"agent_access_denied", "agent_memory_forbidden", "agent_scope_denied"}:
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=code)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code)


def _allowed_task_artifact_resource_uri(task_id: str, artifact_path: str) -> str:
    normalized = Path(artifact_path)
    if normalized.is_absolute() or ".." in normalized.parts or artifact_path.strip() == "":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource_not_found")

    allowed_prefixes = ("previews/",)
    allowed_names = {
        "final_video.mp4",
        "current_script.py",
        "scene_plan.json",
        "failure_context.json",
        "failure_contract.json",
    }
    path_text = normalized.as_posix()

    if path_text.startswith(allowed_prefixes) or path_text in allowed_names:
        return f"video-task://{task_id}/artifacts/{path_text}"
    if path_text.startswith("validations/") or path_text.startswith("logs/"):
        return f"video-task://{task_id}/{path_text}"
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource_not_found")


def _download_url_from_resource_uri(resource_uri: str | None) -> str | None:
    if resource_uri is None:
        return None
    prefix = "video-task://"
    if not str(resource_uri).startswith(prefix):
        return None
    task_and_path = str(resource_uri)[len(prefix) :]
    task_id, separator, relative_path = task_and_path.partition("/")
    if not separator or not task_id or not relative_path:
        return None
    if relative_path.startswith("artifacts/"):
        relative_path = relative_path.removeprefix("artifacts/")
    return f"/api/tasks/{task_id}/artifacts/{relative_path}"


def _strip_internal_session_fields(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(payload)
    sanitized.pop("session_id", None)
    sanitized.pop("source_session_id", None)

    items = sanitized.get("items")
    if isinstance(items, list):
        sanitized["items"] = [
            _strip_internal_session_fields(item) if isinstance(item, dict) else item
            for item in items
        ]
    return sanitized


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
        return context.store.list_agent_memories(agent_id, include_disabled=False)[-_RECENT_PROFILE_SUGGESTION_LIMIT :]

    def _list_recent_session_summaries(agent_id: str) -> list[dict[str, Any]]:
        snapshots = context.session_memory_registry.list_snapshots(agent_id)
        items: list[dict[str, Any]] = []
        for snapshot in reversed(snapshots):
            summary = context.session_memory_service.summarize_session_memory(snapshot.session_id)
            if summary.summary_text:
                items.append({"session_id": summary.session_id, "summary_text": summary.summary_text})
            if len(items) >= _RECENT_PROFILE_SUGGESTION_LIMIT:
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

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        return {"status": "ready"}

    @app.get("/api/runtime/status")
    def runtime_status(
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        if context.settings.auth_mode == "required":
            resolved = resolve_agent_session(request, authorization=authorization)
            try:
                context.agent_identity_service.require_action(resolved.agent_principal, "task:read")
            except PermissionError as exc:
                raise _permission_http_error(exc) from exc
        return context.runtime_service.inspect().model_dump(mode="json")

    @app.post("/api/sessions")
    def create_session(payload: SessionLoginRequest) -> dict[str, object]:
        try:
            created = context.agent_session_service.create_session(payload.agent_token)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_agent_token") from exc

        context.session_auth.authenticate(
            created.session.session_id,
            AgentPrincipal(
                agent_id=created.profile.agent_id,
                profile=created.profile,
                token=created.token,
            ),
        )
        context.session_memory_registry.ensure_session(
            created.session.session_id,
            agent_id=created.profile.agent_id,
        )
        return {
            "session_token": created.session_token,
            "agent_id": created.profile.agent_id,
            "name": created.profile.name,
            "expires_at": created.session.expires_at.isoformat(),
        }

    @app.get("/api/whoami")
    def whoami(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, object]:
        try:
            context.agent_identity_service.require_action(resolved.agent_principal, "profile:read")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        return {
            "agent_id": resolved.agent_principal.agent_id,
            "name": resolved.agent_principal.profile.name,
            "profile": resolved.agent_principal.profile.profile_json,
        }

    @app.delete("/api/sessions/current")
    def delete_session(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, bool]:
        context.agent_session_service.revoke_session(resolved.session_token)
        return {"revoked": True}

    @app.get("/api/profile")
    def get_profile(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, object]:
        try:
            context.agent_identity_service.require_action(resolved.agent_principal, "profile:read")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

        profile = context.store.get_agent_profile(resolved.agent_principal.agent_id)
        if profile is None or profile.status != "active":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session_token")

        return {
            "agent_id": profile.agent_id,
            "name": profile.name,
            "status": profile.status,
            "profile_version": profile.profile_version,
            # Keep the API aligned with UI typings.
            "profile_json": profile.profile_json,
            "policy_json": profile.policy_json,
            "created_at": profile.created_at.isoformat(),
            "updated_at": profile.updated_at.isoformat(),
            # Backward-compatible aliases (older clients).
            "profile": profile.profile_json,
            "policy": profile.policy_json,
        }

    @app.get("/api/profile/scorecard")
    def profile_scorecard(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, object]:
        try:
            context.agent_identity_service.require_action(resolved.agent_principal, "profile:read")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        return context.agent_learning_service.build_scorecard(resolved.agent_principal.agent_id)

    @app.get("/api/profile/strategies")
    def list_profile_strategies(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        try:
            context.agent_identity_service.require_action(resolved.agent_principal, "profile:read")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        items = [_strategy_profile_payload(profile) for profile in context.store.list_strategy_profiles()]
        status_rank = {"active": 0, "candidate": 1, "superseded": 2, "rolled_back": 3}
        items.sort(
            key=lambda item: (
                status_rank.get(str(item.get("status") or ""), 9),
                str(item.get("updated_at") or ""),
            ),
            reverse=False,
        )
        active = [item for item in items if item.get("status") == "active"]
        rest = [item for item in items if item.get("status") != "active"]
        rest.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
        return {"items": [*active, *rest]}

    @app.get("/api/profile/evals")
    def list_profile_evals(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        try:
            context.agent_identity_service.require_action(resolved.agent_principal, "profile:read")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        return {"items": context.artifact_store.list_eval_summaries()}

    @app.get("/api/profile/evals/{run_id}")
    def get_profile_eval(run_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        try:
            context.agent_identity_service.require_action(resolved.agent_principal, "profile:read")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        payload = context.artifact_store.read_eval_summary(run_id)
        if payload is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="eval_run_not_found")
        return payload

    @app.get("/api/profile/strategy-decisions")
    def list_strategy_decisions(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        try:
            context.agent_identity_service.require_action(resolved.agent_principal, "profile:read")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        items: list[dict[str, Any]] = []
        for profile in context.store.list_strategy_profiles():
            for item in profile.metrics.get("decision_timeline", []) or []:
                if not isinstance(item, dict):
                    continue
                items.append(item)
        items.sort(key=lambda item: str(item.get("recorded_at") or ""), reverse=True)
        return {"items": items}

    @app.post("/api/profile/apply")
    def apply_profile_patch(
        payload: ProfileApplyRequest,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, object]:
        try:
            context.agent_identity_service.require_action(resolved.agent_principal, "profile:write")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

        unsupported_keys = sorted(set(payload.patch) - _PROFILE_PATCH_ALLOWLIST)
        if unsupported_keys:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="unsupported_profile_patch_keys")
        _validate_profile_patch_shape(payload.patch)

        current_profile = context.store.get_agent_profile(resolved.agent_principal.agent_id)
        if current_profile is None or current_profile.status != "active":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session_token")

        try:
            updated_profile, revision = context.store.apply_agent_profile_patch(
                current_profile.agent_id,
                patch_json=payload.patch,
                source="http.profile.apply",
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session_token") from exc

        return {
            "applied": True,
            "revision_id": revision.revision_id,
            "agent_id": updated_profile.agent_id,
            "profile_version": updated_profile.profile_version,
            "profile": updated_profile.profile_json,
        }

    @app.post("/api/profile/preferences/propose")
    def propose_profile_preferences(
        payload: PreferenceProposalRequest,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        try:
            context.agent_identity_service.require_action(resolved.agent_principal, "profile:write")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

        if payload.session_id is not None:
            _require_accessible_session_summary(payload.session_id, resolved.agent_principal.agent_id)
        suggestion = profile_suggestion_service.create_suggestion_from_summary(
            resolved.agent_principal.agent_id,
            summary_text=payload.summary_text,
            session_id=payload.session_id,
            profile_version=resolved.agent_principal.profile.profile_version,
            source="preference_proposal",
        )
        if suggestion is None:
            return {"created": False, "reason": "no_supported_preference"}
        return {"created": True, "suggestion": _suggestion_payload(suggestion)}

    @app.post("/api/profile/preferences/promote")
    def promote_profile_preferences(
        payload: PreferencePromotionRequest,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        try:
            context.agent_identity_service.require_action(resolved.agent_principal, "profile:write")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

        summary_text: str | None = None
        session_id: str | None = payload.session_id
        memory_id: str | None = payload.memory_id
        source = "preference_promotion"
        if memory_id is not None:
            try:
                record = context.persistent_memory_service.get_agent_memory(
                    memory_id,
                    agent_id=resolved.agent_principal.agent_id,
                )
            except PersistentMemoryError as exc:
                _raise_persistent_memory_http_error(exc)
            summary_text = record.summary_text
            session_id = record.source_session_id
            source = "memory_promotion"
        elif session_id is not None:
            summary = _require_accessible_session_summary(
                session_id,
                resolved.agent_principal.agent_id,
            )
            summary_text = summary.summary_text
            source = "session_promotion"
        else:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="missing_preference_source")

        suggestion = profile_suggestion_service.create_suggestion_from_summary(
            resolved.agent_principal.agent_id,
            summary_text=summary_text or "",
            session_id=session_id,
            memory_id=memory_id,
            profile_version=resolved.agent_principal.profile.profile_version,
            source=source,
        )
        if suggestion is None:
            return {"created": False, "reason": "no_supported_preference"}
        return {"created": True, "suggestion": _suggestion_payload(suggestion)}

    @app.post("/api/profile/suggestions/generate")
    def generate_profile_suggestions(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        try:
            context.agent_identity_service.require_action(resolved.agent_principal, "profile:write")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        items = profile_suggestion_service.generate_suggestions(
            resolved.agent_principal.agent_id,
            profile_version=resolved.agent_principal.profile.profile_version,
        )
        if not items:
            return {"items": []}

        # Optional: automatically apply safe suggestions once an agent has
        # enough successful history (guarded by settings).
        if context.settings.agent_learning_auto_apply_enabled:
            scorecard = context.agent_learning_service.build_scorecard(resolved.agent_principal.agent_id)
            completed_count = int(scorecard.get("completed_count", 0) or 0)
            failed_count = int(scorecard.get("failed_count", 0) or 0)
            median_quality_score = float(scorecard.get("median_quality_score", 0.0) or 0.0)

            eligible = (
                completed_count >= context.settings.agent_learning_auto_apply_min_completed_tasks
                and failed_count <= context.settings.agent_learning_auto_apply_max_recent_failures
                and median_quality_score >= context.settings.agent_learning_auto_apply_min_quality_score
            )
            if eligible:
                applied: list[Any] = []
                for suggestion in items:
                    if not suggestion.is_safe_for_auto_apply(
                        min_confidence=_AUTO_APPLY_MIN_SUGGESTION_CONFIDENCE,
                    ):
                        applied.append(suggestion)
                        continue
                    unsupported_keys = sorted(set(suggestion.patch_json) - _PROFILE_PATCH_ALLOWLIST)
                    if unsupported_keys:
                        applied.append(suggestion)
                        continue
                    try:
                        _validate_profile_patch_shape(suggestion.patch_json)
                    except HTTPException:
                        applied.append(suggestion)
                        continue

                    try:
                        _, _, updated_suggestion = context.store.apply_agent_profile_suggestion(
                            resolved.agent_principal.agent_id,
                            suggestion_id=suggestion.suggestion_id,
                            source=f"auto_apply:{suggestion.suggestion_id}",
                        )
                    except Exception:
                        applied.append(suggestion)
                        continue
                    applied.append(updated_suggestion or suggestion)
                items = applied

        return {"items": [_suggestion_payload(item) for item in items]}

    @app.get("/api/profile/suggestions")
    def list_profile_suggestions(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        try:
            context.agent_identity_service.require_action(resolved.agent_principal, "profile:read")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        items = context.store.list_agent_profile_suggestions(resolved.agent_principal.agent_id)
        return {"items": [_suggestion_payload(item) for item in items]}

    @app.post("/api/profile/suggestions/{suggestion_id}/apply")
    def apply_profile_suggestion(
        suggestion_id: str,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        try:
            context.agent_identity_service.require_action(resolved.agent_principal, "profile:write")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

        suggestion = context.store.get_agent_profile_suggestion(suggestion_id)
        if suggestion is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile_suggestion_not_found")
        if suggestion.agent_id != resolved.agent_principal.agent_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="agent_access_denied")
        if suggestion.status != "pending":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="profile_suggestion_state_conflict")

        unsupported_keys = sorted(set(suggestion.patch_json) - _PROFILE_PATCH_ALLOWLIST)
        if unsupported_keys:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="unsupported_profile_patch_keys")
        _validate_profile_patch_shape(suggestion.patch_json)

        try:
            updated_profile, revision, updated_suggestion = context.store.apply_agent_profile_suggestion(
                resolved.agent_principal.agent_id,
                suggestion_id=suggestion.suggestion_id,
                source=f"profile_suggestion:{suggestion.suggestion_id}",
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="profile_suggestion_state_conflict")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except ValueError as exc:
            if str(exc) == "profile suggestion not found":
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile_suggestion_not_found") from exc
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session_token") from exc
        return {
            "applied": True,
            "revision_id": revision.revision_id,
            "profile_version": updated_profile.profile_version,
            "profile": updated_profile.profile_json,
            "suggestion": None if updated_suggestion is None else _suggestion_payload(updated_suggestion),
        }

    @app.post("/api/profile/suggestions/{suggestion_id}/dismiss")
    def dismiss_profile_suggestion(
        suggestion_id: str,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        try:
            context.agent_identity_service.require_action(resolved.agent_principal, "profile:write")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

        suggestion = context.store.get_agent_profile_suggestion(suggestion_id)
        if suggestion is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile_suggestion_not_found")
        if suggestion.agent_id != resolved.agent_principal.agent_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="agent_access_denied")
        if suggestion.status != "pending":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="profile_suggestion_state_conflict")

        updated_suggestion = context.store.update_agent_profile_suggestion_status(
            suggestion.suggestion_id,
            status="dismissed",
            expected_status="pending",
        )
        if updated_suggestion is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="profile_suggestion_state_conflict")
        return _suggestion_payload(updated_suggestion)

    @app.get("/api/memory/session")
    def get_session_memory(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, object]:
        return _strip_internal_session_fields(
            get_session_memory_tool(
                context,
                {},
                agent_principal=resolved.agent_principal,
                session_id=current_internal_session_id(resolved),
            )
        )

    @app.get("/api/memory/session/summary")
    def summarize_session_memory(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        return _strip_internal_session_fields(
            _tool_payload_or_http_error(
                summarize_session_memory_tool(
                    context,
                    {},
                    agent_principal=resolved.agent_principal,
                    session_id=current_internal_session_id(resolved),
                )
            )
        )

    @app.delete("/api/memory/session")
    def clear_session_memory(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        return _strip_internal_session_fields(
            _tool_payload_or_http_error(
                clear_session_memory_tool(
                    context,
                    {},
                    agent_principal=resolved.agent_principal,
                    session_id=current_internal_session_id(resolved),
                )
            )
        )

    @app.post("/api/memories/promote")
    def promote_session_memory(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        return _strip_internal_session_fields(
            _tool_payload_or_http_error(
                promote_session_memory_tool(
                    context,
                    {},
                    agent_principal=resolved.agent_principal,
                    session_id=current_internal_session_id(resolved),
                )
            )
        )

    @app.get("/api/memories")
    def list_memories(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        return _strip_internal_session_fields(
            _tool_payload_or_http_error(
                list_agent_memories_tool(
                    context,
                    {},
                    agent_principal=resolved.agent_principal,
                )
            )
        )

    @app.post("/api/memories/retrieve")
    def retrieve_memories(
        payload: MemoryRetrievalRequest,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return _strip_internal_session_fields(
            _tool_payload_or_http_error(
                query_agent_memories_tool(
                    context,
                    {"query": payload.query, "limit": payload.limit},
                    agent_principal=resolved.agent_principal,
                )
            )
        )

    @app.get("/api/memories/{memory_id}")
    def get_memory(memory_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        return _strip_internal_session_fields(
            _tool_payload_or_http_error(
                get_agent_memory_tool(
                    context,
                    {"memory_id": memory_id},
                    agent_principal=resolved.agent_principal,
                )
            )
        )

    @app.post("/api/memories/{memory_id}/disable")
    def disable_memory(memory_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        return _strip_internal_session_fields(
            _tool_payload_or_http_error(
                disable_agent_memory_tool(
                    context,
                    {"memory_id": memory_id},
                    agent_principal=resolved.agent_principal,
                )
            )
        )

    @app.post("/api/tasks")
    def create_task(
        payload: CreateTaskRequest,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return _tool_payload_or_http_error(
            create_video_task_tool(
                context,
                {
                    "prompt": payload.prompt,
                    "idempotency_key": payload.idempotency_key,
                    "output_profile": payload.output_profile,
                    "style_hints": payload.style_hints,
                    "validation_profile": payload.validation_profile,
                    "strategy_prompt_cluster": payload.strategy_prompt_cluster,
                    "memory_ids": payload.memory_ids,
                    "session_id": current_internal_session_id(resolved),
                },
                agent_principal=resolved.agent_principal,
            )
        )

    @app.post("/api/video-threads")
    def create_video_thread(
        payload: CreateVideoThreadRequest,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resolved = _resolve_optional_agent_session(request, authorization)
        principal = None if resolved is None else resolved.agent_principal
        owner_agent_id = (
            payload.owner_agent_id
            or (None if principal is None else principal.agent_id)
            or context.settings.anonymous_agent_id
        )
        return _tool_payload_or_http_error(
            create_video_thread_tool(
                context,
                {
                    "owner_agent_id": owner_agent_id,
                    "title": payload.title,
                    "prompt": payload.prompt,
                    "memory_ids": payload.memory_ids,
                    "session_id": None if resolved is None else current_internal_session_id(resolved),
                },
                agent_principal=principal,
            )
        )

    @app.get("/api/video-threads/{thread_id}")
    def get_video_thread(
        thread_id: str,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resolved = _resolve_optional_agent_session(request, authorization)
        try:
            if resolved is not None and resolved.agent_principal is not None:
                context.agent_identity_service.require_action(resolved.agent_principal, "task:read")
            thread = context.video_thread_service.load_thread(thread_id)
        except PermissionError as exc:
            raise _permission_http_error(exc) from exc
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="thread_not_found") from exc
        return thread.model_dump(mode="json")

    @app.get("/api/video-threads/{thread_id}/surface")
    def get_video_thread_surface(
        thread_id: str,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resolved = _resolve_optional_agent_session(request, authorization)
        return _tool_payload_or_http_error(
            get_video_thread_surface_tool(
                context,
                {"thread_id": thread_id},
                agent_principal=None if resolved is None else resolved.agent_principal,
            )
        )

    @app.get("/api/video-threads/{thread_id}/iterations/{iteration_id}")
    def get_video_thread_iteration(
        thread_id: str,
        iteration_id: str,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resolved = _resolve_optional_agent_session(request, authorization)
        try:
            if resolved is not None and resolved.agent_principal is not None:
                context.agent_identity_service.require_action(resolved.agent_principal, "task:read")
            return context.video_projection_service.build_iteration_payload(thread_id, iteration_id)
        except PermissionError as exc:
            raise _permission_http_error(exc) from exc
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="iteration_not_found") from exc

    @app.post("/api/video-threads/{thread_id}/turns")
    def append_video_thread_turn(
        thread_id: str,
        payload: AppendVideoTurnRequest,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resolved = _resolve_optional_agent_session(request, authorization)
        return _tool_payload_or_http_error(
            append_video_turn_tool(
                context,
                {
                    "thread_id": thread_id,
                    "iteration_id": payload.iteration_id,
                    "title": payload.title,
                    "summary": payload.summary,
                    "addressed_participant_id": payload.addressed_participant_id,
                    "reply_to_turn_id": payload.reply_to_turn_id,
                    "related_result_id": payload.related_result_id,
                },
                agent_principal=None if resolved is None else resolved.agent_principal,
            )
        )

    @app.post("/api/video-threads/{thread_id}/iterations/{iteration_id}/request-revision")
    def request_video_thread_revision(
        thread_id: str,
        iteration_id: str,
        payload: RequestVideoThreadRevisionRequest,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resolved = _resolve_optional_agent_session(request, authorization)
        return _tool_payload_or_http_error(
            request_video_revision_tool(
                context,
                {
                    "thread_id": thread_id,
                    "iteration_id": iteration_id,
                    "summary": payload.summary,
                    "preserve_working_parts": payload.preserve_working_parts,
                    "memory_ids": payload.memory_ids,
                    "session_id": None if resolved is None else current_internal_session_id(resolved),
                },
                agent_principal=None if resolved is None else resolved.agent_principal,
            )
        )

    @app.post("/api/video-threads/{thread_id}/iterations/{iteration_id}/request-explanation")
    def request_video_thread_explanation(
        thread_id: str,
        iteration_id: str,
        payload: RequestVideoExplanationRequest,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resolved = _resolve_optional_agent_session(request, authorization)
        return _tool_payload_or_http_error(
            request_video_explanation_tool(
                context,
                {
                    "thread_id": thread_id,
                    "iteration_id": iteration_id,
                    "summary": payload.summary,
                },
                agent_principal=None if resolved is None else resolved.agent_principal,
            )
        )

    @app.post("/api/video-threads/{thread_id}/iterations/{iteration_id}/select-result")
    def select_video_thread_result(
        thread_id: str,
        iteration_id: str,
        payload: SelectVideoResultRequest,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resolved = _resolve_optional_agent_session(request, authorization)
        return _tool_payload_or_http_error(
            select_video_result_tool(
                context,
                {
                    "thread_id": thread_id,
                    "iteration_id": iteration_id,
                    "result_id": payload.result_id,
                },
                agent_principal=None if resolved is None else resolved.agent_principal,
            )
        )

    @app.get("/api/video-threads/{thread_id}/participants")
    def list_video_thread_participants(
        thread_id: str,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resolved = _resolve_optional_agent_session(request, authorization)
        return _tool_payload_or_http_error(
            list_video_thread_participants_tool(
                context,
                {"thread_id": thread_id},
                agent_principal=None if resolved is None else resolved.agent_principal,
            )
        )

    @app.post("/api/video-threads/{thread_id}/participants")
    def upsert_video_thread_participant(
        thread_id: str,
        payload: VideoThreadParticipantUpsertRequest,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resolved = _resolve_optional_agent_session(request, authorization)
        return _tool_payload_or_http_error(
            upsert_video_thread_participant_tool(
                context,
                {
                    "thread_id": thread_id,
                    "participant_id": payload.participant_id,
                    "participant_type": payload.participant_type,
                    "agent_id": payload.agent_id,
                    "role": payload.role,
                    "display_name": payload.display_name,
                    "capabilities": payload.capabilities,
                },
                agent_principal=None if resolved is None else resolved.agent_principal,
            )
        )

    @app.delete("/api/video-threads/{thread_id}/participants/{participant_id}")
    def remove_video_thread_participant(
        thread_id: str,
        participant_id: str,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resolved = _resolve_optional_agent_session(request, authorization)
        return _tool_payload_or_http_error(
            remove_video_thread_participant_tool(
                context,
                {
                    "thread_id": thread_id,
                    "participant_id": participant_id,
                },
                agent_principal=None if resolved is None else resolved.agent_principal,
            )
        )

    @app.get("/api/tasks")
    def list_tasks(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        return _tool_payload_or_http_error(
            list_video_tasks_tool(
                context,
                {},
                agent_principal=resolved.agent_principal,
            )
        )

    @app.get("/api/tasks/{task_id}")
    def get_task(task_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        return _tool_payload_or_http_error(
            get_video_task_tool(
                context,
                {"task_id": task_id},
                agent_principal=resolved.agent_principal,
            )
        )

    @app.get("/api/tasks/{task_id}/scene-spec")
    def get_task_scene_spec(task_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        payload = _tool_payload_or_http_error(
            get_scene_spec_tool(
                context,
                {"task_id": task_id},
                agent_principal=resolved.agent_principal,
            )
        )
        return payload["scene_spec"]

    @app.get("/api/tasks/{task_id}/recovery-plan")
    def get_task_recovery_plan(task_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        payload = _tool_payload_or_http_error(
            get_recovery_plan_tool(
                context,
                {"task_id": task_id},
                agent_principal=resolved.agent_principal,
            )
        )
        return payload["recovery_plan"]

    @app.get("/api/tasks/{task_id}/quality-score")
    def get_task_quality_score(task_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        payload = _tool_payload_or_http_error(
            get_quality_score_tool(
                context,
                {"task_id": task_id},
                agent_principal=resolved.agent_principal,
            )
        )
        return payload["quality_score"]

    @app.get("/api/tasks/{task_id}/result")
    def get_task_result(task_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        try:
            payload = _tool_payload_or_http_error(
                get_video_result_tool(
                    context,
                    {"task_id": task_id},
                    agent_principal=resolved.agent_principal,
                )
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task_not_found") from exc

        video_download_url = _download_url_from_resource_uri(payload.get("video_resource"))
        if video_download_url is not None:
            payload["video_download_url"] = video_download_url

        preview_resources = payload.get("preview_frame_resources") or []
        preview_urls: list[str] = []
        if preview_resources:
            for uri in preview_resources:
                download_url = _download_url_from_resource_uri(str(uri))
                if download_url is not None:
                    preview_urls.append(download_url)
        if preview_urls:
            payload["preview_download_urls"] = preview_urls

        script_download_url = _download_url_from_resource_uri(payload.get("script_resource"))
        if script_download_url is not None:
            payload["script_download_url"] = script_download_url

        if payload.get("validation_report_resource"):
            validation_report_download_url = _download_url_from_resource_uri(payload["validation_report_resource"])
            if validation_report_download_url is not None:
                payload["validation_report_download_url"] = validation_report_download_url
        return payload

    @app.get("/api/tasks/{task_id}/review-bundle")
    def get_task_review_bundle(
        task_id: str,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return _strip_internal_session_fields(
            _tool_payload_or_http_error(
                get_review_bundle_tool(
                    context,
                    {"task_id": task_id},
                    agent_principal=resolved.agent_principal,
                )
            )
        )

    @app.get("/api/tasks/{task_id}/discussion-thread")
    def get_task_discussion_thread(
        task_id: str,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        _ = (task_id, resolved)
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=_LEGACY_DISCUSSION_TRANSPORT_REMOVED,
        )

    @app.post("/api/tasks/{task_id}/review-decision")
    def apply_task_review_decision(
        task_id: str,
        payload: ApplyReviewDecisionRequest,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return _strip_internal_session_fields(
            _tool_payload_or_http_error(
                apply_review_decision_tool(
                    context,
                    {
                        "task_id": task_id,
                        "review_decision": payload.review_decision.model_dump(mode="json"),
                        "memory_ids": payload.memory_ids,
                        "pin_workflow_memory_ids": payload.pin_workflow_memory_ids,
                        "unpin_workflow_memory_ids": payload.unpin_workflow_memory_ids,
                        "session_id": current_internal_session_id(resolved),
                    },
                    agent_principal=resolved.agent_principal,
                )
            )
        )

    @app.post("/api/tasks/{task_id}/discussion-messages")
    def create_task_discussion_message(
        task_id: str,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        _ = (task_id, resolved)
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=_LEGACY_DISCUSSION_TRANSPORT_REMOVED,
        )

    @app.get("/api/tasks/{task_id}/workflow-participants")
    def list_task_workflow_participants(
        task_id: str,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return _tool_payload_or_http_error(
            list_workflow_participants_tool(
                context,
                {"task_id": task_id},
                agent_principal=resolved.agent_principal,
            )
        )

    @app.post("/api/tasks/{task_id}/workflow-participants")
    def upsert_task_workflow_participant(
        task_id: str,
        payload: WorkflowParticipantUpsertRequest,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return _tool_payload_or_http_error(
            upsert_workflow_participant_tool(
                context,
                {
                    "task_id": task_id,
                    "agent_id": payload.agent_id,
                    "role": payload.role,
                    "capabilities": payload.capabilities,
                },
                agent_principal=resolved.agent_principal,
            )
        )

    @app.delete("/api/tasks/{task_id}/workflow-participants/{agent_id}")
    def remove_task_workflow_participant(
        task_id: str,
        agent_id: str,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return _tool_payload_or_http_error(
            remove_workflow_participant_tool(
                context,
                {
                    "task_id": task_id,
                    "agent_id": agent_id,
                },
                agent_principal=resolved.agent_principal,
            )
        )

    @app.get("/api/tasks/{task_id}/workflow-memory/recommendations")
    def list_task_workflow_memory_recommendations(
        task_id: str,
        limit: int = 5,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return _tool_payload_or_http_error(
            list_workflow_memory_recommendations_tool(
                context,
                {"task_id": task_id, "limit": limit},
                agent_principal=resolved.agent_principal,
            )
        )

    @app.post("/api/tasks/{task_id}/workflow-memory/pins")
    def pin_task_workflow_memory(
        task_id: str,
        payload: WorkflowMemoryPinRequest,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return _tool_payload_or_http_error(
            pin_workflow_memory_tool(
                context,
                {"task_id": task_id, "memory_id": payload.memory_id},
                agent_principal=resolved.agent_principal,
            )
        )

    @app.delete("/api/tasks/{task_id}/workflow-memory/pins/{memory_id}")
    def unpin_task_workflow_memory(
        task_id: str,
        memory_id: str,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return _tool_payload_or_http_error(
            unpin_workflow_memory_tool(
                context,
                {"task_id": task_id, "memory_id": memory_id},
                agent_principal=resolved.agent_principal,
            )
        )

    @app.get("/api/videos/recent")
    def list_recent_videos(
        limit: int = 12,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        principal = resolved.agent_principal
        try:
            if context.settings.auth_mode == "required" and principal is None:
                raise PermissionError("agent_not_authenticated")
            if principal is not None:
                context.agent_identity_service.require_action(principal, "task:read")
        except PermissionError as exc:
            raise _permission_http_error(exc) from exc

        agent_id = principal.agent_id if principal is not None else context.settings.anonymous_agent_id
        safe_limit = max(1, min(limit, 50))
        recent = context.task_service.list_recent_videos_for_agent(agent_id, limit=safe_limit)

        items: list[dict[str, Any]] = []
        for entry in recent:
            preview_path = entry.get("preview_path")
            preview_url = (
                f"/api/tasks/{entry['task_id']}/artifacts/previews/{preview_path.name}"
                if preview_path is not None
                else None
            )
            items.append(
                {
                    "task_id": entry["task_id"],
                    "thread_id": entry.get("thread_id"),
                    "display_title": entry["display_title"],
                    "title_source": entry["title_source"],
                    "status": entry["status"],
                    "updated_at": entry["updated_at"],
                    "latest_summary": entry["latest_summary"],
                    "latest_video_url": f"/api/tasks/{entry['task_id']}/artifacts/final_video.mp4",
                    "latest_preview_url": preview_url,
                }
            )
        return {"items": items, "next_cursor": None}

    @app.get("/api/tasks/{task_id}/artifacts/{artifact_path:path}")
    def download_task_artifact(
        task_id: str,
        artifact_path: str,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> FileResponse:
        try:
            context.agent_identity_service.require_action(resolved.agent_principal, "task:read")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="agent_scope_denied") from exc

        if artifact_path.startswith(("artifacts/", "validations/", "logs/")):
            resource_uri = f"video-task://{task_id}/{artifact_path}"
        else:
            resource_uri = f"video-task://{task_id}/artifacts/{artifact_path}"
        try:
            resolved_task_id, target = resolve_resource_path(
                context,
                resource_uri,
                agent_id=resolved.agent_principal.agent_id,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="agent_access_denied") from exc
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task_not_found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource_not_found") from exc
        if resolved_task_id != task_id or not target.exists() or not target.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource_not_found")
        return FileResponse(target, media_type=guess_mime_type(target), filename=target.name)

    @app.post("/api/tasks/{task_id}/revise")
    def revise_task(
        task_id: str,
        payload: ReviseTaskRequest,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return _tool_payload_or_http_error(
            revise_video_task_tool(
                context,
                {
                    "base_task_id": task_id,
                    "feedback": payload.feedback,
                    "preserve_working_parts": payload.preserve_working_parts,
                    "memory_ids": payload.memory_ids,
                    "session_id": current_internal_session_id(resolved),
                },
                agent_principal=resolved.agent_principal,
            )
        )

    @app.post("/api/tasks/{task_id}/retry")
    def retry_task(task_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        return _tool_payload_or_http_error(
            retry_video_task_tool(
                context,
                {
                    "task_id": task_id,
                    "session_id": current_internal_session_id(resolved),
                },
                agent_principal=resolved.agent_principal,
            )
        )

    @app.post("/api/tasks/{task_id}/cancel")
    def cancel_task(task_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        return _tool_payload_or_http_error(
            cancel_video_task_tool(
                context,
                {"task_id": task_id},
                agent_principal=resolved.agent_principal,
            )
        )

    @app.post("/api/tasks/{task_id}/accept-best")
    def accept_task_as_best(task_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        return _tool_payload_or_http_error(
            accept_best_version_tool(
                context,
                {"task_id": task_id},
                agent_principal=resolved.agent_principal,
            )
        )

    return app
