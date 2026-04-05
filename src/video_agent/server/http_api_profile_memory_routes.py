from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status

from video_agent.server.http_auth import ResolvedAgentSession, current_internal_session_id, resolve_agent_session
from video_agent.server.http_api_support import (
    AUTO_APPLY_MIN_SUGGESTION_CONFIDENCE,
    PROFILE_PATCH_ALLOWLIST,
    MemoryRetrievalRequest,
    PreferencePromotionRequest,
    PreferenceProposalRequest,
    ProfileApplyRequest,
    tool_payload_or_http_error,
    validate_profile_patch_shape,
    strip_internal_session_fields,
)
from video_agent.server.mcp_tools import (
    clear_session_memory_tool,
    disable_agent_memory_tool,
    get_agent_memory_tool,
    list_agent_memories_tool,
    promote_session_memory_tool,
    query_agent_memories_tool,
    summarize_session_memory_tool,
    get_session_memory_tool,
)


def register_profile_memory_routes(
    *,
    app: FastAPI,
    context,
    profile_suggestion_service,
    suggestion_payload,
    strategy_profile_payload,
    require_accessible_session_summary,
    raise_persistent_memory_http_error,
) -> None:
    @app.get("/api/profile/strategies")
    def list_profile_strategies(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        try:
            context.agent_identity_service.require_action(resolved.agent_principal, "profile:read")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        items = [strategy_profile_payload(profile) for profile in context.store.list_strategy_profiles()]
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

        unsupported_keys = sorted(set(payload.patch) - PROFILE_PATCH_ALLOWLIST)
        if unsupported_keys:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="unsupported_profile_patch_keys")
        validate_profile_patch_shape(payload.patch)

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
            require_accessible_session_summary(payload.session_id, resolved.agent_principal.agent_id)
        suggestion = profile_suggestion_service.create_suggestion_from_summary(
            resolved.agent_principal.agent_id,
            summary_text=payload.summary_text,
            session_id=payload.session_id,
            profile_version=resolved.agent_principal.profile.profile_version,
            source="preference_proposal",
        )
        if suggestion is None:
            return {"created": False, "reason": "no_supported_preference"}
        return {"created": True, "suggestion": suggestion_payload(suggestion)}

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
            except Exception as exc:
                raise_persistent_memory_http_error(exc)
                raise AssertionError("unreachable")
            summary_text = record.summary_text
            session_id = record.source_session_id
            source = "memory_promotion"
        elif session_id is not None:
            summary = require_accessible_session_summary(
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
        return {"created": True, "suggestion": suggestion_payload(suggestion)}

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
                        min_confidence=AUTO_APPLY_MIN_SUGGESTION_CONFIDENCE,
                    ):
                        applied.append(suggestion)
                        continue
                    unsupported_keys = sorted(set(suggestion.patch_json) - PROFILE_PATCH_ALLOWLIST)
                    if unsupported_keys:
                        applied.append(suggestion)
                        continue
                    try:
                        validate_profile_patch_shape(suggestion.patch_json)
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

        return {"items": [suggestion_payload(item) for item in items]}

    @app.get("/api/profile/suggestions")
    def list_profile_suggestions(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        try:
            context.agent_identity_service.require_action(resolved.agent_principal, "profile:read")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        items = context.store.list_agent_profile_suggestions(resolved.agent_principal.agent_id)
        return {"items": [suggestion_payload(item) for item in items]}

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

        unsupported_keys = sorted(set(suggestion.patch_json) - PROFILE_PATCH_ALLOWLIST)
        if unsupported_keys:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="unsupported_profile_patch_keys")
        validate_profile_patch_shape(suggestion.patch_json)

        try:
            updated_profile, revision, updated_suggestion = context.store.apply_agent_profile_suggestion(
                resolved.agent_principal.agent_id,
                suggestion_id=suggestion.suggestion_id,
                source=f"profile_suggestion:{suggestion.suggestion_id}",
            )
        except RuntimeError:
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
            "suggestion": None if updated_suggestion is None else suggestion_payload(updated_suggestion),
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
        return suggestion_payload(updated_suggestion)

    @app.get("/api/memory/session")
    def get_session_memory(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, object]:
        return strip_internal_session_fields(
            get_session_memory_tool(
                context,
                {},
                agent_principal=resolved.agent_principal,
                session_id=current_internal_session_id(resolved),
            )
        )

    @app.get("/api/memory/session/summary")
    def summarize_session_memory(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        return strip_internal_session_fields(
            tool_payload_or_http_error(
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
        return strip_internal_session_fields(
            tool_payload_or_http_error(
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
        return strip_internal_session_fields(
            tool_payload_or_http_error(
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
        return strip_internal_session_fields(
            tool_payload_or_http_error(
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
        return strip_internal_session_fields(
            tool_payload_or_http_error(
                query_agent_memories_tool(
                    context,
                    {"query": payload.query, "limit": payload.limit},
                    agent_principal=resolved.agent_principal,
                )
            )
        )

    @app.get("/api/memories/{memory_id}")
    def get_memory(memory_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        return strip_internal_session_fields(
            tool_payload_or_http_error(
                get_agent_memory_tool(
                    context,
                    {"memory_id": memory_id},
                    agent_principal=resolved.agent_principal,
                )
            )
        )

    @app.post("/api/memories/{memory_id}/disable")
    def disable_memory(memory_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        return strip_internal_session_fields(
            tool_payload_or_http_error(
                disable_agent_memory_tool(
                    context,
                    {"memory_id": memory_id},
                    agent_principal=resolved.agent_principal,
                )
            )
        )
