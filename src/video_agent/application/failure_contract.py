from __future__ import annotations

from pydantic import BaseModel, Field


class FailureContract(BaseModel):
    issue_code: str | None = None
    retryable: bool = False
    blocking_layer: str = "unknown"
    recommended_action: str = "inspect_failure_context"
    repair_strategy: str | None = None
    candidate_actions: list[str] = Field(default_factory=list)
    cost_class: str | None = None
    fallback_generation_mode: str | None = None
    suggested_tool: str | None = None
    human_review_required: bool = False


def build_failure_contract(
    issue_code: str | None,
    summary: str | None,
    preview_issue_codes: list[str],
    retryable_issue_codes: list[str],
) -> FailureContract:
    contract = FailureContract(issue_code=issue_code)
    retryable_codes = set(retryable_issue_codes)
    preview_codes = set(preview_issue_codes)

    if issue_code is None:
        contract.human_review_required = True
        return contract

    if issue_code.startswith("provider_"):
        contract.blocking_layer = "provider"
        contract.suggested_tool = "get_task_events"
        if issue_code == "provider_auth_error":
            contract.recommended_action = "fix_credentials"
            contract.human_review_required = True
            contract.candidate_actions = ["fix_credentials"]
        elif issue_code in {"provider_rate_limited", "provider_timeout"}:
            contract.retryable = True
            contract.recommended_action = "retry_later"
            contract.candidate_actions = ["retry_later"]
        else:
            contract.recommended_action = "inspect_upstream"
            contract.human_review_required = True
            contract.candidate_actions = ["inspect_upstream"]
        return contract

    if issue_code == "latex_dependency_missing":
        contract.blocking_layer = "runtime"
        contract.recommended_action = "install_dependencies"
        contract.candidate_actions = ["install_dependencies"]
        contract.fallback_generation_mode = "guided_generate"
        contract.suggested_tool = "get_runtime_status"
        contract.human_review_required = True
        return contract

    if issue_code in {"sandbox_policy_violation", "runtime_policy_violation"}:
        contract.blocking_layer = "runtime"
        contract.recommended_action = "inspect_runtime_policy"
        contract.candidate_actions = ["inspect_runtime_policy"]
        contract.suggested_tool = "get_runtime_status"
        contract.human_review_required = True
        return contract

    if issue_code == "render_failed":
        contract.blocking_layer = "render"
        contract.retryable = issue_code in retryable_codes
        contract.recommended_action = "auto_repair" if contract.retryable else "inspect_failure_context"
        contract.repair_strategy = "targeted_repair" if contract.retryable else None
        contract.candidate_actions = ["repair_render_path"] if contract.retryable else ["inspect_failure_context"]
        contract.cost_class = "medium"
        contract.suggested_tool = "get_video_task"
        return contract

    if issue_code.startswith("unsafe_"):
        contract.blocking_layer = "validation"
        contract.retryable = issue_code in retryable_codes
        contract.recommended_action = "auto_repair" if contract.retryable else "inspect_failure_context"
        contract.repair_strategy = "targeted_repair"
        contract.candidate_actions = ["targeted_repair"] if contract.retryable else ["inspect_failure_context"]
        contract.suggested_tool = "get_video_task"
        return contract

    if issue_code in {"near_blank_preview", "static_previews"} or issue_code in preview_codes:
        contract.blocking_layer = "preview"
        contract.retryable = issue_code in retryable_codes or issue_code in preview_codes
        contract.recommended_action = "auto_repair"
        contract.repair_strategy = "preview_repair"
        contract.candidate_actions = ["preview_repair"]
        contract.cost_class = "low"
        contract.fallback_generation_mode = "guided_generate"
        contract.suggested_tool = "get_video_task"
        return contract

    if issue_code in retryable_codes:
        contract.retryable = True
        contract.recommended_action = "auto_repair"
        contract.repair_strategy = "targeted_repair"
        contract.candidate_actions = ["targeted_repair"]
        contract.suggested_tool = "get_video_task"

    if summary and summary.lower().startswith("provider"):
        contract.blocking_layer = "provider"
    return contract
