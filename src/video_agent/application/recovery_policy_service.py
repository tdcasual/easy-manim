from __future__ import annotations

from video_agent.domain.recovery_models import RecoveryPlan


class RecoveryPolicyService:
    def build(
        self,
        *,
        issue_code: str | None,
        failure_contract: dict | None,
    ) -> RecoveryPlan:
        _ = failure_contract
        if issue_code == "near_blank_preview":
            return RecoveryPlan(
                task_id="",
                issue_code=issue_code,
                candidate_actions=["preview_repair"],
                selected_action="preview_repair",
                repair_recipe="preview_repair",
                fallback_generation_mode="guided_generate",
                cost_class="low",
            )
        if issue_code == "render_failed":
            return RecoveryPlan(
                task_id="",
                issue_code=issue_code,
                candidate_actions=["repair_render_path"],
                selected_action="repair_render_path",
                repair_recipe="targeted_render_repair",
                cost_class="medium",
            )
        return RecoveryPlan(
            task_id="",
            issue_code=issue_code,
            candidate_actions=["escalate_human"],
            selected_action="escalate_human",
            human_gate_required=True,
        )
