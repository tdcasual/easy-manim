from __future__ import annotations

from collections import Counter
from typing import Any, Callable

from video_agent.application.profile_evidence_service import ProfileEvidenceService
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.agent_profile_suggestion_models import AgentProfileSuggestion


class AgentProfileSuggestionService:
    def __init__(
        self,
        *,
        list_memories: Callable[[str], list[AgentMemoryRecord]],
        list_recent_session_summaries: Callable[[str], list[dict[str, Any]]],
        build_scorecard: Callable[[str], dict[str, object]],
        create_suggestion: Callable[[AgentProfileSuggestion], AgentProfileSuggestion],
        evidence_service: ProfileEvidenceService | None = None,
    ) -> None:
        self._list_memories = list_memories
        self._list_recent_session_summaries = list_recent_session_summaries
        self._build_scorecard = build_scorecard
        self._create_suggestion = create_suggestion
        self._evidence_service = evidence_service or ProfileEvidenceService()

    def generate_suggestions(self, agent_id: str, *, profile_version: int | None = None) -> list[AgentProfileSuggestion]:
        scorecard = self._build_scorecard(agent_id)
        texts: list[tuple[str, dict[str, Any]]] = []
        for record in self._list_memories(agent_id):
            if record.status != "active" or not record.summary_text.strip():
                continue
            texts.append(
                (
                    record.summary_text,
                    {
                        "source": "memory",
                        "memory_id": record.memory_id,
                        "session_id": record.source_session_id,
                    },
                )
            )
        for summary in self._list_recent_session_summaries(agent_id):
            summary_text = str(summary.get("summary_text") or "").strip()
            if not summary_text:
                continue
            texts.append(
                (
                    summary_text,
                    {
                        "source": "session_summary",
                        "session_id": summary.get("session_id"),
                    },
                )
            )

        suggestion = self._suggestion_from_texts(
            agent_id=agent_id,
            texts=texts,
            scorecard=scorecard,
            profile_version=profile_version,
        )
        if suggestion is None:
            return []
        return [self._create_suggestion(suggestion)]

    def create_suggestion_from_summary(
        self,
        agent_id: str,
        *,
        summary_text: str,
        session_id: str | None = None,
        memory_id: str | None = None,
        profile_version: int | None = None,
        source: str = "preference_summary",
    ) -> AgentProfileSuggestion | None:
        suggestion = self._suggestion_from_texts(
            agent_id=agent_id,
            texts=[
                (
                    summary_text,
                    {
                        "source": source,
                        "session_id": session_id,
                        "memory_id": memory_id,
                    },
                )
            ],
            scorecard=self._build_scorecard(agent_id),
            profile_version=profile_version,
        )
        if suggestion is None:
            return None
        return self._create_suggestion(suggestion)

    def _suggestion_from_texts(
        self,
        *,
        agent_id: str,
        texts: list[tuple[str, dict[str, Any]]],
        scorecard: dict[str, object],
        profile_version: int | None,
    ) -> AgentProfileSuggestion | None:
        bundle = self._evidence_service.build_bundle(texts)

        completed_count = int(scorecard.get("completed_count", 0) or 0)
        median_quality_score = self._scorecard_quality_metric(scorecard)
        if not bundle.patch or completed_count <= 0 or median_quality_score <= 0.0:
            return None

        return AgentProfileSuggestion(
            agent_id=agent_id,
            patch_json=bundle.patch,
            rationale_json={
                "sources": bundle.sources,
                "scorecard": dict(scorecard),
                "profile_version": profile_version,
                "provenance": self._provenance_counts(bundle.sources),
                "supporting_evidence_counts": bundle.supporting_evidence_counts,
                "field_support": bundle.field_support,
                "conflicts": bundle.conflicts,
                "confidence": self._confidence_from_signals(
                    scorecard=scorecard,
                    supporting_evidence_counts=bundle.supporting_evidence_counts,
                    field_support=bundle.field_support,
                ),
            },
        )

    @staticmethod
    def _scorecard_quality_metric(scorecard: dict[str, object]) -> float:
        return float(scorecard.get("quality_score", scorecard.get("median_quality_score", 0.0)) or 0.0)

    @staticmethod
    def _provenance_counts(sources: list[dict[str, Any]]) -> dict[str, int]:
        counts = Counter(
            str(source["source"])
            for source in sources
            if source.get("source")
        )
        counts["scorecard"] += 1
        return dict(counts)

    @classmethod
    def _confidence_from_signals(
        cls,
        *,
        scorecard: dict[str, object],
        supporting_evidence_counts: dict[str, int],
        field_support: dict[str, dict[str, Any]],
    ) -> float:
        quality = cls._scorecard_quality_metric(scorecard)
        completed_count = int(scorecard.get("completed_count", 0) or 0)
        digest_stability = float(scorecard.get("profile_digest_stability", 0.0) or 0.0)
        max_evidence = max(supporting_evidence_counts.values(), default=0)
        evidence_strength = max(
            (
                float(item.get("confidence", 0.0) or 0.0)
                for item in field_support.values()
                if isinstance(item, dict)
            ),
            default=(min(max_evidence, 3) / 3 if max_evidence else 0.0),
        )
        completion_strength = min(completed_count, 3) / 3 if completed_count else 0.0
        issue_penalty = min(cls._issue_trend_count(scorecard), 3) * 0.1
        weak_support_penalty = 0.2 if max_evidence < 2 else 0.0
        confidence = (
            quality * 0.55
            + digest_stability * 0.15
            + completion_strength * 0.1
            + evidence_strength * 0.2
            - issue_penalty
            - weak_support_penalty
        )
        return round(max(0.0, min(1.0, confidence)), 4)

    @staticmethod
    def _issue_trend_count(scorecard: dict[str, object]) -> int:
        total = 0
        for item in scorecard.get("top_issue_codes", []) or []:
            if not isinstance(item, dict):
                continue
            total += int(item.get("count", 0) or 0)
        return total
