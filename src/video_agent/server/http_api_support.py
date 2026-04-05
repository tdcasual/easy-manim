from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from pydantic import BaseModel, Field

PROFILE_PATCH_ALLOWLIST = frozenset({"style_hints", "output_profile", "validation_profile"})
RECENT_PROFILE_SUGGESTION_LIMIT = 5
AUTO_APPLY_MIN_SUGGESTION_CONFIDENCE = 0.8
LEGACY_DISCUSSION_TRANSPORT_REMOVED = "legacy_discussion_transport_removed"


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


def validate_profile_patch_shape(patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if key in PROFILE_PATCH_ALLOWLIST and not isinstance(value, dict):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="invalid_profile_patch_shape")


def tool_payload_or_http_error(payload: dict[str, Any]) -> dict[str, Any]:
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


def permission_error_code(exc: PermissionError) -> str:
    code = str(exc)
    if code in {"agent_not_authenticated", "agent_access_denied", "agent_scope_denied"}:
        return code
    return "agent_access_denied"


def permission_http_error(exc: PermissionError) -> HTTPException:
    code = permission_error_code(exc)
    if code == "agent_not_authenticated":
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=code)
    if code in {"agent_access_denied", "agent_memory_forbidden", "agent_scope_denied"}:
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=code)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code)


def allowed_task_artifact_resource_uri(task_id: str, artifact_path: str) -> str:
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


def download_url_from_resource_uri(resource_uri: str | None) -> str | None:
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


def strip_internal_session_fields(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(payload)
    sanitized.pop("session_id", None)
    sanitized.pop("source_session_id", None)

    items = sanitized.get("items")
    if isinstance(items, list):
        sanitized["items"] = [
            strip_internal_session_fields(item) if isinstance(item, dict) else item
            for item in items
        ]
    return sanitized
