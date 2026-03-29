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
    assert "Add a clearly visible motion beat so the preview sequence is not effectively static." in feedback
    assert "Within the first 2 seconds, change position, scale, or emphasis of an existing on-screen object" in feedback
    assert "Keep at least two visually distinct states across the preview frames." in feedback


def test_repair_feedback_adds_explicit_motion_recipe_for_static_previews() -> None:
    feedback = build_targeted_repair_feedback(
        issue_code="static_previews",
        failure_context={
            "preview_issue_codes": ["static_previews"],
            "current_script_resource": "video-task://task-id/artifacts/current_script.py",
        },
    )

    assert "Add a clearly visible motion beat so the preview sequence is not effectively static." in feedback
    assert "Within the first 2 seconds, change position, scale, or emphasis of an existing on-screen object" in feedback
    assert "Keep at least two visually distinct states across the preview frames." in feedback


def test_repair_feedback_includes_session_memory_context() -> None:
    feedback = build_targeted_repair_feedback(
        issue_code="near_blank_preview",
        failure_context={"summary": "blank opening"},
        memory_context_summary="Earlier attempts already established a working light-background layout.",
    )

    assert "Session memory context:" in feedback
    assert "working light-background layout" in feedback
