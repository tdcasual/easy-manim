from video_agent.application.video_policy_service import VideoPolicyService


def test_video_policy_service_selects_responsible_role_for_revision() -> None:
    service = VideoPolicyService()

    assert service.determine_next_role(requested_action="revise", has_selected_result=True) == "repairer"
    assert service.determine_next_role(requested_action="discuss", has_selected_result=True) is None
    assert service.determine_next_role(requested_action="generate", has_selected_result=False) == "planner"
