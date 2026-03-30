from video_agent.application.agent_learning_service import (
    AgentLearningService,
    quality_score_for_task_outcome,
    quality_score_from_scorecard,
)
from video_agent.domain.quality_models import QualityScorecard
from video_agent.domain.agent_learning_models import AgentLearningEvent


def test_learning_service_records_success_and_quality_signals() -> None:
    written: list[AgentLearningEvent] = []
    service = AgentLearningService(write_event=lambda event: written.append(event) or event)

    service.record_task_outcome(
        agent_id="agent-a",
        task_id="task-1",
        session_id="sess-1",
        status="completed",
        issue_codes=["near_blank_preview"],
        quality_score=0.8,
        profile_digest="digest-1",
        memory_ids=["mem-1"],
    )

    assert written[0].agent_id == "agent-a"
    assert written[0].task_id == "task-1"
    assert written[0].quality_score == 0.8
    assert written[0].memory_ids == ["mem-1"]


def test_learning_service_builds_scorecard_from_recent_events() -> None:
    service = AgentLearningService(
        write_event=lambda event: event,
        list_events=lambda agent_id, limit=200: [
            AgentLearningEvent(
                event_id="evt-3",
                agent_id=agent_id,
                task_id="task-3",
                session_id="sess-3",
                status="completed",
                issue_codes=["near_blank_preview"],
                quality_score=0.8,
                profile_digest="digest-3",
                memory_ids=["mem-2"],
            ),
            AgentLearningEvent(
                event_id="evt-2",
                agent_id=agent_id,
                task_id="task-2",
                session_id="sess-2",
                status="failed",
                issue_codes=["near_blank_preview", "render_failed"],
                quality_score=0.2,
                profile_digest="digest-2",
                memory_ids=[],
            ),
            AgentLearningEvent(
                event_id="evt-1",
                agent_id=agent_id,
                task_id="task-1",
                session_id="sess-1",
                status="completed",
                issue_codes=[],
                quality_score=0.9,
                profile_digest="digest-1",
                memory_ids=["mem-1"],
            ),
        ],
    )

    scorecard = service.build_scorecard("agent-a")

    assert scorecard["completed_count"] == 2
    assert scorecard["failed_count"] == 1
    assert scorecard["median_quality_score"] == 0.8
    assert scorecard["top_issue_codes"][0] == {"code": "near_blank_preview", "count": 2}
    assert scorecard["recent_profile_digests"] == ["digest-3", "digest-2", "digest-1"]


def test_learning_service_builds_scorecard_from_quality_passed_outcomes_only() -> None:
    service = AgentLearningService(
        write_event=lambda event: event,
        list_events=lambda agent_id, limit=200: [
            AgentLearningEvent(
                event_id="evt-2",
                agent_id=agent_id,
                task_id="task-2",
                session_id="sess-2",
                status="completed",
                issue_codes=[],
                quality_score=0.6,
                quality_passed=False,
                profile_digest="digest-2",
                memory_ids=[],
            ),
            AgentLearningEvent(
                event_id="evt-1",
                agent_id=agent_id,
                task_id="task-1",
                session_id="sess-1",
                status="completed",
                issue_codes=[],
                quality_score=0.9,
                quality_passed=True,
                profile_digest="digest-1",
                memory_ids=[],
            ),
        ],
    )

    scorecard = service.build_scorecard("agent-a")

    assert scorecard["completed_count"] == 1
    assert scorecard["quality_passed_count"] == 1
    assert scorecard["failed_count"] == 0
    assert scorecard["median_quality_score"] == 0.75


def test_learning_service_accepts_quality_scorecard_total_score() -> None:
    written: list[AgentLearningEvent] = []
    service = AgentLearningService(write_event=lambda event: written.append(event) or event)
    scorecard = QualityScorecard(
        total_score=0.72,
        dimension_scores={"motion_smoothness": 0.4},
        must_fix_issues=["static_previews"],
        accepted=False,
    )

    service.record_task_outcome(
        agent_id="agent-a",
        task_id="task-1",
        session_id="sess-1",
        status="completed",
        issue_codes=scorecard.must_fix_issues,
        quality_score=scorecard.total_score,
        profile_digest="digest-1",
        memory_ids=[],
    )

    assert written[0].quality_score == 0.72


def test_quality_score_from_scorecard_supports_legacy_overall_score_field() -> None:
    scorecard = QualityScorecard(
        overall_score=0.81,
        dimensions={"motion_smoothness": 0.9},
        accepted=True,
    )

    assert quality_score_from_scorecard(scorecard) == 0.81


def test_quality_score_for_task_outcome_prefers_scorecard_when_available() -> None:
    scorecard = QualityScorecard(total_score=0.925, accepted=True)

    score = quality_score_for_task_outcome(
        status="completed",
        issue_codes=[],
        scorecard=scorecard,
    )

    assert score == 0.925


def test_quality_score_for_task_outcome_falls_back_to_heuristic_without_scorecard() -> None:
    score = quality_score_for_task_outcome(
        status="completed",
        issue_codes=[],
        scorecard=None,
    )

    assert score == 1.0


def test_quality_score_for_task_outcome_does_not_apply_scorecard_to_failed_status() -> None:
    scorecard = QualityScorecard(total_score=0.925, accepted=True)

    score = quality_score_for_task_outcome(
        status="failed",
        issue_codes=[],
        scorecard=scorecard,
    )

    assert score == 0.6


def test_quality_score_for_task_outcome_does_not_apply_scorecard_to_delivery_only_completion() -> None:
    scorecard = QualityScorecard(total_score=0.925, accepted=True)

    score = quality_score_for_task_outcome(
        status="completed",
        issue_codes=[],
        scorecard=scorecard,
        quality_passed=False,
    )

    assert score == 0.6
