from video_agent.application.agent_profile_suggestion_service import AgentProfileSuggestionService
from video_agent.domain.agent_memory_models import AgentMemoryRecord


def test_service_generates_confident_suggestion_with_evidence_provenance() -> None:
    created = []
    service = AgentProfileSuggestionService(
        list_memories=lambda agent_id: [
            AgentMemoryRecord(
                memory_id="mem-1",
                agent_id=agent_id,
                source_session_id="sess-1",
                summary_text="Use a steady teaching tone and 1280x720 output.",
                summary_digest="digest-1",
            ),
            AgentMemoryRecord(
                memory_id="mem-2",
                agent_id=agent_id,
                source_session_id="sess-2",
                summary_text="Successful runs kept a teaching tone and steady pacing.",
                summary_digest="digest-2",
            ),
        ],
        list_recent_session_summaries=lambda agent_id: [
            {
                "session_id": "sess-3",
                "summary_text": "Recent successful sessions used a teaching tone and steady pacing.",
            }
        ],
        build_scorecard=lambda agent_id: {
            "completed_count": 4,
            "failed_count": 0,
            "median_quality_score": 0.97,
            "quality_score": 0.97,
            "top_issue_codes": [],
            "recent_profile_digests": ["digest-stable"],
            "profile_digest_stability": 1.0,
        },
        create_suggestion=lambda suggestion: created.append(suggestion) or suggestion,
    )

    suggestion = service.generate_suggestions("agent-a", profile_version=3)[0]

    assert suggestion.agent_id == "agent-a"
    assert suggestion.patch["style_hints"]["tone"] == "teaching"
    assert suggestion.patch["style_hints"]["pace"] == "steady"
    assert suggestion.patch["output_profile"]["pixel_width"] == 1280
    assert suggestion.patch["output_profile"]["pixel_height"] == 720
    assert suggestion.rationale_json["profile_version"] == 3
    assert suggestion.rationale_json["confidence"] >= 0.8
    assert suggestion.rationale_json["provenance"]["memory"] == 2
    assert suggestion.rationale_json["provenance"]["session_summary"] == 1
    assert suggestion.rationale_json["provenance"]["scorecard"] == 1
    assert suggestion.rationale_json["supporting_evidence_counts"]["style_hints.tone"] >= 3
    assert suggestion.rationale_json["scorecard"]["profile_digest_stability"] == 1.0
    assert created[0].suggestion_id == suggestion.suggestion_id


def test_service_filters_conflicting_patch_fields_and_records_conflicts() -> None:
    service = AgentProfileSuggestionService(
        list_memories=lambda agent_id: [
            AgentMemoryRecord(
                memory_id="mem-1",
                agent_id=agent_id,
                source_session_id="sess-1",
                summary_text="Use a teaching tone and 1280x720 output.",
                summary_digest="digest-1",
            ),
            AgentMemoryRecord(
                memory_id="mem-2",
                agent_id=agent_id,
                source_session_id="sess-2",
                summary_text="Use a direct tone and 1280x720 output.",
                summary_digest="digest-2",
            ),
        ],
        list_recent_session_summaries=lambda agent_id: [],
        build_scorecard=lambda agent_id: {
            "completed_count": 5,
            "failed_count": 0,
            "median_quality_score": 0.96,
            "quality_score": 0.96,
            "top_issue_codes": [],
            "recent_profile_digests": ["digest-stable"],
            "profile_digest_stability": 1.0,
        },
        create_suggestion=lambda suggestion: suggestion,
    )

    suggestion = service.generate_suggestions("agent-a", profile_version=2)[0]

    assert "style_hints" not in suggestion.patch or "tone" not in suggestion.patch.get("style_hints", {})
    assert suggestion.patch["output_profile"]["pixel_width"] == 1280
    assert suggestion.patch["output_profile"]["pixel_height"] == 720
    assert suggestion.rationale_json["conflicts"]
    assert suggestion.rationale_json["conflicts"][0]["field"] == "style_hints.tone"


def test_service_penalizes_issue_trends_in_confidence() -> None:
    service = AgentProfileSuggestionService(
        list_memories=lambda agent_id: [
            AgentMemoryRecord(
                memory_id="mem-1",
                agent_id=agent_id,
                source_session_id="sess-1",
                summary_text="Use a steady teaching tone.",
                summary_digest="digest-1",
            )
        ],
        list_recent_session_summaries=lambda agent_id: [],
        build_scorecard=lambda agent_id: {
            "completed_count": 3,
            "failed_count": 0,
            "median_quality_score": 0.95,
            "quality_score": 0.95,
            "top_issue_codes": [{"code": "static_previews", "count": 3}],
            "recent_profile_digests": ["digest-a", "digest-b"],
            "profile_digest_stability": 0.5,
        },
        create_suggestion=lambda suggestion: suggestion,
    )

    suggestion = service.generate_suggestions("agent-a", profile_version=1)[0]

    assert suggestion.patch["style_hints"]["tone"] == "teaching"
    assert suggestion.rationale_json["confidence"] < 0.8
    assert suggestion.rationale_json["scorecard"]["top_issue_codes"][0]["code"] == "static_previews"


def test_service_does_not_treat_indirect_as_direct_tone() -> None:
    service = AgentProfileSuggestionService(
        list_memories=lambda agent_id: [
            AgentMemoryRecord(
                memory_id="mem-1",
                agent_id=agent_id,
                source_session_id="sess-1",
                summary_text="Use an indirect tone and 1280x720 output.",
                summary_digest="digest-1",
            )
        ],
        list_recent_session_summaries=lambda agent_id: [],
        build_scorecard=lambda agent_id: {
            "completed_count": 2,
            "failed_count": 0,
            "median_quality_score": 0.96,
            "quality_score": 0.96,
            "top_issue_codes": [],
            "recent_profile_digests": ["digest-stable"],
            "profile_digest_stability": 1.0,
        },
        create_suggestion=lambda suggestion: suggestion,
    )

    suggestion = service.generate_suggestions("agent-a", profile_version=1)[0]

    assert "style_hints" not in suggestion.patch or "tone" not in suggestion.patch.get("style_hints", {})
    assert suggestion.patch["output_profile"]["pixel_width"] == 1280
    assert suggestion.patch["output_profile"]["pixel_height"] == 720
