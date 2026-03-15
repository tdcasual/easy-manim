from video_agent.application.repair_prompt_builder import build_targeted_repair_feedback


def test_repair_feedback_adds_preview_quality_guidance_for_near_blank_previews() -> None:
    feedback = build_targeted_repair_feedback(
        issue_code="near_blank_preview",
        failure_context={
            "preview_issue_codes": ["near_blank_preview"],
            "current_script_resource": "video-task://task-id/artifacts/current_script.py",
        },
    )

    assert "Do not open on a blank or almost blank frame." in feedback
    assert "Set the light background before scene construction begins" in feedback
    assert "Make the first beat visibly populated" in feedback
