from video_agent.application.agent_profile_suggestion_service import AgentProfileSuggestionService
from video_agent.domain.agent_memory_models import AgentMemoryRecord


def test_service_derives_patch_from_persistent_memory_and_recent_success() -> None:
    created = []
    service = AgentProfileSuggestionService(
        list_memories=lambda agent_id: [
            AgentMemoryRecord(
                memory_id="mem-1",
                agent_id=agent_id,
                source_session_id="sess-1",
                summary_text="Use a steady teaching tone and 1280x720 output.",
                summary_digest="digest-1",
            )
        ],
        list_recent_session_summaries=lambda agent_id: [
            {"session_id": "sess-1", "summary_text": "Successful sessions preferred a teaching tone and steady pacing."}
        ],
        build_scorecard=lambda agent_id: {"completed_count": 5, "median_quality_score": 0.95},
        create_suggestion=lambda suggestion: created.append(suggestion) or suggestion,
    )

    suggestion = service.generate_suggestions("agent-a", profile_version=3)[0]

    assert suggestion.agent_id == "agent-a"
    assert suggestion.patch["style_hints"]["tone"] == "teaching"
    assert suggestion.patch["style_hints"]["pace"] == "steady"
    assert suggestion.patch["output_profile"]["pixel_width"] == 1280
    assert suggestion.patch["output_profile"]["pixel_height"] == 720
    assert suggestion.rationale_json["profile_version"] == 3
    assert created[0].suggestion_id == suggestion.suggestion_id
