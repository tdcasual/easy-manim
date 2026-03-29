from video_agent.application.profile_evidence_service import ProfileEvidenceService


def test_evidence_service_builds_patch_with_field_support_metadata() -> None:
    service = ProfileEvidenceService()

    bundle = service.build_bundle(
        [
            (
                "Use a teaching tone and 1280x720 output.",
                {"source": "memory", "memory_id": "mem-1", "session_id": "sess-1"},
            ),
            (
                "Successful sessions preferred a teaching tone and steady pacing.",
                {"source": "session_summary", "session_id": "sess-2"},
            ),
        ]
    )

    assert bundle.patch["style_hints"]["tone"] == "teaching"
    assert bundle.patch["style_hints"]["pace"] == "steady"
    assert bundle.patch["output_profile"]["pixel_width"] == 1280
    assert bundle.patch["output_profile"]["pixel_height"] == 720
    assert bundle.supporting_evidence_counts["style_hints.tone"] == 2
    assert bundle.field_support["style_hints.tone"]["support_count"] == 2
    assert bundle.field_support["style_hints.tone"]["source_type_counts"]["memory"] == 1
    assert bundle.field_support["style_hints.tone"]["source_type_counts"]["session_summary"] == 1
    assert bundle.field_support["style_hints.tone"]["distinct_session_count"] == 2
    assert bundle.has_strong_field_support(min_support_per_field=2) is True


def test_evidence_service_flags_conflicts_and_reports_rationale_metadata() -> None:
    service = ProfileEvidenceService()

    bundle = service.build_bundle(
        [
            (
                "Use a teaching tone and steady pacing.",
                {"source": "memory", "memory_id": "mem-1", "session_id": "sess-1"},
            ),
            (
                "Use a direct tone and steady pacing.",
                {"source": "memory", "memory_id": "mem-2", "session_id": "sess-2"},
            ),
        ]
    )

    assert "style_hints" in bundle.patch
    assert "tone" not in bundle.patch["style_hints"]
    assert bundle.patch["style_hints"]["pace"] == "steady"
    assert bundle.conflicts
    assert bundle.conflicts[0]["field"] == "style_hints.tone"
    assert bundle.field_support["style_hints.pace"]["support_count"] == 2


def test_evidence_service_treats_split_single_field_evidence_as_weak() -> None:
    service = ProfileEvidenceService()

    bundle = service.build_bundle(
        [
            (
                "Use a teaching tone.",
                {"source": "memory", "memory_id": "mem-1", "session_id": "sess-1"},
            ),
            (
                "Use 1280x720 output.",
                {"source": "memory", "memory_id": "mem-2", "session_id": "sess-2"},
            ),
        ]
    )

    assert bundle.supporting_evidence_counts["style_hints.tone"] == 1
    assert bundle.supporting_evidence_counts["output_profile.pixel_width"] == 1
    assert bundle.has_strong_field_support(min_support_per_field=2) is False
