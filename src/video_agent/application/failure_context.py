from __future__ import annotations

from typing import Any

from video_agent.adapters.storage.artifact_store import ArtifactStore
from video_agent.domain.models import VideoTask
from video_agent.domain.validation_models import ValidationReport
from video_agent.validation.script_diagnostics import collect_script_diagnostics


def build_failure_context(
    task: VideoTask,
    report: ValidationReport,
    artifact_store: ArtifactStore,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    top_issue = report.issues[0] if report.issues else None
    current_script_path = artifact_store.script_path(task.task_id)
    current_script_exists = current_script_path.exists()
    semantic_diagnostics = []
    if current_script_exists:
        semantic_diagnostics = [
            item.model_dump(mode="json") for item in collect_script_diagnostics(current_script_path.read_text())
        ]

    failure_context = {
        "task_id": task.task_id,
        "root_task_id": task.root_task_id,
        "parent_task_id": task.parent_task_id,
        "inherited_from_task_id": task.inherited_from_task_id,
        "phase": task.phase.value,
        "failure_code": top_issue.code if top_issue else None,
        "failure_message": top_issue.message if top_issue else None,
        "summary": report.summary,
        "stderr": _find_latest_event_value(events, "stderr"),
        "provider_error": _provider_error_for_issue(top_issue.code if top_issue else None, events),
        "missing_checks": _find_latest_event_value(events, "missing_checks"),
        "current_script_path": str(current_script_path) if current_script_exists else None,
        "current_script_resource": (
            artifact_store.resource_uri(task.task_id, current_script_path) if current_script_exists else None
        ),
        "semantic_diagnostics": semantic_diagnostics,
        "preview_issue_codes": _preview_issue_codes(report),
        "sandbox_policy": report.details.get("sandbox_policy") if report.details else None,
    }
    return failure_context


def _find_latest_event_value(events: list[dict[str, Any]], key: str) -> Any:
    for event in reversed(events):
        payload = event.get("payload", {})
        if key in payload and payload[key] not in (None, "", []):
            return payload[key]
    return None


def _provider_error_for_issue(issue_code: str | None, events: list[dict[str, Any]]) -> str | None:
    if issue_code is None or not issue_code.startswith("provider_"):
        return None
    error = _find_latest_event_value(events, "error")
    if error is None:
        return None
    return str(error)


def _preview_issue_codes(report: ValidationReport) -> list[str]:
    if not report.details:
        return []
    preview = report.details.get("preview")
    if not isinstance(preview, dict):
        return []
    issues = preview.get("issues")
    if not isinstance(issues, list):
        return []
    return [str(item.get("code")) for item in issues if isinstance(item, dict) and item.get("code")]
