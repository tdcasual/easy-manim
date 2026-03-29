from __future__ import annotations

from video_agent.domain.recovery_models import RecoveryPlan


class RecoveryPolicyService:
    def build(
        self,
        *,
        issue_code: str | None,
        failure_contract: dict | None,
    ) -> RecoveryPlan:
        if failure_contract:
            recommended_action = str(failure_contract.get("recommended_action") or "")
            candidate_actions = [str(item) for item in failure_contract.get("candidate_actions") or [] if item]
            if recommended_action == "auto_repair" and candidate_actions:
                repair_recipe = failure_contract.get("repair_strategy") or candidate_actions[0]
                return RecoveryPlan(
                    task_id="",
                    issue_code=issue_code,
                    candidate_actions=candidate_actions,
                    selected_action=candidate_actions[0],
                    repair_recipe=repair_recipe,
                    fallback_generation_mode=failure_contract.get("fallback_generation_mode"),
                    cost_class=failure_contract.get("cost_class"),
                    human_gate_required=bool(failure_contract.get("human_review_required")),
                )
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
