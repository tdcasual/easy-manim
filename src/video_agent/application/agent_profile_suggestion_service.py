from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from typing import Any, Callable

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
    ) -> None:
        self._list_memories = list_memories
        self._list_recent_session_summaries = list_recent_session_summaries
        self._build_scorecard = build_scorecard
        self._create_suggestion = create_suggestion

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
        sources: list[dict[str, Any]] = []
        evidence_by_field: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
        value_lookup: dict[tuple[str, str], Any] = {}
        for summary_text, provenance in texts:
            field_evidence = self._field_evidence_from_text(summary_text, provenance)
            if not field_evidence:
                continue
            sources.append(
                {
                    **provenance,
                    "summary_text": summary_text,
                }
            )
            for item in field_evidence:
                field_path = str(item["field"])
                value = item["value"]
                value_key = self._value_key(value)
                evidence_by_field[field_path][value_key].append(item)
                value_lookup[(field_path, value_key)] = value

        combined_patch, supporting_evidence_counts, conflicts = self._build_patch_from_field_evidence(
            evidence_by_field,
            value_lookup,
        )

        completed_count = int(scorecard.get("completed_count", 0) or 0)
        median_quality_score = self._scorecard_quality_metric(scorecard)
        if not combined_patch or completed_count <= 0 or median_quality_score <= 0.0:
            return None

        return AgentProfileSuggestion(
            agent_id=agent_id,
            patch_json=combined_patch,
            rationale_json={
                "sources": sources,
                "scorecard": dict(scorecard),
                "profile_version": profile_version,
                "provenance": self._provenance_counts(sources),
                "supporting_evidence_counts": supporting_evidence_counts,
                "conflicts": conflicts,
                "confidence": self._confidence_from_signals(
                    scorecard=scorecard,
                    supporting_evidence_counts=supporting_evidence_counts,
                ),
            },
        )

    @staticmethod
    def _scorecard_quality_metric(scorecard: dict[str, object]) -> float:
        return float(scorecard.get("quality_score", scorecard.get("median_quality_score", 0.0)) or 0.0)

    @staticmethod
    def _field_evidence_from_text(summary_text: str, provenance: dict[str, Any]) -> list[dict[str, Any]]:
        normalized = summary_text.lower()
        evidence: list[dict[str, Any]] = []

        def add(field: str, value: Any) -> None:
            evidence.append(
                {
                    "field": field,
                    "value": value,
                    "source": provenance.get("source"),
                    "memory_id": provenance.get("memory_id"),
                    "session_id": provenance.get("session_id"),
                }
            )

        if re.search(r"\bteaching(?:\s+tone)?\b", normalized):
            add("style_hints.tone", "teaching")
        elif re.search(r"\bpatient(?:\s+tone)?\b", normalized):
            add("style_hints.tone", "patient")
        elif re.search(r"\bdirect(?:\s+tone)?\b", normalized):
            add("style_hints.tone", "direct")

        if re.search(r"\bsteady(?:\s+(?:pacing|pace))?\b", normalized):
            add("style_hints.pace", "steady")
        elif re.search(r"\bbrisk(?:\s+(?:pacing|pace))?\b", normalized):
            add("style_hints.pace", "brisk")

        resolution_match = re.search(r"(\d{3,4})\s*[x×]\s*(\d{3,4})", normalized)
        if resolution_match:
            add("output_profile.pixel_width", int(resolution_match.group(1)))
            add("output_profile.pixel_height", int(resolution_match.group(2)))

        if re.search(r"\bstrict validation\b", normalized) or re.search(r"\bstrictly validate\b", normalized):
            add("validation_profile.strict", True)

        return evidence

    @classmethod
    def _build_patch_from_field_evidence(
        cls,
        evidence_by_field: dict[str, dict[str, list[dict[str, Any]]]],
        value_lookup: dict[tuple[str, str], Any],
    ) -> tuple[dict[str, Any], dict[str, int], list[dict[str, Any]]]:
        patch: dict[str, Any] = {}
        supporting_evidence_counts: dict[str, int] = {}
        conflicts: list[dict[str, Any]] = []

        for field_path in sorted(evidence_by_field):
            options = evidence_by_field[field_path]
            if len(options) > 1:
                conflicts.append(
                    {
                        "field": field_path,
                        "values": [
                            {
                                "value": value_lookup[(field_path, value_key)],
                                "count": len(items),
                            }
                            for value_key, items in sorted(
                                options.items(),
                                key=lambda option: (-len(option[1]), option[0]),
                            )
                        ],
                    }
                )
                continue

            value_key, items = next(iter(options.items()))
            cls._assign_patch_value(patch, field_path, value_lookup[(field_path, value_key)])
            supporting_evidence_counts[field_path] = len(items)

        return patch, supporting_evidence_counts, conflicts

    @staticmethod
    def _assign_patch_value(patch: dict[str, Any], field_path: str, value: Any) -> None:
        current = patch
        parts = field_path.split(".")
        for key in parts[:-1]:
            current = current.setdefault(key, {})
        current[parts[-1]] = value

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
    ) -> float:
        quality = cls._scorecard_quality_metric(scorecard)
        completed_count = int(scorecard.get("completed_count", 0) or 0)
        digest_stability = float(scorecard.get("profile_digest_stability", 0.0) or 0.0)
        max_evidence = max(supporting_evidence_counts.values(), default=0)
        evidence_strength = min(max_evidence, 3) / 3 if max_evidence else 0.0
        completion_strength = min(completed_count, 3) / 3 if completed_count else 0.0
        issue_penalty = min(cls._issue_trend_count(scorecard), 3) * 0.1
        weak_support_penalty = 0.2 if max_evidence < 2 else 0.0
        confidence = (
            quality * 0.65
            + digest_stability * 0.2
            + completion_strength * 0.1
            + evidence_strength * 0.1
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

    @staticmethod
    def _value_key(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
