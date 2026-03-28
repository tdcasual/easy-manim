from video_agent.domain.recovery_models import RecoveryPlan


def test_recovery_plan_tracks_selected_action_and_recipe() -> None:
    plan = RecoveryPlan(
        task_id="task-1",
        selected_action="simplify_scene",
        candidate_actions=["simplify_scene", "retry"],
        repair_recipe={"remove_effects": True},
    )

    assert plan.selected_action == "simplify_scene"
    assert plan.candidate_actions == ["simplify_scene", "retry"]
    assert plan.repair_recipe["remove_effects"] is True
