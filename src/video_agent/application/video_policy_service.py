from __future__ import annotations


class VideoPolicyService:
    def determine_next_role(
        self,
        *,
        requested_action: str,
        has_selected_result: bool,
    ) -> str | None:
        if requested_action == "generate":
            return "planner"
        if requested_action == "revise" and has_selected_result:
            return "repairer"
        return None
