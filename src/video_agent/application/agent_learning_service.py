from __future__ import annotations

from collections import Counter
from statistics import median
from typing import Callable

from video_agent.agent_policy import QUALITY_ISSUE_CODES
from video_agent.domain.agent_learning_models import AgentLearningEvent
from video_agent.domain.quality_models import QualityScorecard


_QUALITY_ISSUE_CODE_SET = set(QUALITY_ISSUE_CODES)


def select_quality_issue_codes(issue_codes: list[str]) -> list[str]:
    return [str(code) for code in issue_codes if code in _QUALITY_ISSUE_CODE_SET]


def compute_quality_score(status: str, issue_codes: list[str]) -> float:
    score = 1.0
    if status != "completed":
        score -= 0.4
    score -= 0.2 * len(select_quality_issue_codes(issue_codes))
    return max(0.0, round(score, 4))


def quality_score_from_scorecard(scorecard: QualityScorecard) -> float:
    return float(scorecard.total_score or 0.0)


def quality_score_for_task_outcome(
    *,
    status: str,
    issue_codes: list[str],
    scorecard: QualityScorecard | None,
) -> float:
    # Only completed outcomes should inherit persisted scorecard totals.
    # Failed/cancelled paths must keep heuristic penalties.
    if scorecard is not None and status == "completed":
        return quality_score_from_scorecard(scorecard)
    return compute_quality_score(status, issue_codes)


class AgentLearningService:
    def __init__(
        self,
        *,
        write_event: Callable[[AgentLearningEvent], AgentLearningEvent],
        list_events: Callable[[str, int], list[AgentLearningEvent]] | None = None,
    ) -> None:
        self._write_event = write_event
        self._list_events = list_events or (lambda agent_id, limit=200: [])

    def record_task_outcome(
        self,
        *,
        agent_id: str,
        task_id: str,
        session_id: str | None,
        status: str,
        issue_codes: list[str],
        quality_score: float,
        profile_digest: str | None,
        memory_ids: list[str],
    ) -> AgentLearningEvent:
        event = AgentLearningEvent(
            agent_id=agent_id,
            task_id=task_id,
            session_id=session_id,
            status=status,
            issue_codes=list(issue_codes),
            quality_score=quality_score,
            profile_digest=profile_digest,
            memory_ids=list(memory_ids),
        )
        return self._write_event(event)

    def build_scorecard(self, agent_id: str, limit: int = 200) -> dict[str, object]:
        events = self._list_events(agent_id, limit)
        quality_scores = [float(event.quality_score) for event in events]
        median_quality_score = round(median(quality_scores), 4) if quality_scores else 0.0
        issue_counts = Counter(code for event in events for code in event.issue_codes)
        recent_profile_digests = list(
            dict.fromkeys(event.profile_digest for event in events if event.profile_digest)
        )
        return {
            "completed_count": sum(1 for event in events if event.status == "completed"),
            "failed_count": sum(1 for event in events if event.status == "failed"),
            "median_quality_score": median_quality_score,
            "quality_score": median_quality_score,
            "top_issue_codes": [
                {"code": code, "count": count}
                for code, count in issue_counts.most_common(5)
            ],
            "recent_profile_digests": recent_profile_digests[:5],
        }
